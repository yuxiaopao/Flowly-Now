# Generated migration for execution cache models

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0009_add_credential_encryption'),
    ]

    operations = [
        # ExecutionCache model
        migrations.CreateModel(
            name='ExecutionCache',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('config_hash', models.CharField(
                    db_index=True,
                    max_length=64,
                    unique=True,
                    verbose_name='配置哈希'
                )),
                ('node_type', models.CharField(
                    db_index=True,
                    max_length=50,
                    verbose_name='节点类型'
                )),
                ('node_config', models.JSONField(
                    default=dict,
                    verbose_name='节点配置'
                )),
                ('output_data', models.JSONField(
                    default=dict,
                    verbose_name='输出数据'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='创建时间'
                )),
                ('access_count', models.IntegerField(
                    default=0,
                    verbose_name='访问次数'
                )),
                ('last_accessed', models.DateTimeField(
                    auto_now=True,
                    verbose_name='最后访问时间'
                )),
                ('is_valid', models.BooleanField(
                    db_index=True,
                    default=True,
                    verbose_name='是否有效'
                )),
                ('expires_at', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='过期时间'
                )),
                ('checksum', models.CharField(
                    blank=True,
                    max_length=64,
                    verbose_name='校验和'
                )),
            ],
            options={
                'verbose_name_plural': 'Execution caches',
                'db_table': 'execution_cache',
            },
        ),
        
        # Add indexes for ExecutionCache
        migrations.AddIndex(
            model_name='executioncache',
            index=models.Index(
                fields=['node_type', 'is_valid'],
                name='exec_cache_node_i_ab1234_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='executioncache',
            index=models.Index(
                fields=['last_accessed'],
                name='exec_cache_last_a_ab1234_idx'
            ),
        ),

        # ExecutionCacheConfig model
        migrations.CreateModel(
            name='ExecutionCacheConfig',
            fields=[
                ('node_type', models.CharField(
                    max_length=50,
                    primary_key=True,
                    serialize=False,
                    verbose_name='节点类型'
                )),
                ('enabled', models.BooleanField(
                    default=True,
                    verbose_name='是否启用'
                )),
                ('ttl_hours', models.IntegerField(
                    default=24,
                    help_text='Cache TTL in hours',
                    verbose_name='缓存TTL(小时)'
                )),
                ('max_size_mb', models.IntegerField(
                    default=100,
                    help_text='Max cache size per node type in MB',
                    verbose_name='最大缓存大小(MB)'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='创建时间'
                )),
                ('updated_at', models.DateTimeField(
                    auto_now=True,
                    verbose_name='更新时间'
                )),
            ],
            options={
                'verbose_name_plural': 'Execution cache configs',
                'db_table': 'execution_cache_config',
            },
        ),
    ]
