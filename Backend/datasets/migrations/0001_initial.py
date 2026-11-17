# Adopt legacy datasets tables; fresh installations create the historical schema.
# Unapplying the initial state preserves an adopted table and its user data.

import datasets.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class EnsureDatasetTable(migrations.SeparateDatabaseAndState):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, 'Dataset')
        if not self.allow_migrate_model(schema_editor.connection.alias, model):
            return
        if model._meta.db_table not in schema_editor.connection.introspection.table_names():
            schema_editor.create_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # Legacy tables predate this migration; reversal must not delete their data.
        pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0002_taskassignee_teamactivity_teamskill_teamtask_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        EnsureDatasetTable(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Dataset",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        ("name", models.CharField(max_length=255, verbose_name="数据集名称")),
                        ("description", models.TextField(blank=True, verbose_name="描述")),
                        (
                            "source",
                            models.CharField(
                                choices=[
                                    ("upload", "本地上传"),
                                    ("url", "URL下载"),
                                    ("s3", "S3存储"),
                                ],
                                default="upload",
                                max_length=10,
                                verbose_name="数据来源",
                            ),
                        ),
                        (
                            "file_path",
                            models.CharField(
                                blank=True, max_length=500, verbose_name="文件路径"
                            ),
                        ),
                        (
                            "file",
                            models.FileField(
                                blank=True,
                                null=True,
                                upload_to=datasets.models.dataset_upload_path,
                                verbose_name="上传文件",
                            ),
                        ),
                        (
                            "url",
                            models.URLField(
                                blank=True, max_length=1000, verbose_name="数据URL"
                            ),
                        ),
                        (
                            "s3_path",
                            models.CharField(blank=True, max_length=500, verbose_name="S3路径"),
                        ),
                        (
                            "s3_bucket",
                            models.CharField(
                                blank=True, max_length=255, verbose_name="S3存储桶"
                            ),
                        ),
                        (
                            "format",
                            models.CharField(
                                choices=[
                                    ("text", "TXT"),
                                    ("csv", "CSV"),
                                    ("json", "JSON"),
                                    ("parquet", "Parquet"),
                                ],
                                default="csv",
                                max_length=10,
                                verbose_name="数据格式",
                            ),
                        ),
                        (
                            "size_bytes",
                            models.BigIntegerField(default=0, verbose_name="文件大小(字节)"),
                        ),
                        ("row_count", models.IntegerField(default=0, verbose_name="行数")),
                        ("column_count", models.IntegerField(default=0, verbose_name="列数")),
                        (
                            "columns",
                            models.JSONField(blank=True, default=list, verbose_name="列信息"),
                        ),
                        (
                            "preview_data",
                            models.JSONField(blank=True, default=list, verbose_name="预览数据"),
                        ),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("pending", "处理中"),
                                    ("ready", "就绪"),
                                    ("error", "错误"),
                                ],
                                default="pending",
                                max_length=20,
                                verbose_name="状态",
                            ),
                        ),
                        (
                            "error_message",
                            models.TextField(blank=True, verbose_name="错误信息"),
                        ),
                        (
                            "metadata",
                            models.JSONField(blank=True, default=dict, verbose_name="元数据"),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                        ),
                        (
                            "updated_at",
                            models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                        ),
                        (
                            "created_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="datasets",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="创建者",
                            ),
                        ),
                        (
                            "tenant",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="datasets",
                                to="tenants.tenant",
                                verbose_name="所属租户",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "数据集",
                        "verbose_name_plural": "数据集",
                        "db_table": "datasets",
                        "ordering": ["-created_at"],
                        "indexes": [
                            models.Index(fields=["tenant"], name="datasets_tenant__db1148_idx"),
                            models.Index(
                                fields=["created_by"], name="datasets_created_ca154c_idx"
                            ),
                            models.Index(fields=["source"], name="datasets_source_11f9a4_idx"),
                            models.Index(fields=["format"], name="datasets_format_bad36b_idx"),
                            models.Index(fields=["status"], name="datasets_status_e5764c_idx"),
                            models.Index(
                                fields=["-created_at"], name="datasets_created_04cf9e_idx"
                            ),
                        ],
                    },
                ),
            ],
        ),
    ]
