export const PERSONAL_CENTER = Object.freeze({
  title: '个人中心',
  subtitle: '管理账户、连接服务与工作空间偏好',
  navigationLabel: '个人中心设置',
  groups: [
    { key: 'account', label: '账户', items: ['profile', 'avatar', 'preferences', 'notifications', 'billing'] },
    { key: 'connections', label: '连接与服务', items: ['credentials', 'integrations', 'api-doc', 'desktop-agent'] },
    { key: 'workspace', label: '工作空间', items: ['data-export', 'branding'] },
  ],
})

export const PROFILE_LIMITS = Object.freeze({
  username: 150,
  email: 254,
  name: 150,
  phone: 20,
  bio: 500,
  passwordMin: 8,
  avatarBytes: 2 * 1024 * 1024,
  avatarTypes: ['image/jpeg', 'image/png'],
  avatarAccept: '.jpg,.jpeg,.png',
  avatarSize: 56,
  bioRows: 3,
})

export const PROFILE_COPY = Object.freeze({
  title: '个人资料', subtitle: '更新账户资料，管理头像与登录密码',
  basicTitle: '账户资料',
  securityTitle: '账户安全', securityDescription: '使用独立的强密码，避免与其他服务共用。',
  avatarLabel: '个人头像', passwordLabel: '登录密码',
  openPassword: '修改密码', closePassword: '收起密码表单',
  username: '用户名', email: '邮箱', firstName: '名', lastName: '姓', phone: '手机号', bio: '个人简介',
  usernameHint: '支持字母、数字、中文及 @ . + - _',
  bioPlaceholder: '介绍你的工作方向或擅长领域',
  designAvatar: '设计 AI 头像', upload: '上传图片', remove: '移除图片', avatarHint: '默认使用动态机器人。也可主动上传 JPG 或 PNG 图片，最大 2 MB。',
  avatarAlt: '账户头像', avatarTypeError: '请选择 JPG 或 PNG 图片', avatarSizeError: '头像大小不能超过 2 MB',
  avatarSuccess: '头像已更新', avatarRemoved: '头像已移除', avatarError: '头像操作失败，请重试',
  save: '保存更改', reset: '撤销更改', unsaved: '有未保存的更改', saved: '资料已同步',
  profileSuccess: '个人资料已更新', profileError: '保存失败，请检查输入后重试',
  loadError: '无法加载账户资料，请重试', retry: '重新加载',
  oldPassword: '当前密码', newPassword: '新密码', confirmPassword: '确认新密码',
  passwordHint: '至少 8 个字符，避免纯数字、常见密码和与账户信息相似的密码。',
  changePassword: '更新密码', passwordSuccess: '密码修改成功', passwordError: '密码修改失败，请重试',
  requiredUsername: '请输入用户名', invalidUsername: '用户名包含不支持的字符',
  requiredEmail: '请输入邮箱', invalidEmail: '请输入有效的邮箱地址',
  requiredOldPassword: '请输入当前密码', requiredNewPassword: '请输入新密码',
  shortPassword: '密码至少 8 个字符',
  requiredConfirmation: '请确认新密码', mismatch: '两次输入的密码不一致',
  leaveTitle: '未保存的资料', leaveMessage: '离开后，本次尚未保存的资料更改将丢失。',
  leave: '离开', stay: '继续编辑',
})

export const PREFERENCE_CONFIG = Object.freeze({
  defaultTheme: 'dark',
  storageKey: 'user_preferences', autoSaveIntervalMs: 30000,
  defaults: { autoSave: true, snapToGrid: true, showMinimap: true },
  title: '偏好设置', subtitle: '选择界面主题，调整工作流编辑习惯',
  appearance: '界面外观', theme: '主题', themeDescription: '主题切换后立即生效。',
  editor: '工作流编辑器', editorDescription: '保存在当前浏览器，应用于工作流编辑器。',
  items: [
    { key: 'autoSave', label: '自动保存', description: '每 30 秒保存已有工作流的更改，新建工作流需先手动保存。' },
    { key: 'snapToGrid', label: '对齐网格', description: '拖动节点时自动对齐画布网格。' },
    { key: 'showMinimap', label: '显示迷你地图', description: '缩放画布时显示导航预览，停止操作后自动收起。' },
  ],
  reset: '恢复默认', save: '保存设置', saved: '设置已保存', savedStatus: '已使用保存的偏好', unsaved: '有未保存的更改',
  error: '无法保存设置，请检查浏览器的存储权限后重试',
  autosaveError: '自动保存失败，更改仍保留，请手动保存',
})
