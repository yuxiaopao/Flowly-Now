# 知识库团队空间一致性修复 · 2026-11-01

本记录对应知识库默认存储、显式存储绑定和 Project Agent 记忆的同空间修复。生产与测试源码已冻结；本文只记录已验证范围，不提前声明最终全后端或 Docker 镜像通过。

## 根因与结果

原 `Backend/rag/views.py::DocumentCollectionViewSet.perform_create` 只按 `owner + is_default` 选择存储，创建兜底存储也没有带 tenant。用户已有个人默认存储时，新建团队知识库可能得到“Collection 属于团队、Store 属于个人”的错误绑定。随后创建知识应用会被 `applications.services.resolve_source` 以 `source_unavailable` 拒绝；这是有效的隔离检查，修复没有放宽它。

同一轮核查还发现：显式 Store 的 serializer 只检查可见性，没有检查目标空间；设置 Store 默认标记会清除同 owner 的所有空间默认；Collection PATCH 省略 tenant 时，原 owner 撤销团队成员资格后仍可能写入。Project Agent 的个人记忆和演示数据 helper 也存在只按 owner 选择或清除默认存储的入口。

修复将这些入口统一接到 `Backend/rag/store_scope.py`，保留个人与团队各自的业务空间：

- 自动默认存储按 **owner + tenant** 查找 / 创建。`tenant=None` 仅表示个人空间，不会复用该用户任意团队的默认存储；不同团队之间也不互用。
- 创建或更新默认标记，只清除同 owner、同 tenant 的其他默认标记。默认选择与创建使用 owner 行锁串行化，避免空空间下并发创建时各自选择默认。
- 显式 Collection Store 必须属于同一 tenant；个人知识库还要求 Store 与 Collection 为同一所有者。同团队有可用权限的 Store 可以被授权成员显式引用，不能借此取得 Store 凭证和管理权限。
- Collection 创建和更新都校验有效空间；PATCH 省略 tenant 仍检查原空间。保存前在锁内重新核对当前 Collection / Store，已有绑定的 Store 不能通过单独修改 tenant 把知识库留在另一空间。
- `features/management/commands/seed_demo_data.py` 的存储 helper 仅处理个人空间，不覆盖同名团队 Store，也不清除团队默认标记。本轮只在隔离测试夹具中验证该 helper，没有运行演示数据命令或改写业务记录。

## 当前身份与团队权限

写入要求当前账号有效；团队须为 active / trial，角色为 owner、admin 或 member。viewer、撤销成员资格和停用团队不能创建团队 Store / Collection。团队所有者的固有权限保留。创建、更新及内部分派检查真实数据库状态，不能依赖旧的 request / model 缓存继续写入。

知识库原有管理规则仍生效：修改既有 Collection 需要所有者或团队管理员权限。显式引用同团队 Store 与管理该 Store 是两种权限；普通成员不能因此修改他人的连接参数。无法访问的 Store ID 也可能在 DRF 字段解析阶段直接被拒绝，不会为了统一错误文案而扩大可见范围。

后续真实权限回归又确认：仅修 PATCH 的写入检查还不够。原 `accessible_collections` 和 Store queryset 中的 `Q(owner=user)` 没有限定个人空间，原 `can_manage_collection` 也直接允许 owner，导致团队资源的原创建者离队或团队停用后仍可能 GET、查询、导入和 DELETE。该 owner 旁路现已从公共访问策略移除，未以放宽 App 来源检查来绕过问题。

`Backend/rag/access.py` 统一提供 fresh active actor、有效团队范围、`accessible_collections` / `accessible_stores` 和资源管理判定；`Backend/rag/permissions.py::RAGResourcePermission` 在同一对象权限入口区分读取和写入：

| 当前身份 | 读取与查询 | 写入与删除 |
| --- | --- | --- |
| 个人资源 owner | 仅 `owner=actor AND tenant IS NULL` 的资源 | 管理本人个人资源 |
| active / trial 团队 viewer | 可读可检索同团队内容，包括既有 POST search / ask / pipeline query | 拒绝创建、导入、修改、重处理及删除 |
| active / trial 团队 member | 可读可检索同团队内容 | 仅管理自己的资源；Document / Chunk 的管理跟随 Collection 所有权 |
| active / trial 团队 admin / 实际 tenant.owner | 可读团队资源 | 可管理团队资源；实际团队所有者不依赖额外 membership 行 |
| 离队、团队停用或账号失效 | 团队资源不再因旧 owner 身份可见 / 可用 | 拒绝；不会删除已有内容作为“修复” |

超级用户保留既有团队资源管理权限。普通请求的对象查询先排除失效团队资源，因此通常返回 404；已知但无写权限的对象返回 403。显式创建时给出失效目标 tenant 会先被权限校验拒绝；不可访问的关联 Store ID 也可能按 DRF 字段契约返回 400。以上拒绝均不会产生新文档或删除原分块。

Collection、Store、Document、Chunk 与 RAGPipeline 的正式 HTTP 入口共用该策略，不能靠换成 POST 查询或直接 Document DELETE 绕过。工作流 RAG 与 Agent runtime 原已调用访问 helper；Agent 的知识库绑定校验和详情名称展示也已改为复用它。旧 Agent 知识库 UUID 绑定保留，不暗删关联；权限失效后不显示不可访问详情，实际检索与新绑定均拒绝。

## Project Agent 记忆

