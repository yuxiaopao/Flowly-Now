export const APPLICATION_WORKFLOW_TRACE = Object.freeze({
  statuses: Object.freeze({
    pending: '等待执行', queued: '排队中', running: '运行中', paused: '已暂停',
    completed: '已完成', failed: '失败', cancelled: '已取消', interrupted: '已中断',
    skipped: '已跳过', retrying: '重试中', timeout: '已超时', waiting: '等待中'
  })
})
