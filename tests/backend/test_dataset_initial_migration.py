"""Fresh and adopted datasets schemas both use real database operations."""
from importlib import import_module
from uuid import uuid4

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import override_settings
from datasets.models import Dataset

pytestmark = pytest.mark.django_db(transaction=True)


def migration_state():
    with override_settings(MIGRATION_MODULES={}):
        return MigrationLoader(connection).project_state([('datasets', '0001_initial')])


def test_initial_migration_adopts_existing_table_and_preserves_rows(user):
    row = Dataset.objects.create(created_by=user, name='Existing dataset stays intact')
    module = import_module('datasets.migrations.0001_initial')
    operation = module.Migration.operations[0]
    state = migration_state()
    with connection.schema_editor() as editor:
        operation.database_forwards('datasets', editor, state, state)
        operation.database_backwards('datasets', editor, state, state)
    row.refresh_from_db()
    assert row.name == 'Existing dataset stays intact'
    assert Dataset._meta.db_table in connection.introspection.table_names()


def test_initial_migration_creates_missing_historical_table_and_reverse_preserves_it(user):
    state = migration_state()
    table = 'datasets_initial_probe_' + uuid4().hex[:12]
    state.models[('datasets', 'dataset')].options['db_table'] = table
    indexes = []
    for number, original in enumerate(state.models[('datasets', 'dataset')].options.get('indexes', [])):
        index = original.clone()
        index.name = f'ds_probe_{uuid4().hex[:8]}_{number}'
        indexes.append(index)
    state.models[('datasets', 'dataset')].options['indexes'] = indexes
    state.reload_model('datasets', 'dataset')
    model = state.apps.get_model('datasets', 'Dataset')
    operation = import_module('datasets.migrations.0001_initial').Migration.operations[0]
    try:
        assert table not in connection.introspection.table_names()
        with connection.schema_editor() as editor:
            operation.database_forwards('datasets', editor, state, state)
        row = model.objects.create(created_by_id=user.pk, name='Fresh historical schema')
        with connection.schema_editor() as editor:
            operation.database_forwards('datasets', editor, state, state)
            operation.database_backwards('datasets', editor, state, state)
        assert model.objects.get(pk=row.pk).name == 'Fresh historical schema'
    finally:
        assert table.startswith('datasets_initial_probe_')
        if table in connection.introspection.table_names():
            with connection.schema_editor() as editor:
                editor.delete_model(model)
