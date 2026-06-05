"""
Shared workspace and team collaboration models.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkspaceType(models.TextChoices):
    """Workspace types."""
    PERSONAL = 'personal', '个人'
    TEAM = 'team', '团队'
    ORGANIZATION = 'organization', '组织'


class MembershipRole(models.TextChoices):
    """Membership roles."""
    OWNER = 'owner', '所有者'
    ADMIN = 'admin', '管理员'
    EDITOR = 'editor', '编辑'
    VIEWER = 'viewer', '查看'


class Workspace(models.Model):
    """Shared workspace for team collaboration."""

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Type
    workspace_type = models.CharField(
        max_length=20,
        choices=WorkspaceType.choices,
        default=WorkspaceType.TEAM,
        verbose_name='类型'
    )

    # Settings
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    allow_guest_access = models.BooleanField(default=False, verbose_name='允许访客访问')

    # Avatar
    avatar = models.URLField(blank=True, verbose_name='头像 URL')

    # Billing (for teams)
    plan = models.CharField(
        max_length=20,
        choices=[
            ('free', '免费'),
            ('pro', '专业版'),
            ('enterprise', '企业版')
        ],
        default='free',
        verbose_name='套餐'
    )

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_workspaces',
        verbose_name='所有者'
    )

    # Limits
    max_members = models.IntegerField(default=5, verbose_name='最大成员数')
    max_workflows = models.IntegerField(default=50, verbose_name='最大工作流数')
    max_storage_gb = models.IntegerField(default=10, verbose_name='最大存储(GB)')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'workspaces'
        verbose_name = '工作空间'
        verbose_name_plural = '工作空间'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()

    @property
    def workflow_count(self):
        return self.workflows.count()

    @property
    def is_at_member_limit(self):
        return self.member_count >= self.max_members


class WorkspaceMember(models.Model):
    """Workspace member."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='工作空间'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
        verbose_name='用户'
    )

    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        default=MembershipRole.VIEWER,
        verbose_name='角色'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', '活跃'),
            ('invited', '已邀请'),
            ('pending', '待确认'),
            ('removed', '已移除')
        ],
        default='pending',
        verbose_name='状态'
    )

    # Invitation
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations',
        verbose_name='邀请人'
    )
    invited_at = models.DateTimeField(null=True, blank=True, verbose_name='邀请时间')
    joined_at = models.DateTimeField(null=True, blank=True, verbose_name='加入时间')

    # Permissions
    can_create_workflow = models.BooleanField(default=True, verbose_name='可创建工作流')
    can_delete_workflow = models.BooleanField(default=False, verbose_name='可删除工作流')
    can_invite_members = models.BooleanField(default=False, verbose_name='可邀请成员')
    can_manage_settings = models.BooleanField(default=False, verbose_name='可管理设置')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workspace_members'
        verbose_name = '工作空间成员'
        verbose_name_plural = '工作空间成员'
        unique_together = ['workspace', 'user']

    def __str__(self):
        return f"{self.workspace.name} - {self.user.username}"

    def can_edit(self):
        """Check if member can edit."""
        return self.role in [MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.EDITOR]

    def can_manage(self):
        """Check if member can manage workspace."""
        return self.role in [MembershipRole.OWNER, MembershipRole.ADMIN]

    def is_owner(self):
        """Check if member is owner."""
        return self.role == MembershipRole.OWNER


class Folder(models.Model):
    """Folder for organizing workflows."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='folders',
        verbose_name='工作空间'
    )

    name = models.CharField(max_length=200, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')

    # Hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='父文件夹'
    )
    path = models.CharField(max_length=500, blank=True, verbose_name='路径')

    # Color and icon
    color = models.CharField(max_length=20, default='#3b82f6', verbose_name='颜色')
    icon = models.CharField(max_length=50, blank=True, verbose_name='图标')

    # Settings
    is_shared = models.BooleanField(default=True, verbose_name='是否共享')
    allow_download = models.BooleanField(default=True, verbose_name='允许下载')

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='folders',
        verbose_name='所有者'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'folders'
        verbose_name = '文件夹'
        verbose_name_plural = '文件夹'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_full_path(self):
        """Get full folder path."""
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name


class WorkspaceInvitation(models.Model):
    """Workspace invitation."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='工作空间'
    )

    email = models.EmailField(verbose_name='邮箱')
    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        default=MembershipRole.VIEWER,
        verbose_name='角色'
    )

    # Invitation details
    token = models.CharField(max_length=100, unique=True, verbose_name='邀请码')
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workspace_invitations_sent',
        verbose_name='邀请人'
    )
    invited_at = models.DateTimeField(auto_now_add=True, verbose_name='邀请时间')

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待确认'),
            ('accepted', '已接受'),
            ('declined', '已拒绝'),
            ('expired', '已过期')
        ],
        default='pending',
        verbose_name='状态'
    )

    # Expiration
    expires_at = models.DateTimeField(verbose_name='过期时间')

    class Meta:
        db_table = 'workspace_invitations'
        verbose_name = '工作空间邀请'
        verbose_name_plural = '工作空间邀请'

    def __str__(self):
        return f"{self.workspace.name} - {self.email}"


class ActivityLog(models.Model):
    """Workspace activity log."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name='工作空间'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workspace_activities',
        verbose_name='用户'
    )

    # Action
    action_type = models.CharField(max_length=50, verbose_name='操作类型')
    action_description = models.TextField(verbose_name='操作描述')

    # Target
    target_type = models.CharField(max_length=50, blank=True, verbose_name='目标类型')
    target_id = models.CharField(max_length=100, blank=True, verbose_name='目标ID')
    target_name = models.CharField(max_length=200, blank=True, verbose_name='目标名称')

    # Details
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 地址')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workspace_activity_logs'
        verbose_name = '活动日志'
        verbose_name_plural = '活动日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action_type}"
