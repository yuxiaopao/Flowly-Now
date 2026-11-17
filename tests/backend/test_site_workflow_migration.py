"""Apply this migration to its actual prior schema, without skipping legacy SQL."""
import copy
import importlib

import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.state import ProjectState
from django.db.migrations.operations.models import CreateModel


@pytest.mark.django_db(transaction=True)
def test_site_source_migration_preserves_history_and_creates_real_constraints(user):
    # The full history includes MySQL-only SQL. Exercise the new operations against
    # a separate, prior-state table in the isolated test DB, preserving that history.
    state = ProjectState.from_apps(apps)
    state.remove_model('website_generator', 'siteworkflowrebuild')
    site_state = state.models['website_generator', 'generatedsite']
    for field in ('source_workflow', 'source_node', 'source_execution', 'source_recorded'):
        site_state.fields.pop(field)
    site_state.options['db_table'] = 'f5_migration_site_before'
    for index, value in enumerate(site_state.options.get('indexes', [])):
        value.name = f'f5_prior_index_{index}'
    before = state.apps.get_model('website_generator', 'GeneratedSite')
    migration_class = importlib.import_module('website_generator.migrations.0008_generatedsite_source_workflow_rebuild').Migration
    migration = migration_class('0008_generatedsite_source_workflow_rebuild', 'website_generator')
    migration.operations = copy.deepcopy(migration.operations)
    for operation in migration.operations:
        if isinstance(operation, CreateModel):
            operation.options['db_table'] = 'f5_migration_rebuild_after'
    after = None
    with connection.schema_editor() as editor:
        editor.create_model(before)
    original = before.objects.create(name='Historical site', created_by_id=user.pk, model_path='/weights/old.pt', output_dir='/old/site')
    try:
        with connection.schema_editor() as editor:
            after = migration.apply(state, editor)
        site_model = after.apps.get_model('website_generator', 'GeneratedSite')
        rebuild_model = after.apps.get_model('website_generator', 'SiteWorkflowRebuild')
        saved = site_model.objects.get(pk=original.pk)
        assert saved.model_path == '/weights/old.pt' and not saved.source_recorded
        assert saved.source_workflow_id is None and saved.source_node_id is None and saved.source_execution_id is None
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, rebuild_model._meta.db_table)
        assert any(item['unique'] and set(item['columns']) == {'site_id', 'user_id', 'key_hash'} for item in constraints.values())
    finally:
        with connection.schema_editor() as editor:
            if after:
                editor.delete_model(after.apps.get_model('website_generator', 'SiteWorkflowRebuild'))
                editor.delete_model(after.apps.get_model('website_generator', 'GeneratedSite'))
            else:
                editor.delete_model(before)