`Backend/website_generator/site_factory/project_agent.py` 从 fresh、已授权的真实 `GeneratedSite` 记录读取 tenant，并复用站点 `can_manage_site` 和知识库当前权限。内部 tenant 参数不能覆盖记录中的空间，客户端字段不构成权限依据。

团队项目的新记忆 Collection 和 Store 一起落在相同团队；缺少该空间 Store 时创建同 owner + tenant 的默认存储。个人项目只使用个人 Store，保留原来个人空间没有 Store 时的 missing 分支，不再误取团队默认存储。

已有记忆关联若 Collection 或 Store 跨空间、来源缺失或权限失效，会明确失败；错误类型为 `project_memory_scope`。真实 HTTP 回归确认：旧错误绑定在文件编辑或外部模型操作之前被拒绝，原项目状态、关联及文档保持原样。没有自动迁移、复制、删除或改绑旧记忆，也没有重构系统 Agent 同步的其他分支。

旧项目记忆需要显式重建时，可由有权限的用户使用现有“回到工作流”入口创建项目副本，再按其真实来源和运行配置生成新项目及同空间记忆。底层入口为 `POST /api/v1/website-generator/{site_id}/rebuild-workflow/`，正文 `{}`，携带非空 `Idempotency-Key`；该操作返回副本工作流，不会直接迁移旧知识库或代替后续运行配置。

## 已有错误绑定的显式处理

本轮不批量改写历史绑定、向量内容、业务数据库或 QA 数据。操作者先确认 Collection 的实际文档数量，再选择正式 API 路径。

如果旧知识库**没有文档**，有编辑权限的同团队用户可以先创建 Store，再显式更新原 Collection：

```http
POST /api/v1/rag/vector-stores/
Content-Type: application/json

{"name":"团队本地存储","store_type":"memory","tenant":42,"is_default":true}
```

```http
PATCH /api/v1/rag/collections/{collection_id}/
Content-Type: application/json

{"tenant":42,"vector_store":"<新 Store UUID>","description":"显式修复同空间绑定"}
```

示例 `42` 是待替换的团队 ID；身份必须有该团队和 Collection 的实际编辑权限。创建 Store 成功不代表外部向量服务已经连通。

如果旧知识库**已有文档**，保留原来“不能直接切换 Store”的限制。应创建新的同空间知识库，通过现有上传 / 导入接口重新导入内容，再显式为应用选择新知识库。旧知识库保留，不能为完成演示而偷偷删除内容或绕过迁移限制：

```http
POST /api/v1/rag/collections/
Content-Type: application/json

{"name":"团队知识库副本","tenant":42,"retrieval_mode":"keyword"}
```

省略 `vector_store` 时，新默认逻辑会选择或创建正确的 owner + tenant Store。导入后再创建同 tenant 的知识应用；readiness 仍分别检查内容和平台回答配置，`connection_verified=false` 不会被配置存在冒充为真实连接成功。

## 验证证据与限制

定向测试位于 `tests/backend/test_rag_store_scope.py`，共 **20 项**，覆盖个人 / 两团队默认隔离、真实 HTTP 团队 Collection → 文档导入 → App 创建 → readiness、显式跨空间拒绝、Store 默认标记隔离、viewer / 撤权 / suspended 拒绝、空知识库显式转移、已绑定 Store 不能背后转移、个人 Project 记忆、演示 helper 隔离、真实团队 Project 记忆写入和旧跨空间记忆拒绝。

核心新回归先复现 **10 failed、3 passed**（`.cache/rag-store-scope-red.log`）；另外两个默认调用方问题和团队记忆接缝均有独立红测。修复后，包含上述 20 项及原 RAG、内容事务、应用生命周期、应用回归、readiness、站点 provenance 和 site factory 的最终关联集为 **187 passed，29.79 秒，退出码 0**，日志 `.cache/rag-store-memory-final.log`。20 项属于该集合，不与 187 相加。

中央读写策略的增量位于 `tests/backend/test_rag_space_permissions.py`，最新 **18 passed，4.08 秒，exit 0**，日志 `.cache/rag-space-permissions-post-read.log`。最初 17 项中 **15 failed、2 passed** 复现权限缺口（`.cache/rag-space-permissions-red.log`）；修复后的 RAG / 默认存储 / Agent / App / 安全关联集为 **208 passed，18.98 秒，exit 0**，日志 `.cache/rag-space-permissions-final.log`。最后新增的 viewer POST ask / pipeline query 用例经真实本机模型协议 HTTP 完成两次调用，撤权后 404 且不再调用 provider；上传文件提取内容、metadata 与原 chunk ID 均保留。208 的记录早于该最后一项追加，18 项和 208 项有重叠，不能直接相加。

最新隔离 MySQL 集合 **18 passed，23.50 秒，exit 0**，日志 `.cache/continuation-mysql-release-20261101.log`。在此前 16 项锁与发布边界基础上，新增真实并发两次 POST 同团队默认知识库只创建一个 Store，以及普通 member 创建者撤权后不能读取 / 删除的 HTTP 回归；这不是业务数据库验证。

相关模块编译与 `git diff --check` 通过；全 Backend 的默认存储选择 / 清除入口已用 `rg` 复查，已发现的 owner-only VectorStore 默认入口均复用空间 helper。没有安装依赖、改动 GPU 栈、执行真实 GPU 训练或自动迁移历史数据。最新完整后端、真实 Chrome 总验收和最终 Docker 镜像结果由总交付记录另行汇总。
