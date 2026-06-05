# 模板系统 / 市场 / Workflow 内嵌模板重复审查

## 审查范围
- `Backend/templates`
- `Backend/marketplace`
- `Backend/workflows` 中模板相关模型、序列化、接口
- `Frontend` 模板市场相关 store / API / 页面

## 结论
当前模板能力被拆成三套并行系统：模板系统、市场系统、workflow 内嵌模板系统。它们不是分层关系，而是重复建设。

## 问题分级

### P0-1 三套模板模型并存，没有统一真相源
- `Backend/templates`
- `Backend/marketplace`
- `Backend/workflows` 中各自都有模板实体/分类/统计能力

#### 影响
- 数据同步不可控
- 发布、安装、使用、评分、收藏统计全部分裂
- 一次字段调整要改三处

#### 建议
- 立即选定唯一模板真相源
- 其余两套只保留适配层或逐步下线

### P0-2 三套 serializer / API 体系并行
同一模板概念，在三个 app 下分别维护列表、详情、分类、创建、使用等 serializer 和 endpoint。

#### 影响
- 返回字段不一致
- 前端必须写兼容分支
- bug 修复成本三倍

#### 建议
- 统一模板 API 入口
- 列表/详情/发布/使用/收藏/评论全部收敛到一条资源线

### P0-3 前端同时消费两套甚至三套模板 API
前端 store 与页面在不同场景下切换调用 marketplace API 与 workflow template API。

#### 影响
- 同一页面里可能混入不同真相源的数据
- 字段名兼容逻辑越来越脏

#### 建议
- 统一前端模板 store
- 统一模板 DTO，彻底删除兼容分支

### P1-1 字段语义冲突严重
例如：
- `use_count` vs `install_count`
- `rating` vs `avg_rating`
- `thumbnail` vs `preview_image` vs `thumbnail_url`
- `access` vs `is_published` vs `is_public`

#### 建议
- 统一字段命名与统计口径
- 先做 DTO 统一，再做底层表迁移

### P1-2 主键类型不一致
模板系统与市场系统使用整型主键，workflow 模板使用 UUID。

#### 影响
- 迁移复杂度高
- API 契约容易出现隐式转换问题

### P1-3 分类模型重复且字段不一致
分类模型在排序、层级、颜色、启用状态等方面都不一致。

### P1-4 tenant 语义不一致
有的模板支持 tenant，有的是全局市场，有的只有 owner/public，没有统一可见性模型。

## 推荐治理路径
1. 选定唯一模板真相源
2. 统一模板 DTO / serializer / endpoint
3. 统一前端模板 store 和页面数据源
4. 迁移旧表数据到唯一模板模型
5. 下线多余 app 或把它们降级为薄适配层
