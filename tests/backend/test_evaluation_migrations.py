"""Adopt real legacy rows and upgrade their schema without deleting the table."""
from importlib import import_module
from uuid import uuid4
import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import override_settings

pytestmark = pytest.mark.django_db(transaction=True)


def historical_state(table):
    with override_settings(MIGRATION_MODULES={}):
        state = MigrationLoader(connection).project_state([('evaluation', '0001_initial')])
    stored = state.models[('evaluation', 'evaluationjob')]
    stored.options['db_table'] = table
    stored.options['indexes'] = []
    state.reload_model('evaluation', 'evaluationjob')
    return state


@pytest.mark.parametrize('existing', [False, True])
def test_initial_adoption_and_field_migration_preserve_legacy_rows(user, existing):
    table = 'evaluation_probe_' + uuid4().hex[:12]
    state = historical_state(table)
    model = state.apps.get_model('evaluation', 'EvaluationJob')
    initial = import_module('evaluation.migrations.0001_initial').Migration.operations[0]
    try:
        if existing:
            with connection.schema_editor() as editor:
                editor.create_model(model)
        with connection.schema_editor() as editor:
            initial.database_forwards('evaluation', editor, state, state)
        row = model.objects.create(job_id='existing-job', name='Preserve audit', model_path='/old/model.pt',
            created_by_id=user.pk, status='completed', metrics={'accuracy': .75})
        upgrade = import_module('evaluation.migrations.0002_evaluationjob_artifact_snapshot_and_more').Migration
        for operation in upgrade.operations:
            next_state = state.clone()
            operation.state_forwards('evaluation', next_state)
            with connection.schema_editor() as editor:
                operation.database_forwards('evaluation', editor, state, next_state)
            state = next_state
        model = state.apps.get_model('evaluation', 'EvaluationJob')
        upgraded = model.objects.get(pk=row.pk)
        assert upgraded.name == 'Preserve audit' and upgraded.metrics == {'accuracy': .75}
        assert upgraded.created_by_id == user.pk and upgraded.training_job_id is None and upgraded.tenant_id is None
        assert upgraded.parameters == {} and upgraded.artifact_snapshot == {} and upgraded.error_code == ''
        with connection.schema_editor() as editor:
            initial.database_backwards('evaluation', editor, state, state)
        assert model.objects.get(pk=row.pk).name == 'Preserve audit'
    finally:
        assert table.startswith('evaluation_probe_')
        if table in connection.introspection.table_names():
            with connection.schema_editor() as editor:
                editor.delete_model(model)
