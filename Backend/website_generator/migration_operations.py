"""Schema operations for historical installations with overlapping initial fields."""

from django.core.exceptions import FieldDoesNotExist
from django.db import migrations


class AddFieldIfMissing(migrations.AddField):
    """Add an absent column without replacing data introduced by the initial migration."""

    @staticmethod
    def _has_column(schema_editor, model, column):
        with schema_editor.connection.cursor() as cursor:
            description = schema_editor.connection.introspection.get_table_description(
                cursor, model._meta.db_table
            )
        return any(item.name == column for item in description)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, model):
            return
        if self._has_column(schema_editor, model, model._meta.get_field(self.name).column):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        prior_model = to_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, prior_model):
            return
        try:
            prior_model._meta.get_field(self.name)
        except FieldDoesNotExist:
            current_model = from_state.apps.get_model(app_label, self.model_name)
            column = current_model._meta.get_field(self.name).column
            if self._has_column(schema_editor, current_model, column):
                super().database_backwards(app_label, schema_editor, from_state, to_state)

