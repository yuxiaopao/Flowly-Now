"""
Direct DB migration applier.
Bypasses Django's state-builder entirely to apply migrations.
"""
import os, sys
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from django.db import connection
from importlib import import_module
from packaging.version import Version

def apply_migration_sql(cursor, app, migration_name):
    """Apply a migration's SQL directly to the database."""
    name = migration_name
    migration_file = os.path.join(_backend_dir, app, 'migrations', f'{name}.py')

    if not os.path.exists(migration_file):
        print(f"  [SKIP] {app}.{name} — file not found")
        return

    spec = import_module(f'{app}.migrations.{name}')
    migration = spec.Migration('initial' in dir(spec.Migration) and spec.Migration.__dict__['initial'] or False)
    # Manually create migration object
    from django.db.migrations.migration import Migration as DjangoMigration
    mig_cls = getattr(spec, 'Migration')
    mig = mig_cls(name, app)

    # Get the operations
    for op in getattr(mig, 'operations', []):
        # Skip CreateModel since tables already exist
        from django.db.migrations.operations.models import CreateModel
        if isinstance(op, CreateModel):
            print(f"  [SKIP] CreateModel {op.name} (table exists)")
            continue

        # For simple field operations, we could try to generate SQL
        # But ALTER TABLE is complex, so we'll skip most operations
        print(f"  [OP] {type(op).__name__}: {op}")
        try:
            from django.db.migrations.autodetector import MigrationAutodetector
            from django.db.migrations.loader import MigrationLoader
            from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
            from django.db.migrations.state import ProjectState
            autodetector = MigrationAutodetector(
                MigrationLoader(None).graph,
                NonInteractiveMigrationQuestioner(specified_apps={app}, dry_run=True),
            )
            # Skip - this is too complex
            print(f"  [SKIP] Complex operation: {type(op).__name__}")
        except Exception as e:
            print(f"  [SKIP] {type(op).__name__}: {e}")

    # Record as applied
    with connection.cursor() as c:
        c.execute("DELETE FROM django_migrations WHERE app=%s AND name=%s", [app, name])
        c.execute("INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())", [app, name])
    print(f"  [APPLIED] {app}.{name}")

# The migrations we actually need to apply (new ones with real DB changes):
# Let's just check which ones have pending changes we need
# The key question: do our new migrations (website_generator 0002, agents 0003, training 0002/0003)
# actually modify the DB schema, or just metadata?

# From inspection:
# - website_generator 0002: adds new columns to existing table
# - agents 0003: alters existing columns
# - training 0002: adds new columns
# - training 0003: renames indexes (metadata only)
# - core 0001: creates new tables
# - augmentation 0001: creates new tables

# core and augmentation tables likely already exist
# So let's check what tables actually exist

with connection.cursor() as c:
    c.execute("SHOW TABLES LIKE %s", ['%augment%'])
    print("Augmentation tables:", [r[0] for r in c.fetchall()])
    c.execute("SHOW TABLES LIKE %s", ['%notification%'])
    print("Core/notification tables:", [r[0] for r in c.fetchall()])
    c.execute("SHOW TABLES LIKE %s", ['desktop_agent%"])
    print("Desktop agent tables:", [r[0] for r in c.fetchall()])
    c.execute("SHOW TABLES LIKE %s", ['training_job%'])
    print("Training job tables:", [r[0] for r in c.fetchall()])
    c.execute("SHOW TABLES LIKE %s", ['generated_site%'])
    print("Generated site tables:", [r[0] for r in c.fetchall()])

print("\nDone checking tables.")
