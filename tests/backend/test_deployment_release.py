"""Exercise deployment outcomes with Docker and curl replaced at their process boundary."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest
import yaml


SCRIPT = Path(__file__).resolve().parents[2] / 'docker' / 'deploy_release.py'
SPEC = importlib.util.spec_from_file_location('flowly_deploy_release', SCRIPT)
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)

NEW_BACKEND = 'registry.example/flowly-backend@sha256:' + 'a' * 64
NEW_FRONTEND = 'registry.example/flowly-frontend@sha256:' + 'b' * 64
OLD_BACKEND = 'sha256:' + 'c' * 64
OLD_FRONTEND = 'sha256:' + 'd' * 64


class ExternalProcesses:
    def __init__(self, *, running=False, bad_new=False, bad_old=False, fail_stage=None, new_status=200, legacy_infrastructure=False):
        self.running = running
        self.bad_new = bad_new
        self.bad_old = bad_old
        self.fail_stage = fail_stage
        self.new_status = new_status
        self.legacy_infrastructure = legacy_infrastructure
        self.calls = []

    def __call__(self, arguments, *, cwd, env, text, capture_output):
        self.calls.append((arguments, env.copy()))
        output = ''
        code = 0
        if arguments[0] == 'curl':
            failed = self.bad_new if env['BACKEND_IMAGE_REF'] == NEW_BACKEND else self.bad_old
            code = 22 if failed else 0
            output = '503' if failed else str(self.new_status if env['BACKEND_IMAGE_REF'] == NEW_BACKEND else 200)
        elif arguments[:2] == ['docker', 'inspect']:
            output = OLD_FRONTEND if arguments[-1] == 'frontend-container' else OLD_BACKEND
        elif arguments[:2] == ['docker', 'compose']:
            command = arguments[arguments.index('-f') + 2:]
            if command[:2] == ['ps', '-q'] and self.running:
                output = f'{command[-1]}-container'
            if command == ['config', '--format', 'json']:
                configuration = {'services': {
                    'backend': {'image': 'legacy-backend:latest', 'build': '.', 'environment': {'TOKEN': 'literal$$VALUE'}},
                    'celery': {'image': 'legacy-backend:latest'},
                    'frontend': {'image': 'legacy-frontend:latest'},
                }}
                if self.legacy_infrastructure:
                    configuration['services']['mysql'] = {'image': 'mysql:8'}
                    configuration['services']['backend']['depends_on'] = {'mysql': {'condition': 'service_started'}}
                output = json.dumps(configuration)
            if command == ['config', '--services']:
                compose_path = arguments[arguments.index('-f') + 1]
                output = '\n'.join(yaml.safe_load(Path(compose_path).read_text())['services'])
            if self.fail_stage == 'pull' and command[0] == 'pull':
                code = 1
            if self.fail_stage == 'migration' and 'migrate' in command:
                code = 1
            if self.fail_stage == 'startup' and command[0] == 'up' and env['BACKEND_IMAGE_REF'] == NEW_BACKEND:
                code = 1
        return subprocess.CompletedProcess(arguments, code, stdout=output, stderr='')

    def compose_calls(self, operation):
        result = []
        for arguments, environment in self.calls:
            if arguments[:2] != ['docker', 'compose']:
                continue
            command = arguments[arguments.index('-f') + 2:]
            if command[0] == operation:
                result.append((command, environment))
        return result


@pytest.fixture
def environment(tmp_path):
    runtime = tmp_path / 'incoming.env'
    runtime.write_text('DB_HOST=new-db\nDJANGO_SECRET_KEY=new-test-secret\n', encoding='utf-8')
    return runtime


def deployment(tmp_path, processes):
    return deploy.Deployment(
        tmp_path, SCRIPT.parents[1] / 'docker-compose.prod.yml', tmp_path / 'state',
        'flowly-now', 'https://configured.example/api/health/',
        runner=processes, sleep=lambda _: None, health_attempts=2,
    )


def previous_release(tmp_path, application):
    runtime = tmp_path / 'old.env'
    runtime.write_text('DB_HOST=old-db\nDJANGO_SECRET_KEY=old-test-secret\n', encoding='utf-8')
    compose = tmp_path / 'old-compose.yml'
    compose.write_bytes(application.compose_file.read_bytes())
    release = {
        'backend_image': OLD_BACKEND, 'frontend_image': OLD_FRONTEND,
        'env_file': str(runtime), 'release_id': 'old-release',
        'compose_file': str(compose),
    }
    deploy.write_json(application.state_directory / 'current.json', release)
    return release


def test_success_records_exact_digests_and_a_private_environment_copy(tmp_path, environment):
    processes = ExternalProcesses()
    application = deployment(tmp_path, processes)
    application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')

    current = application.read_state('current.json')
    assert current['backend_image'] == NEW_BACKEND
    assert current['frontend_image'] == NEW_FRONTEND
    assert Path(current['env_file']) != environment
    assert Path(current['env_file']).read_text() == environment.read_text()
    environment.write_text('changed-after-upload', encoding='utf-8')
    assert 'DB_HOST=new-db' in Path(current['env_file']).read_text()
    assert any('migrate' in command for command, _ in processes.compose_calls('run'))
    command = processes.compose_calls('up')[0][0]
    assert '--no-build' in command and command[command.index('--pull') + 1] == 'never'
    assert not (application.state_directory / 'pending.json').exists()


@pytest.mark.parametrize('failure', ['health', 'migration', 'startup'])
def test_failure_restores_previous_images_and_environment_without_reversing_database(tmp_path, environment, failure):
    processes = ExternalProcesses(running=True, bad_new=failure == 'health', fail_stage=failure)
    application = deployment(tmp_path, processes)
    previous = previous_release(tmp_path, application)

    with pytest.raises(deploy.DeploymentError, match='previous application images and environment restored'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')

    assert application.read_state('current.json') == previous
    restored = processes.compose_calls('up')[-1][1]
    assert restored['BACKEND_IMAGE_REF'] == OLD_BACKEND
    assert restored['FRONTEND_IMAGE_REF'] == OLD_FRONTEND
    assert restored['FLOWLY_RUNTIME_ENV_FILE'] == previous['env_file']
    migrations = [(command, env) for command, env in processes.compose_calls('run') if 'migrate' in command]
    assert len(migrations) == 1
    assert migrations[0][1]['BACKEND_IMAGE_REF'] == NEW_BACKEND
    assert migrations[0][0][-2:] == ['migrate', '--noinput']


def test_first_release_failure_stops_only_applications_and_keeps_data_volumes(tmp_path, environment):
    processes = ExternalProcesses(bad_new=True)
    application = deployment(tmp_path, processes)
    with pytest.raises(deploy.DeploymentError, match='data volumes retained'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'first-release')
    assert processes.compose_calls('stop')[0][0] == ['stop', 'backend', 'celery', 'celery-beat', 'frontend']
    assert processes.compose_calls('down') == []
    assert application.read_state('current.json') is None


def test_failed_rollback_is_reported_as_failure_and_keeps_current_record(tmp_path, environment):
    processes = ExternalProcesses(running=True, bad_new=True, bad_old=True)
    application = deployment(tmp_path, processes)
    previous = previous_release(tmp_path, application)
    with pytest.raises(deploy.DeploymentError, match='application rollback failed'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')
    assert application.read_state('current.json') == previous
    assert (application.state_directory / 'pending.json').exists()


def test_pull_failure_does_not_touch_running_services(tmp_path, environment):
    processes = ExternalProcesses(running=True, fail_stage='pull')
    application = deployment(tmp_path, processes)
    previous_release(tmp_path, application)
    with pytest.raises(deploy.DeploymentError):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')
    assert processes.compose_calls('run') == []
    assert processes.compose_calls('up') == []
    assert processes.compose_calls('stop') == []


def test_mutable_tags_are_rejected_before_any_external_command(tmp_path, environment):
    processes = ExternalProcesses()
    application = deployment(tmp_path, processes)
    with pytest.raises(deploy.DeploymentError, match='never a mutable tag'):
        application.deploy('registry.example/backend:staging', NEW_FRONTEND, environment, 'new-release')
    assert processes.calls == []


def test_legacy_containers_require_their_effective_environment_before_migration(tmp_path, environment):
    processes = ExternalProcesses(running=True)
    application = deployment(tmp_path, processes)
    with pytest.raises(deploy.DeploymentError, match='--adopt-env-file'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')
    assert processes.compose_calls('pull') == processes.compose_calls('run') == []
    assert processes.compose_calls('stop') == []


def test_legacy_adoption_records_actual_running_image_ids_and_old_environment(tmp_path, environment):
    processes = ExternalProcesses(running=True)
    application = deployment(tmp_path, processes)
    old_environment = tmp_path / 'legacy.env'
    old_environment.write_text('DB_HOST=legacy-db\n', encoding='utf-8')
    old_compose = tmp_path / 'legacy-compose.yml'
    old_compose.write_text('services: {}', encoding='utf-8')
    application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release',
                       adopt_environment=old_environment, adopt_compose=old_compose)
    previous = application.read_state('previous.json')
    assert previous['backend_image'] == OLD_BACKEND
    assert previous['frontend_image'] == OLD_FRONTEND
    assert Path(previous['env_file']).read_text() == 'DB_HOST=legacy-db\n'
    configuration = json.loads(Path(previous['compose_file']).read_text())
    assert configuration['services']['backend']['image'] == OLD_BACKEND
    assert configuration['services']['celery']['image'] == OLD_BACKEND
    assert configuration['services']['frontend']['image'] == OLD_FRONTEND
    assert 'build' not in configuration['services']['backend']
    assert configuration['services']['backend']['environment']['TOKEN'] == 'literal$$VALUE'


def test_explicit_rollback_uses_recorded_local_images_without_pulling_mutable_names(tmp_path, environment):
    processes = ExternalProcesses()
    application = deployment(tmp_path, processes)
    previous = previous_release(tmp_path, application)
    deploy.write_json(application.state_directory / 'previous.json', previous)
    current = {
        'backend_image': NEW_BACKEND, 'frontend_image': NEW_FRONTEND,
        'env_file': str(environment), 'release_id': 'new-release',
        'compose_file': previous['compose_file'],
    }
    deploy.write_json(application.state_directory / 'current.json', current)
    application.rollback()
    assert application.read_state('current.json') == previous
    assert application.read_state('previous.json') == current
    assert processes.compose_calls('pull') == []
    assert not any('migrate' in command for command, _ in processes.compose_calls('run'))
    assert any(arguments[:3] == ['docker', 'image', 'inspect'] for arguments, _ in processes.calls)


def test_existing_deployment_lock_is_not_removed_or_bypassed(tmp_path, environment):
    processes = ExternalProcesses()
    application = deployment(tmp_path, processes)
    application.state_directory.mkdir()
    lock = application.state_directory / 'deployment.lock'
    lock.write_text('another-operation', encoding='utf-8')
    with pytest.raises(deploy.DeploymentError, match='deployment lock'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')
    assert lock.read_text() == 'another-operation'
    assert processes.calls == []


def test_absent_previous_environment_cannot_be_used_for_rollback(tmp_path):
    processes = ExternalProcesses()
    application = deployment(tmp_path, processes)
    previous = previous_release(tmp_path, application)
    Path(previous['env_file']).unlink()
    with pytest.raises(deploy.DeploymentError, match='environment is missing'):
        application.rollback()
    assert processes.calls == []


def test_recorded_compose_does_not_change_when_the_next_upload_replaces_input(tmp_path, environment):
    processes = ExternalProcesses()
    incoming = tmp_path / 'incoming-compose.yml'
    original = 'services: {backend: {image: recorded-build}, frontend: {image: recorded-frontend}}\n'
    incoming.write_text(original, encoding='utf-8')
    application = deploy.Deployment(
        tmp_path, incoming, tmp_path / 'state', 'flowly-now', 'https://configured.example/api/health/',
        runner=processes, sleep=lambda _: None,
    )
    application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')
    current = application.read_state('current.json')
    incoming.write_text('services: {backend: {image: a-later-build}}\n', encoding='utf-8')
    assert Path(current['compose_file']).read_text() == original


def test_invalid_health_url_is_rejected_before_migrations_or_external_commands(tmp_path):
    processes = ExternalProcesses()
    with pytest.raises(deploy.DeploymentError, match='absolute HTTP or HTTPS'):
        deploy.Deployment(tmp_path, 'compose.yml', 'state', 'flowly-now', '/api/health/', runner=processes)
    assert processes.calls == []


def test_a_redirect_does_not_pass_release_health_or_skip_rollback(tmp_path, environment):
    processes = ExternalProcesses(running=True, new_status=301)
    application = deployment(tmp_path, processes)
    previous_release(tmp_path, application)
    with pytest.raises(deploy.DeploymentError, match='previous application images and environment restored'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release')
    assert processes.compose_calls('up')[-1][1]['BACKEND_IMAGE_REF'] == OLD_BACKEND


def test_missing_compose_snapshot_never_falls_back_to_an_incoming_new_configuration(tmp_path):
    processes = ExternalProcesses()
    application = deployment(tmp_path, processes)
    previous = previous_release(tmp_path, application)
    previous.pop('compose_file')
    deploy.write_json(application.state_directory / 'current.json', previous)
    with pytest.raises(deploy.DeploymentError, match='Compose file is missing'):
        application.rollback()
    assert processes.calls == []


def test_legacy_rollback_stops_new_beat_without_removing_external_infrastructure(tmp_path, environment):
    processes = ExternalProcesses(running=True, bad_new=True)
    application = deployment(tmp_path, processes)
    old_environment = tmp_path / 'legacy.env'
    old_environment.write_text('DB_HOST=legacy-db\n', encoding='utf-8')
    old_compose = tmp_path / 'legacy-compose.yml'
    old_compose.write_text('services: {}', encoding='utf-8')
    with pytest.raises(deploy.DeploymentError, match='previous application images and environment restored'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release',
                           adopt_environment=old_environment, adopt_compose=old_compose)
    assert processes.compose_calls('stop')[0][0] == ['stop', 'celery-beat']
    assert processes.compose_calls('down') == []


def test_legacy_rollback_does_not_start_or_recreate_database_dependencies(tmp_path, environment):
    processes = ExternalProcesses(running=True, bad_new=True, legacy_infrastructure=True)
    application = deployment(tmp_path, processes)
    old_environment = tmp_path / 'legacy.env'
    old_environment.write_text('DB_HOST=legacy-db\n', encoding='utf-8')
    old_compose = tmp_path / 'legacy-compose.yml'
    old_compose.write_text('services: {}', encoding='utf-8')
    with pytest.raises(deploy.DeploymentError, match='previous application images and environment restored'):
        application.deploy(NEW_BACKEND, NEW_FRONTEND, environment, 'new-release',
                           adopt_environment=old_environment, adopt_compose=old_compose)
    for command, _ in processes.compose_calls('up'):
        assert '--no-deps' in command
        assert 'mysql' not in command
        assert 'backend' in command and 'frontend' in command
    assert all('mysql' not in command for command, _ in processes.compose_calls('pull'))
