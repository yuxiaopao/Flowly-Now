"""Deploy immutable application images and restore the previous release on failure.

Runs only when explicitly invoked on a deployment host. Database migrations run
forward once; restoring application images never reverses database migrations.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from urllib.parse import urlsplit


REMOTE_IMAGE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}$')
LOCAL_IMAGE = re.compile(r'^sha256:[a-f0-9]{64}$')
SERVICES = ('backend', 'celery', 'celery-beat', 'frontend')


class DeploymentError(RuntimeError):
    pass


def validate_image(reference, *, allow_local=False):
    if not isinstance(reference, str) or not (
        REMOTE_IMAGE.fullmatch(reference) or (allow_local and LOCAL_IMAGE.fullmatch(reference))
    ):
        raise DeploymentError('Image references must use a sha256 digest, never a mutable tag')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', text=True)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as output:
            json.dump(value, output, indent=2)
            output.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Deployment:
    def __init__(self, project_directory, compose_file, state_directory, project_name,
                 health_url, *, health_attempts=30, health_interval=2, wait_timeout=120,
                 runner=subprocess.run, sleep=time.sleep):
        self.project_directory = Path(project_directory).resolve()
        self.compose_file = (self.project_directory / compose_file).resolve()
        self.state_directory = (self.project_directory / state_directory).resolve()
        address = urlsplit(health_url)
        if address.scheme not in ('http', 'https') or not address.hostname:
            raise DeploymentError('Health URL must be an absolute HTTP or HTTPS URL')
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', project_name):
            raise DeploymentError('Compose project name is invalid')
        self.project_name = project_name
        self.health_url = health_url
        self.health_attempts = health_attempts
        self.health_interval = health_interval
        self.wait_timeout = wait_timeout
        self.runner = runner
        self.sleep = sleep

    @contextmanager
    def lock(self):
        self.state_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self.state_directory / 'deployment.lock'
        try:
            handle = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise DeploymentError('A deployment lock exists; inspect the active deployment before retrying') from error
        os.close(handle)
        try:
            yield
        finally:
            lock_path.unlink()

    def run(self, arguments, release, *, check=True):
        environment = {
            **os.environ,
            'BACKEND_IMAGE_REF': release['backend_image'],
            'FRONTEND_IMAGE_REF': release['frontend_image'],
            'FLOWLY_RUNTIME_ENV_FILE': release['env_file'],
        }
        result = self.runner(arguments, cwd=self.project_directory, env=environment,
                             text=True, capture_output=True)
        if check and result.returncode:
            # Command output may contain configuration secrets. Keep it off CI logs.
            raise DeploymentError(f'{arguments[0]} command failed with exit code {result.returncode}')
        return result

    def compose(self, release, *arguments, check=True):
        command = [
            'docker', 'compose', '--project-directory', str(self.project_directory),
            '--project-name', self.project_name, '--env-file', release['env_file'],
            '-f', release['compose_file'], *arguments,
        ]
        return self.run(command, release, check=check)

    def read_state(self, name):
        path = self.state_directory / name
        if not path.exists():
            return None
        try:
            release = json.loads(path.read_text(encoding='utf-8'))
        except ValueError as error:
            raise DeploymentError('Recorded release state is invalid') from error
        if not isinstance(release, dict):
            raise DeploymentError('Recorded release state is invalid')
        for key in ('backend_image', 'frontend_image'):
            validate_image(release.get(key), allow_local=True)
        if not isinstance(release.get('env_file'), str) or not Path(release['env_file']).is_file():
            raise DeploymentError('Recorded release environment is missing')
        if not isinstance(release.get('compose_file'), str) or not Path(release['compose_file']).is_file():
            raise DeploymentError('Recorded release Compose file is missing')
        return release

    def save_artifact(self, source, release_id, directory_name, suffix):
        source = Path(source).resolve()
        if not source.is_file():
            raise DeploymentError('Release configuration file is missing')
        directory = self.state_directory / directory_name
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = directory / f'{release_id}-{uuid.uuid4().hex}{suffix}'
        handle = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(handle, 'wb') as output, source.open('rb') as runtime:
            shutil.copyfileobj(runtime, output)
        return str(destination)

    def save_environment(self, source, release_id):
        return self.save_artifact(source, release_id, 'environments', '.env')

    def healthy(self, release):
        for attempt in range(self.health_attempts):
            result = self.run([
                'curl', '--fail', '--silent', '--show-error', '--max-time', '5',
                '--output', os.devnull, '--write-out', '%{http_code}', self.health_url,
            ], release, check=False)
            status_code = result.stdout.strip()
            if result.returncode == 0 and status_code.isdigit() and 200 <= int(status_code) < 300:
                return True
            if attempt + 1 < self.health_attempts:
                self.sleep(self.health_interval)
        return False

    def running_images(self, candidate):
        images = {}
        for service in ('backend', 'frontend'):
            container = self.compose(candidate, 'ps', '-q', service).stdout.strip()
            if container:
                image = self.run(['docker', 'inspect', '--format', '{{.Image}}', container], candidate).stdout.strip()
                validate_image(image, allow_local=True)
                images[f'{service}_image'] = image
        if images and len(images) != 2:
            raise DeploymentError('Only part of the previous stack is running; restore or stop it before deploying')
        return images

    def adopt_legacy(self, candidate, environment_file, compose_file):
        previous = {
            'env_file': self.save_environment(environment_file, 'adopted'),
            'compose_file': str((self.project_directory / compose_file).resolve()),
            'backend_image': candidate['backend_image'],
            'frontend_image': candidate['frontend_image'],
            'release_id': 'adopted',
        }
        configuration = json.loads(self.compose(previous, 'config', '--format', 'json').stdout)
        services = configuration.get('services', {})
        if not isinstance(services, dict) or not {'backend', 'frontend'} <= services.keys():
            raise DeploymentError('Legacy Compose must describe the currently running backend and frontend')
        for name, service in services.items():
            container = self.compose(previous, 'ps', '-q', name).stdout.strip()
            if container:
                image = self.run(['docker', 'inspect', '--format', '{{.Image}}', container], previous).stdout.strip()
            elif service.get('image'):
                image = self.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', service['image']], previous).stdout.strip()
            else:
                raise DeploymentError('Legacy service has no running or locally cached image for rollback')
            validate_image(image, allow_local=True)
            service['image'] = image
            service.pop('build', None)
            service.pop('pull_policy', None)
            if name in ('backend', 'frontend'):
                previous[f'{name}_image'] = image
        snapshot = self.state_directory / 'compose' / f'adopted-{uuid.uuid4().hex}.json'
        # Compose's rendered JSON already escapes literal dollars for reuse.
        write_json(snapshot, configuration)
        previous['compose_file'] = str(snapshot)
        return previous

    def stop_removed_services(self, source, target):
        source_services = set(self.compose(source, 'config', '--services').stdout.splitlines())
        target_services = set(self.compose(target, 'config', '--services').stdout.splitlines())
        obsolete = sorted((source_services - target_services) & set(SERVICES))
        if obsolete:
            self.compose(source, 'stop', *obsolete)

    def managed_services(self, release):
        available = set(self.compose(release, 'config', '--services').stdout.splitlines())
        if not {'backend', 'frontend'} <= available:
            raise DeploymentError('Application Compose must contain backend and frontend services')
        return [service for service in SERVICES if service in available]

    def start_applications(self, release):
        self.compose(release, 'up', '-d', '--no-build', '--pull', 'never', '--no-deps',
                     '--wait', '--wait-timeout', str(self.wait_timeout), *self.managed_services(release))

    def restore(self, release, candidate):
        self.compose(release, 'config', '--quiet')
        self.stop_removed_services(candidate, release)
        self.compose(release, 'run', '--rm', '--no-deps', 'backend',
                     'python', 'manage.py', 'collectstatic', '--noinput')
        self.start_applications(release)
        if not self.healthy(release):
            raise DeploymentError('Previous images were restored but their health check failed; operator action is required')

    def apply(self, candidate, previous, *, migrate):
        self.compose(candidate, 'config', '--quiet')
        if migrate:
            self.compose(candidate, 'pull', *self.managed_services(candidate))
        else:
            for reference in (candidate['backend_image'], candidate['frontend_image']):
                if LOCAL_IMAGE.fullmatch(reference):
                    self.run(['docker', 'image', 'inspect', reference], candidate)
                else:
                    self.run(['docker', 'pull', reference], candidate)
        write_json(self.state_directory / 'pending.json', {'candidate': candidate, 'previous': previous})
        try:
            if migrate:
                self.compose(candidate, 'run', '--rm', '--no-deps', 'backend',
                             'python', 'manage.py', 'migrate', '--noinput')
            self.compose(candidate, 'run', '--rm', '--no-deps', 'backend',
                         'python', 'manage.py', 'collectstatic', '--noinput')
            self.start_applications(candidate)
            if previous:
                self.stop_removed_services(previous, candidate)
            if not self.healthy(candidate):
                raise DeploymentError('New application health check failed')
        except (DeploymentError, OSError) as failure:
            if previous:
                try:
                    self.restore(previous, candidate)
                except (DeploymentError, OSError) as recovery:
                    raise DeploymentError('Deployment failed and application rollback failed; database migrations were not reversed') from recovery
                raise DeploymentError('Deployment failed; previous application images and environment restored. Database migrations were not reversed') from failure
            self.compose(candidate, 'stop', *self.managed_services(candidate), check=False)
            raise DeploymentError('First deployment failed; application services stopped and data volumes retained. Database migrations were not reversed') from failure
        else:
            if previous:
                write_json(self.state_directory / 'previous.json', previous)
            write_json(self.state_directory / 'current.json', candidate)
            (self.state_directory / 'pending.json').unlink(missing_ok=True)

    def deploy(self, backend_image, frontend_image, environment_file, release_id, *, adopt_environment=None, adopt_compose=None):
        validate_image(backend_image)
        validate_image(frontend_image)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', release_id):
            raise DeploymentError('Release identifier must contain only letters, digits, underscores and hyphens')
        with self.lock():
            previous = self.read_state('current.json')
            candidate = {
                'backend_image': backend_image, 'frontend_image': frontend_image,
                'env_file': self.save_environment(environment_file, release_id),
                'compose_file': self.save_artifact(self.compose_file, release_id, 'compose', '.yml'),
                'release_id': release_id, 'created_at': datetime.now(timezone.utc).isoformat(),
            }
            running = self.running_images(candidate)
            if running:
                if previous:
                    previous = {**previous, **running}
                elif adopt_environment and adopt_compose:
                    previous = self.adopt_legacy(candidate, adopt_environment, adopt_compose)
                else:
                    raise DeploymentError('Existing containers have no release record; supply --adopt-env-file and --adopt-compose-file for the running stack before the first migration')
            self.apply(candidate, previous, migrate=True)

    def rollback(self):
        with self.lock():
            current = self.read_state('current.json')
            previous = self.read_state('previous.json')
            if not current or not previous:
                raise DeploymentError('No recorded previous release is available')
            self.apply(previous, current, migrate=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-directory', default='.')
    parser.add_argument('--compose-file', default='docker-compose.prod.yml')
    parser.add_argument('--state-directory', default='.flowly-deploy')
    parser.add_argument('--project-name', default='flowly-now')
    parser.add_argument('--health-url', required=True)
    parser.add_argument('--backend-image')
    parser.add_argument('--frontend-image')
    parser.add_argument('--env-file')
    parser.add_argument('--adopt-env-file')
    parser.add_argument('--adopt-compose-file')
    parser.add_argument('--release-id', default=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--health-attempts', type=int, default=30)
    parser.add_argument('--health-interval', type=float, default=2)
    parser.add_argument('--wait-timeout', type=int, default=120)
    options = parser.parse_args()
    if options.health_attempts < 1 or options.health_interval < 0 or options.wait_timeout < 1:
        parser.error('Health and wait limits must be positive')
    try:
        deployment = Deployment(
            options.project_directory, options.compose_file, options.state_directory,
            options.project_name, options.health_url, health_attempts=options.health_attempts,
            health_interval=options.health_interval, wait_timeout=options.wait_timeout,
        )
        if options.rollback:
            deployment.rollback()
        else:
            if not all((options.backend_image, options.frontend_image, options.env_file)):
                parser.error('Deploy requires --backend-image, --frontend-image and --env-file')
            deployment.deploy(options.backend_image, options.frontend_image, options.env_file,
                              options.release_id, adopt_environment=options.adopt_env_file,
                              adopt_compose=options.adopt_compose_file)
    except (DeploymentError, OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print('Application release is healthy. Database migrations were not reversed.')


if __name__ == '__main__':
    main()
