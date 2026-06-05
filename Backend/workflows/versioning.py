"""
Workflow version models for tracking changes and enabling rollback.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkflowVersion(models.Model):
    """Workflow version for tracking changes."""

    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='工作流'
    )

    version_number = models.IntegerField(verbose_name='版本号')
    name = models.CharField(max_length=200, verbose_name='版本名称')

    # Workflow snapshot
    nodes = models.JSONField(default=list, verbose_name='节点数据')
    edges = models.JSONField(default=list, verbose_name='连接数据')
    variables = models.JSONField(default=dict, verbose_name='变量')

    # Metadata
    description = models.TextField(blank=True, verbose_name='变更描述')
    change_summary = models.TextField(blank=True, verbose_name='变更摘要')

    # Status
    is_auto_save = models.BooleanField(default=False, verbose_name='自动保存')

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_versions',
        verbose_name='创建者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_versions'
        verbose_name = '工作流版本'
        verbose_name_plural = '工作流版本'
        ordering = ['-version_number']
        unique_together = ['workflow', 'version_number']

    def __str__(self):
        return f"{self.workflow.name} v{self.version_number}"

    @property
    def node_count(self):
        return len(self.nodes)

    @property
    def edge_count(self):
        return len(self.edges)


class WorkflowSnapshot(models.Model):
    """
    Point-in-time snapshot of a workflow for backup/restore.
    More comprehensive than versions - includes full workflow metadata.
    """

    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='snapshots',
        verbose_name='工作流'
    )

    name = models.CharField(max_length=200, verbose_name='快照名称')

    # Full workflow data
    workflow_data = models.JSONField(default=dict, verbose_name='完整工作流数据')

    # Tags
    is_auto_created = models.BooleanField(default=False, verbose_name='自动创建')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')

    # Storage info
    size_bytes = models.BigIntegerField(default=0, verbose_name='大小(字节)')

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_snapshots',
        verbose_name='创建者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_snapshots'
        verbose_name = '工作流快照'
        verbose_name_plural = '工作流快照'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.workflow.name} - {self.name}"


class WorkflowDiff(models.Model):
    """
    Diff between two workflow versions.
    """

    workflow = models.ForeignKey(
        'workflows.Workflow',
        on_delete=models.CASCADE,
        related_name='diffs',
        verbose_name='工作流'
    )

    from_version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name='diffs_from',
        verbose_name='源版本'
    )
    to_version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name='diffs_to',
        verbose_name='目标版本'
    )

    # Diff data
    diff_data = models.JSONField(default=dict, verbose_name='差异数据')
    summary = models.TextField(blank=True, verbose_name='差异摘要')

    # Statistics
    nodes_added = models.IntegerField(default=0, verbose_name='新增节点')
    nodes_removed = models.IntegerField(default=0, verbose_name='删除节点')
    nodes_modified = models.IntegerField(default=0, verbose_name='修改节点')
    edges_added = models.IntegerField(default=0, verbose_name='新增连接')
    edges_removed = models.IntegerField(default=0, verbose_name='删除连接')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_diffs'
        verbose_name = '版本差异'
        verbose_name_plural = '版本差异'
        unique_together = ['from_version', 'to_version']

    def __str__(self):
        return f"v{self.from_version.version_number} -> v{self.to_version.version_number}"
