export const APPLICATION_READINESS = Object.freeze({
  title: '运行前检查',
  notice: '检查已保存的资源与服务配置，不会向模型发送请求。配置通过不代表外部连接或回答质量已验证。',
  failed: '检查未能完成，不能据此判断应用可用。',
  statuses: Object.freeze({ pass: '已检查', blocked: '需要处理', warning: '注意', not_checked: '未验证' }),
  targets: Object.freeze({ draft: '已保存草稿', active_release: '线上版本' }),
})
