"""Run navigation migration forwards/backwards against real prior table shapes."""
import importlib

import pytest
from django.db import connection, models
from django.db.migrations.state import ModelState, ProjectState


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('has_graph,has_navigation', [(True, True), (False, False), (True, False), (False, True)])
def test_site_navigation_migration_adds_only_missing_columns_and_preserves_initial_data(has_graph, has_navigation):
    table = f'f5_nav_{int(has_graph)}_{int(has_navigation)}'
    fields = [('id', models.AutoField(primary_key=True)), ('name', models.CharField(max_length=200))]
    if has_graph:
        fields.append(('codegraph_project_id', models.IntegerField(null=True, blank=True)))
    if has_navigation:
        fields.append(('show_in_nav', models.BooleanField(default=True)))
    before_state = ProjectState()
    before_state.add_model(ModelState('website_generator', 'GeneratedSite', fields, options={'db_table': table}))
    before = before_state.apps.get_model('website_generator', 'GeneratedSite')
    migration_type = importlib.import_module('website_generator.migrations.0002_generatedsite_nav_codegraph').Migration
    migration = migration_type('0002_generatedsite_nav_codegraph', 'website_generator')
    with connection.schema_editor() as editor:
        editor.create_model(before)
    values = {'name': 'Historical'}
    if has_graph:
        values['codegraph_project_id'] = 42
    if has_navigation:
        values['show_in_nav'] = False
    row = before.objects.create(**values)
    try:
        with connection.schema_editor() as editor:
            after_state = migration.apply(before_state.clone(), editor)
        after = after_state.apps.get_model('website_generator', 'GeneratedSite')
        saved = after.objects.get(pk=row.pk)
        assert saved.codegraph_project_id == (42 if has_graph else None)
        assert saved.show_in_nav is (False if has_navigation else True)
        with connection.schema_editor() as editor:
            migration.unapply(before_state.clone(), editor)
        with connection.cursor() as cursor:
            columns = {column.name for column in connection.introspection.get_table_description(cursor, table)}
        assert ('codegraph_project_id' in columns) is has_graph
        assert ('show_in_nav' in columns) is has_navigation
        original = before.objects.get(pk=row.pk)
        assert original.name == 'Historical'
        if has_graph:
            assert original.codegraph_project_id == 42
        if has_navigation:
            assert original.show_in_nav is False
    finally:
        with connection.schema_editor() as editor:
            editor.delete_model(before)
