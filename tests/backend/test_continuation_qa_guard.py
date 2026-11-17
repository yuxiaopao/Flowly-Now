"""The UI acceptance runner must reject ambient services before framework imports."""
import json
import uuid
import pytest
from Scripts.continuation_qa_guard import KIND, local_provider_url, validate_environment
from Scripts.run_continuation_qa import clean_environment


@pytest.fixture
def qa_environment(tmp_path, monkeypatch):
    workspace = tmp_path/'workspace'
    (workspace/'.cache').mkdir(parents=True)
    (workspace/'Backend').mkdir()
    token = uuid.uuid4().hex
    root = workspace/'.cache'/f'continuation-runtime-{token}'
    root.mkdir()
    for name in ('messages', 'processed', 'control', 'media', 'model-artifacts', 'model-datasets', 'backups', 'tmp', 'logs'):
        (root/name).mkdir()
    (root/'manifest.json').write_text(json.dumps({'kind': KIND, 'root': str(root), 'token': token, 'queue': f'continuation-{token}'}))
    (root/'flowly_continuation_settings.py').write_text('')
    monkeypatch.chdir(workspace/'Backend')
    return workspace, root, clean_environment(root)


def test_private_manifest_and_storage_paths_are_verified(qa_environment):
    workspace, root, env = qa_environment
    assert validate_environment(env, workspace=workspace)[0] == root


@pytest.mark.parametrize('key,value', [
    ('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0'),
    ('CELERY_BROKER_READ_URL', 'redis://127.0.0.1:6379/0'),
    ('CELERY_BROKER_WRITE_URL', 'redis://127.0.0.1:6379/0'),
    ('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0'),
    ('DJANGO_SETTINGS_MODULE', 'config.settings'),
    ('PYTHON_DOTENV_DISABLED', '0'),
    ('DATABASE_URL', 'mysql://forbidden'),
    ('OPENAI_API_KEY', 'forbidden-inherited-secret'),
    ('FLOWLY_QA_TOKEN', 'foreign'),
])
def test_guard_rejects_ambient_configuration(qa_environment, key, value):
    workspace, _, env = qa_environment
    env[key] = value
    with pytest.raises(RuntimeError):
        validate_environment(env, workspace=workspace)


def test_child_environment_drops_credentials_and_queue_defaults(qa_environment, monkeypatch):
    _, root, _ = qa_environment
    monkeypatch.setenv('CELERY_BROKER_URL', 'redis://forbidden')
    monkeypatch.setenv('DATABASE_URL', 'mysql://forbidden')
    monkeypatch.setenv('RAG_CHAT_API_KEY', 'secret')
    env = clean_environment(root)
    assert env['CELERY_BROKER_URL'] == 'filesystem://'
    assert not set(('DATABASE_URL', 'RAG_CHAT_API_KEY')) & set(env)


def test_manifest_tampering_is_not_an_owned_runtime(qa_environment):
    workspace, root, env = qa_environment
    manifest = json.loads((root/'manifest.json').read_text())
    manifest['queue'] = 'celery'
    (root/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError):
        validate_environment(env, workspace=workspace)


@pytest.mark.parametrize('url', ['https://external.example/v1', 'http://localhost:22/v1', 'http://127.0.0.1:1234/other',
    'http://127.0.0.1:1234/v1?key=forbidden', 'http://user:password@127.0.0.1:1234/v1'])
def test_provider_metadata_cannot_redirect_to_an_external_service(url):
    with pytest.raises(RuntimeError):
        local_provider_url(url)


def test_provider_metadata_accepts_the_actual_local_fixture():
    assert local_provider_url('http://127.0.0.1:1234/v1') == 'http://127.0.0.1:1234/v1'
