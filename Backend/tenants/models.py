"""
Tenant models for multi-tenancy support.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Tenant(models.Model):
    """Tenant model for multi-tenancy."""

    STATUS_CHOICES = [
        ('active', '活跃'),
        ('suspended', '暂停'),
        ('trial', '试用中'),
        ('cancelled', '已取消'),
    ]

    PLAN_CHOICES = [
        ('free', '免费版'),
        ('starter', '入门版'),
        ('professional', '专业版'),
        ('enterprise', '企业版'),
    ]

    name = models.CharField(max_length=200, verbose_name='租户名称')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='租户标识')
    description = models.TextField(blank=True, verbose_name='描述')

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trial',
        verbose_name='状态'
    )

    # Plan
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='free',
        verbose_name='套餐'
    )

    # Owner
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_tenants',
        verbose_name='所有者'
    )

    # Settings
    settings = models.JSONField(default=dict, verbose_name='设置')
    custom_domain = models.CharField(max_length=255, blank=True, verbose_name='自定义域名')

    # Usage limits
    max_users = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='最大用户数'
    )
    max_workflows = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name='最大工作流数'
    )
    max_executions_per_month = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        verbose_name='每月最大执行次数'
    )

    # Billing
    billing_email = models.EmailField(verbose_name='账单邮箱')
    subscription_id = models.CharField(max_length=255, blank=True, verbose_name='订阅ID')
    subscription_end = models.DateTimeField(null=True, blank=True, verbose_name='订阅到期时间')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'
        verbose_name = '租户'
        verbose_name_plural = '租户'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    """Membership model linking users to tenants."""

    ROLE_CHOICES = [
        ('owner', '所有者'),
        ('admin', '管理员'),
        ('member', '成员'),
        ('viewer', '查看者'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='租户'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_memberships',
        verbose_name='用户'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        verbose_name='角色'
    )

    # Permissions
    permissions = models.JSONField(default=list, verbose_name='自定义权限')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitations_sent',
        verbose_name='邀请人'
    )

    class Meta:
        db_table = 'tenant_memberships'
        verbose_name = '租户成员'
        verbose_name_plural = '租户成员'
        unique_together = ['tenant', 'user']
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} - {self.tenant.name} ({self.role})"

    @property
    def is_admin(self):
        return self.role in ['owner', 'admin']

    @property
    def can_manage(self):
        return self.role in ['owner', 'admin']

    @property
    def can_edit(self):
        return self.role in ['owner', 'admin', 'member']


class TenantInvitation(models.Model):
    """Invitation model for inviting users to tenants."""

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('accepted', '已接受'),
        ('expired', '已过期'),
        ('declined', '已拒绝'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='租户'
    )
    email = models.EmailField(verbose_name='邀请邮箱')
    role = models.CharField(
        max_length=20,
        choices=TenantMembership.ROLE_CHOICES,
        default='member',
        verbose_name='邀请角色'
    )

    # Invitation details
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name='邀请人'
    )
    token = models.CharField(max_length=100, unique=True, verbose_name='邀请令牌')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name='过期时间')
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name='接受时间')

    class Meta:
        db_table = 'tenant_invitations'
        verbose_name = '租户邀请'
        verbose_name_plural = '租户邀请'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} -> {self.tenant.name}"


class TenantUsage(models.Model):
    """Track usage statistics per tenant."""

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='usage',
        verbose_name='租户'
    )

    # Current month usage
    current_month_workflows = models.IntegerField(default=0, verbose_name='本月工作流数')
    current_month_executions = models.IntegerField(default=0, verbose_name='本月执行次数')
    current_month_users = models.IntegerField(default=0, verbose_name='本月用户数')

    # Historical tracking
    total_workflows_created = models.IntegerField(default=0, verbose_name='历史创建工作流数')
    total_executions = models.IntegerField(default=0, verbose_name='历史执行次数')
    total_api_calls = models.IntegerField(default=0, verbose_name='历史API调用数')

    # Token usage (approximate)
    total_tokens_used = models.BigIntegerField(default=0, verbose_name='历史Token使用量')

    # Last updated
    last_reset_at = models.DateTimeField(auto_now=True, verbose_name='最后重置时间')

    class Meta:
        db_table = 'tenant_usage'
        verbose_name = '租户使用量'
        verbose_name_plural = '租户使用量'

    def __str__(self):
        return f"{self.tenant.name} 使用统计"


# ============ Team Skill / Task Assignment Models ============

class TeamSkill(models.Model):
    """Skill model for team task division and assignment."""

    CATEGORY_CHOICES = [
        ('workflow', '工作流'),
        ('agent', 'Agent'),
        ('data', '数据处理'),
        ('integration', '集成'),
        ('monitoring', '监控'),
        ('prompt', '提示词'),
        ('testing', '测试'),
        ('deployment', '部署'),
        ('documentation', '文档'),
        ('other', '其他'),
    ]

    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]

    STATUS_CHOICES = [
        ('available', '可用'),
        ('assigned', '已分配'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('archived', '已归档'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='team_skills',
        verbose_name='所属团队'
    )
    name = models.CharField(max_length=200, verbose_name='技能名称')
    description = models.TextField(blank=True, verbose_name='技能描述')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name='分类'
    )

    # Skill definition
    keywords = models.JSONField(default=list, verbose_name='关键词')
    node_types = models.JSONField(default=list, verbose_name='相关节点类型')
    instructions = models.TextField(blank=True, verbose_name='技能说明')
    examples = models.JSONField(default=list, verbose_name='使用示例')

    # Mastery level required
    mastery_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='所需熟练度(1-5)'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='状态'
    )

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='skills_created',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'team_skills'
        verbose_name = '团队技能'
        verbose_name_plural = '团队技能'
        ordering = ['-created_at']
        unique_together = ['tenant', 'name']

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class SkillAssignment(models.Model):
    """Assignment of skills to team members."""

    ROLE_CHOICES = [
        ('owner', '负责人'),
        ('contributor', '贡献者'),
        ('reviewer', '审核者'),
        ('viewer', '观察者'),
    ]

    skill = models.ForeignKey(
        TeamSkill,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='技能'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='skill_assignments',
        verbose_name='用户'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='contributor',
        verbose_name='角色'
    )

    # Proficiency level for this user
    proficiency_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='熟练度(1-5)'
    )

    # Assignment metadata
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='skills_assigned',
        verbose_name='分配者'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        db_table = 'skill_assignments'
        verbose_name = '技能分配'
        verbose_name_plural = '技能分配'
        unique_together = ['skill', 'user']
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.user.username} - {self.skill.name} ({self.role})"


class TeamTask(models.Model):
    """Task model for team collaboration and work division."""

    STATUS_CHOICES = [
        ('todo', '待处理'),
        ('in_progress', '进行中'),
        ('review', '审核中'),
        ('done', '已完成'),
        ('blocked', '已阻塞'),
        ('cancelled', '已取消'),
    ]

    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='team_tasks',
        verbose_name='所属团队'
    )

    # Task info
    title = models.CharField(max_length=300, verbose_name='任务标题')
    description = models.TextField(blank=True, verbose_name='任务描述')
    category = models.CharField(
        max_length=20,
        choices=TeamSkill.CATEGORY_CHOICES,
        default='other',
        verbose_name='分类'
    )

    # Linked skill
    linked_skill = models.ForeignKey(
        TeamSkill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_tasks',
        verbose_name='关联技能'
    )

    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo',
        verbose_name='状态'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='优先级'
    )

    # Due date
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='截止日期')

    # Assignment
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tasks_owned',
        verbose_name='负责人'
    )
    assignees = models.ManyToManyField(
        User,
        through='TaskAssignee',
        through_fields=('task', 'user'),
        related_name='tasks_assigned',
        verbose_name='协作者'
    )

    # Progress
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='进度(%)'
    )

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tasks_created',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'team_tasks'
        verbose_name = '团队任务'
        verbose_name_plural = '团队任务'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"[{self.tenant.name}] {self.title}"


class TaskAssignee(models.Model):
    """Through model for task assignees."""

    task = models.ForeignKey(
        TeamTask,
        on_delete=models.CASCADE,
        related_name='task_assignees'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_assignments'
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ('owner', '负责人'),
            ('contributor', '贡献者'),
            ('reviewer', '审核者'),
            ('viewer', '观察者'),
        ],
        default='contributor',
        verbose_name='角色'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_assignments_made'
    )

    class Meta:
        db_table = 'task_assignees'
        unique_together = ['task', 'user']


class TeamActivity(models.Model):
    """Activity log for team actions."""

    ACTION_CHOICES = [
        ('skill_created', '创建技能'),
        ('skill_assigned', '分配技能'),
        ('skill_updated', '更新技能'),
        ('task_created', '创建任务'),
        ('task_assigned', '分配任务'),
        ('task_updated', '更新任务'),
        ('task_completed', '完成任务'),
        ('member_joined', '成员加入'),
        ('member_left', '成员离开'),
        ('role_changed', '角色变更'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='所属团队'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='team_activities',
        verbose_name='操作用户'
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name='操作类型')
    target_type = models.CharField(max_length=50, blank=True, verbose_name='目标类型')
    target_id = models.IntegerField(null=True, blank=True, verbose_name='目标ID')
    description = models.TextField(verbose_name='描述')
    metadata = models.JSONField(default=dict, verbose_name='附加数据')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_activities'
        verbose_name = '团队活动'
        verbose_name_plural = '团队活动'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action}"
