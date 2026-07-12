#!/usr/bin/env python
"""
Template Vector Indexing Script

Requires PostgreSQL with pgvector extension.

Usage:
    python scripts/index_templates.py

Environment:
    PG_HOST=localhost
    PG_PORT=5433
    PG_NAME=flowly_vector
    PG_USER=flowly
    PG_PASSWORD=flowly123
    OPENAI_API_KEY=your-key
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workflows.models import WorkflowTemplate


def check_pgvector():
    """Check if PgVector is available."""
    print("Checking PgVector...")
    try:
        from nl_to_workflow.vector_store import PgVectorConnection
        if PgVectorConnection.ensure_extension():
            print("PgVector extension is enabled")
            PgVectorConnection.create_table()
            print("Vector table created")
            return True
        return False
    except Exception as e:
        print(f"PgVector not available: {e}")
        return False


def check_openai_key():
    """Check if OpenAI API key is available."""
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"OpenAI API Key: ****{api_key[-4:]}")
        return True
    else:
        print("Warning: OPENAI_API_KEY not set")
        print("Embeddings will not work without an API key")
        return False


def index_workflow_templates():
    """Index templates using pgvector."""
    from nl_to_workflow.vector_store import TemplateVectorStore

    print("\nIndexing workflow templates (pgvector)...")
    store = TemplateVectorStore()
    templates = WorkflowTemplate.objects.filter(is_active=True)
    total = templates.count()
    print(f"Total templates to index: {total}")

    if total == 0:
        return {'success': 0, 'failed': 0}

    success = 0
    failed = 0
    batch = []

    for template in templates.iterator():
        batch.append({
            'id': str(template.id),
            'name': template.name,
            'description': template.description or '',
            'category': template.category or '',
            'metadata': {
                'created_at': template.created_at.isoformat() if template.created_at else None,
                'is_public': template.is_public,
            }
        })

        if len(batch) >= 50:
            result = store.bulk_index(batch)
            success += result['success']
            failed += result['failed']
            print(f"Processed {success + failed}/{total}...")
            batch = []

    if batch:
        result = store.bulk_index(batch)
        success += result['success']
        failed += result['failed']

    print(f"Success: {success}, Failed: {failed}")
    return {'success': success, 'failed': failed}


def main():
    """Main entry point."""
    print("=" * 50)
    print("Flowly Vector Indexing Tool")
    print("=" * 50)

    # Check PgVector
    print()
    if not check_pgvector():
        print("PgVector is not available. Please ensure PostgreSQL with pgvector is running.")
        print("Docker command: docker run -d --name flowly-pgvector -e POSTGRES_USER=flowly -e POSTGRES_PASSWORD=flowly123 -e POSTGRES_DB=flowly_vector -p 5433:5432 pgvector/pgvector:pg16")
        return 1

    check_openai_key()

    # Index templates
    result1 = index_workflow_templates()

    print("\n" + "=" * 50)
    print("Indexing Complete")
    print(f"  Workflow templates: {result1['success']} success, {result1['failed']} failed")
    print("=" * 50)

    return 0


if __name__ == '__main__':
    sys.exit(main())
