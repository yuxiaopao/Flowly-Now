# Frontend 路由 / 状态 / API 协议审查

## 审查范围
- `Frontend/src/router`
- `Frontend/src/stores`
- `Frontend/src/api`
- `Frontend/src/views`
- `Frontend/src/utils/workflowTransform.*`

## 结论
前端当前的主要问题不是“UI 不好看”，而是状态域边界失控、路由守卫不完整、与后端协议漂移。这些已经开始直接损坏业务行为。

## 问题分级

### P0-1 Store 职责膨胀
`tenant` store 混装了 tenant、member、skill、task、activity 等多个域。

#### 影响
- 状态耦合过重
- 任意修改都会提高回归风险
- 后续多人协作会持续互相污染

#### 建议
- 按业务域拆 store
- tenant 只保留租户相关状态

### P0-2 路由守卫缺少管理员校验
路由元信息定义了管理员要求，但守卫未真正执行。

#### 影响
- 已登录但非管理员用户可能直接进入管理页面

#### 建议
- 在统一路由守卫中补 `requiresAdmin` 校验
- 不要把管理员判断散落在页面内部兜底

### P0-3 前后端协议漂移：工作流发布状态不一致
前端仍保留 `isPublished` 之类历史语义，而后端主语义依赖 `status`。

#### 影响
- 发布状态在提交/读取链路中错位
- 会出现前端显示已发布、后端实际未发布的假象

#### 建议
- 删除前端历史兼容字段
- 统一以 `status` 为唯一发布态语义

### P1-1 执行状态重复存储
`workflow` store 与 `execution` store 对执行态有重复持有。

### P1-2 节点类型映射双维护
前后端都维护一份节点类型映射，新增节点时非常容易漏改。

### P1-3 Token 双写
认证 token 同时写 cookie/localStorage，增加泄漏面和同步负担。

### P1-4 API 命名与路由命名不一致
不同模块 CRUD/执行命名风格不统一，路径风格也不统一。

### P1-5 页面域命名与数据域命名不一致
如 knowledge / collections / rag 概念混用，降低可维护性。

## 推荐治理路径
1. 先修管理员守卫与发布状态协议
2. 拆 tenant store
3. 合并执行状态来源
4. 收敛节点类型映射
5. 收敛 token 存储策略与路由/API 命名规范
