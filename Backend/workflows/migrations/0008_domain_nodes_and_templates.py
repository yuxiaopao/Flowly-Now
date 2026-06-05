# Generated migration for Workflow Template System

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency('auth.User'),
        ('users', '0001_initial'),
        ('workflows', '0007_auto_20260513_1416'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemplateCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(blank=True, max_length=50)),
                ('color', models.CharField(default='#8b5cf6', max_length=20)),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'workflows_template_categories',
                'ordering': ['sort_order', 'name'],
            },
        ),
# Disable FK checks for this migration (auth_user doesn't exist, using users.User)
migrations.RunSQL(
    sql="SET FOREIGN_KEY_CHECKS=0",
    reverse_sql="SET FOREIGN_KEY_CHECKS=1",
),

migrations.CreateModel(
    name='WorkflowTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('difficulty', models.CharField(
                    choices=[('beginner', '入门'), ('intermediate', '进阶'), ('advanced', '高级')],
                    default='beginner',
                    max_length=20
                )),
                ('tags', models.JSONField(blank=True, default=list)),
                ('thumbnail_url', models.URLField(blank=True, max_length=500)),
                ('workflow_data', models.JSONField()),
                ('variables_schema', models.JSONField(blank=True, default=list)),
                ('estimated_duration', models.CharField(blank=True, max_length=50)),
                ('required_apis', models.JSONField(blank=True, default=list)),
                ('use_count', models.IntegerField(default=0)),
                ('rating', models.FloatField(default=0.0)),
                ('rating_count', models.IntegerField(default=0)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('version', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='templates',
                    to='workflows.templatecategory'
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='workflow_templates',
                    to='users.user'
                )),
            ],
            options={
                'db_table': 'workflows_workflow_templates',
                'ordering': ['-use_count', '-rating'],
            },
        ),
    ]
