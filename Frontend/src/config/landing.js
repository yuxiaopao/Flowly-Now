export const LANDING = Object.freeze({
  eyebrow: '为 AI 应用开发小团队而建',
  title: '让 AI 原型，',
  emphasis: '成为可交付的应用。',
  description: '把团队知识和自动化流程连接起来。用真实输入验证效果，发布固定版本，通过 API 接入，再根据请求记录持续迭代。',
  primary: '进入应用工作区',
  primaryPath: '/applications',
  stages: Object.freeze([
    Object.freeze({ label: '构建', title: '知识与流程，各司其职', detail: '知识助手绑定团队知识库；流程应用复用可视化工作流。构建资源保留独立管理，应用负责交付。', code: '知识库 / 工作流 → 应用草稿', icon: 'Boxes' }),
    Object.freeze({ label: '测试', title: '先看真实输出，再决定发布', detail: '用应用实际运行链路测试输入。资料不足、模型不可用、节点错误都会保留记录，失败的测试不能直接发布。', code: '输入 → 实际运行 → 输出与错误记录', icon: 'FlaskConical' }),
    Object.freeze({ label: '发布', title: '把可用状态固定为一个版本', detail: '发布版本与草稿分开管理。修改源流程不会改写已发布定义，需要时可切换回之前的发布版本。知识库内容持续更新。', code: '成功测试 → 固定版本 → 激活', icon: 'GitBranch' }),
    Object.freeze({ label: '接入', title: '给调用者入口，给团队运行证据', detail: '创建应用专属密钥，通过当前 Flowly 服务的 API 调用。查看请求、错误和耗时，撤销密钥后立即停止授权。', code: '应用密钥 → API → 请求记录', icon: 'Radio' }),
  ]),
  scenarios: Object.freeze([
    Object.freeze({ number: '01', title: '面向客户的知识助手', description: '将产品资料与服务规范整理为知识库，验证回答是否有依据，再提供给业务系统调用。', tags: '文档接入 · 检索测试 · 回答来源' }),
    Object.freeze({ number: '02', title: '团队内部的自动化工具', description: '把整理信息、分类分流和模型调用连接为工作流，发布稳定入口，供已有系统复用。', tags: '可视化编排 · 输入输出 · 固定版本' }),
    Object.freeze({ number: '03', title: '需要持续维护的交付项目', description: '让团队从同一份发布记录与失败请求开始排查，验证修改后再发布，保留可回退的历史。', tags: '成员权限 · 调用记录 · 版本回滚' }),
  ]),
  faqs: Object.freeze([
    Object.freeze({ question: '需要先准备什么？', answer: '需要一个可使用的 Flowly 服务与账户。知识助手需要知识库和回答模型配置；流程应用需要可运行的工作流。没有模型凭证时，系统会明确报告依赖不可用。' }),
    Object.freeze({ question: '发布会自动购买或创建云主机吗？', answer: '不会。发布是在当前 Flowly 服务中激活应用版本与调用 API。对外访问取决于你部署的服务地址、网络和访问配置。' }),
    Object.freeze({ question: '修改草稿会影响正在使用的版本吗？', answer: '已发布工作流使用固定图定义。修改草稿或源流程后，需要重新测试和发布才会切换。知识助手固定检索与提示配置，知识库文档内容会持续更新。' }),
    Object.freeze({ question: '可以看到准确的模型费用吗？', answer: '请求记录保留实际可归因的用量和费用。供应商或执行链路没有提供时显示未知，不把估算 Token 或空值作为实际账单。' }),
    Object.freeze({ question: '团队如何共享应用？', answer: '创建应用时选择团队归属，按照成员角色分配查看、编辑和发布权限。调用密钥只授权对应应用；成员退出或密钥撤销后，授权会失效。' }),
    Object.freeze({ question: '原有的训练与模型网站功能还在吗？', answer: '保留。数据集、训练权重、模型应用网站、向量存储与代码图谱位于高级工具中，可以继续使用原有业务流程。' }),
  ]),
})
