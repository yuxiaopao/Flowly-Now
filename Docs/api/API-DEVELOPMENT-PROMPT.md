# Flowly API 开发规范提示词

> 本文件包含用于 AI 编码助手的系统级提示词，确保前后端 API 的一致性实现。

---

## 系统提示词 (System Prompt)

```
你是一位全栈开发专家，正在参与 Flowly AI Workflow Platform 的开发。

## 项目技术栈
- **后端**: Django + Django REST Framework
- **前端**: Vue 3 + Pinia + Axios
- **API 规范**: OpenAPI 3.0 (api-spec.yaml)
- **类型定义**: TypeScript (api-types.ts)

## 核心原则
每次实现 API 功能时，必须**同时**完成以下所有项：

1. **更新 api-spec.yaml** - 添加 OpenAPI 规范定义
2. **实现后端** - views.py → serializers.py → urls.py
3. **实现前端** - api/{module}.js
4. **更新类型** - api-types.ts

## 禁止事项
❌ 只实现后端，不实现前端调用
❌ 只实现前端，不实现后端接口
❌ 前后端字段名不一致 (user_id vs userId)
❌ 前后端数据类型不一致 (string vs number)
❌ API 路径不一致 (/agent/ vs /agents/)
❌ 修改 API 不更新规范文件

## 命名规范
| 层级 | 规范 | 示例 |
|------|------|------|
| 后端字段 | snake_case | created_at, user_id |
| 前端字段 | camelCase | createdAt, userId |
| API 路径 | kebab-case | /workflows/, /user-profile/ |
| 枚举值 | snake_case | draft, active, paused |

## 认证规则
- 公开端点: register, login, refresh, password-reset, prices
- 认证端点: 除上述外的所有端点

## 错误处理
每个 API 必须返回一致的错误格式：
{
  "error": "错误描述",
  "detail": "详细错误信息（可选）",
  "code": "错误代码（可选）"
}

## 实现检查表
在提交代码前，必须确认：
□ api-spec.yaml 已更新
□ 后端视图已实现
□ 后端序列化器已定义
□ URL 路由已注册
□ 前端 API 函数已实现
□ TypeScript 类型已添加
□ 字段名称完全一致
□ 数据类型完全一致
```

---

## API 实现模板

### 后端实现模板

```python
# views.py
class MyResourceViewSet(viewsets.ModelViewSet):
    """我的资源视图集。
    
    端点: /api/v1/my-resources/
    
    请求示例:
        GET  /api/v1/my-resources/          - 列表
        POST /api/v1/my-resources/          - 创建
        GET  /api/v1/my-resources/{id}/     - 详情
        PATCH /api/v1/my-resources/{id}/    - 部分更新
        DELETE /api/v1/my-resources/{id}/    - 删除
    """
    serializer_class = MyResourceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return MyResource.objects.filter(user=self.request.user)
```

```python
# serializers.py
class MyResourceSerializer(serializers.ModelSerializer):
    """我的资源序列化器。
    
    字段映射:
        - id: 资源ID
        - name: 资源名称
        - created_at: 创建时间 (snake_case)
        - updated_at: 更新时间 (snake_case)
    """
    class Meta:
        model = MyResource
        fields = [
            'id', 'name', 'description', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
```

```python
# urls.py
router.register(r'my-resources', MyResourceViewSet, basename='my-resource')
```

### 前端实现模板

```javascript
// api/myResource.js

/**
 * 我的资源 API
 * 
 * API 路径: /api/v1/my-resources/
 */
import request from './request'

export const myResourceApi = {
  /**
   * 获取资源列表
   * @param {Object} params - { page, page_size, search }
   * @returns {Promise<{count, next, previous, results}>}
   */
  getList(params) {
    return request.get('/my-resources/', { params })
  },

  /**
   * 获取资源详情
   * @param {number} id - 资源ID
   * @returns {Promise<MyResource>}
   */
  getById(id) {
    return request.get(`/my-resources/${id}/`)
  },

  /**
   * 创建资源
   * @param {Object} data - { name, description }
   * @returns {Promise<MyResource>}
   */
  create(data) {
    return request.post('/my-resources/', data)
  },

  /**
   * 更新资源
   * @param {number} id - 资源ID
   * @param {Object} data - { name, description }
   * @returns {Promise<MyResource>}
   */
  update(id, data) {
    return request.patch(`/my-resources/${id}/`, data)
  },

  /**
   * 删除资源
   * @param {number} id - 资源ID
   * @returns {Promise<void>}
   */
  delete(id) {
    return request.delete(`/my-resources/${id}/`)
  }
}
```

### TypeScript 类型模板

```typescript
// api-types.ts

/**
 * 我的资源
 */
export interface MyResource {
  id: number;
  name: string;
  description?: string;
  created_at: string;  // snake_case (API 响应)
  updated_at: string;
}

/**
 * 创建资源的请求参数
 */
export interface MyResourceCreate {
  name: string;
  description?: string;
}

/**
 * 更新资源的请求参数
 */
export interface MyResourceUpdate {
  name?: string;
  description?: string;
}
```

### OpenAPI 规范模板

```yaml
# api-spec.yaml

  /my-resources/:
    get:
      tags: [My Resources]
      summary: List my resources
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: page_size
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: List of resources
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      results:
                        type: array
                        items:
                          $ref: '#/components/schemas/MyResource'
    
    post:
      tags: [My Resources]
      summary: Create my resource
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MyResourceCreate'
      responses:
        '201':
          description: Resource created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MyResource'
```

---

## 字段映射规则

### 前后端字段名转换

前端 API 适配器已内置自动转换，无需手动处理：

```javascript
// Frontend/src/api/request.js

// 请求拦截器：自动转换 camelCase -> snake_case
axios.interceptors.request.use(config => {
  if (config.data && typeof config.data === 'object') {
    config.data = toSnakeCaseKeys(config.data)
  }
  return config
})

// 响应拦截器：自动转换 snake_case -> camelCase
axios.interceptors.response.use(response => {
  if (response.data && typeof response.data === 'object') {
    response.data = toCamelCaseKeys(response.data)
  }
  return response.data
})
```

**注意**：由于已内置自动转换，前端代码可以直接使用 camelCase，无需手动转换。

### 类型对应关系

| Python 类型 | TypeScript 类型 | 说明 |
|-------------|-----------------|------|
| str | string | 字符串 |
| int | number | 整数 |
| float | number | 浮点数 |
| bool | boolean | 布尔值 |
| list[str] | string[] | 字符串数组 |
| dict | object / Record | 对象 |
| Optional[str] | string \| null | 可选字符串 |
| datetime | string | ISO 8601 日期字符串 |
| UUID | string | UUID 字符串 |

---

## 常见错误修复提示词

### 错误 1：字段名不一致

```
问题：前端发送 userId，后端期望 user_id

修复：
1. 检查 api-spec.yaml 中定义的字段名
2. 前端适配器转换为 snake_case
3. 确认后端 serializer 使用 snake_case
```

### 错误 2：API 路径不一致

```
问题：前端调用 /agent/，后端定义 /agents/

修复：
1. 参考 api-spec.yaml 中的规范路径
2. 后端：统一使用 /agents/ (复数)
3. 前端：更新 API 函数路径
```

### 错误 3：HTTP 方法错误

```
问题：前端使用 GET 删除资源

修复：
1. GET - 获取资源
2. POST - 创建资源
3. PATCH - 部分更新
4. PUT - 完全替换
5. DELETE - 删除资源
```

### 错误 4：响应字段缺失

```
问题：前端期望 response.data.user_name，后端返回 userName

修复：
1. 在请求拦截器中统一转换字段名
2. 或在后端 serializer 中明确字段名
3. 确保 api-spec.yaml 与实际返回一致
```

---

## API 审计检查表

```markdown
## 审计清单

### 路由审计
- [ ] 所有后端路由都有对应的前端 API 函数
- [ ] 所有前端 API 函数都有对应的后端路由
- [ ] 路径命名一致 (/workflows/ vs /workflow/)

### 字段审计
- [ ] 请求参数字段名完全一致
- [ ] 响应数据字段名完全一致
- [ ] 字段数据类型一致

### 类型审计
- [ ] TypeScript 类型与 Python 类型对应
- [ ] 可选字段正确标记为可选
- [ ] 枚举值拼写一致

### 认证审计
- [ ] 公开端点正确标记 (security: [])
- [ ] 认证端点使用 IsAuthenticated
- [ ] Token 处理逻辑一致
```

---

## 实现检查表

每次实现 API 功能时，必须**同时**完成以下所有项：

| # | 检查项 | 文件位置 | 状态 |
|---|--------|----------|------|
| 1 | 更新 api-spec.yaml | `Docs/api/api-spec.yaml` | 必填 |
| 2 | 实现后端视图 | `Backend/{app}/views.py` | 必填 |
| 3 | 实现序列化器 | `Backend/{app}/serializers.py` | 必填 |
| 4 | 注册 URL 路由 | `Backend/{app}/urls.py` | 必填 |
| 5 | 实现前端 API | `Frontend/src/api/{module}.js` | 必填 |
| 6 | 更新类型定义 | `Docs/api/api-types.ts` | 必填 |
| 7 | 字段名称一致 | 所有文件 | 必填 |
| 8 | 数据类型一致 | 所有文件 | 必填 |

### 公开端点清单 (无需认证)

| 端点 | 说明 |
|------|------|
| POST /auth/register/ | 用户注册 |
| POST /auth/login/ | 用户登录 |
| POST /auth/refresh/ | 刷新 Token |
| POST /auth/password-reset/ | 请求密码重置 |
| POST /auth/password-reset/confirm/ | 确认密码重置 |
| GET /billing/prices/ | 获取价格列表 |

---

## 快速参考卡

### HTTP 方法用途

| 方法 | 用途 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET | 获取资源 | ✓ | ✓ |
| POST | 创建资源 | ✗ | ✗ |
| PUT | 完全替换 | ✓ | ✗ |
| PATCH | 部分更新 | ✗ | ✗ |
| DELETE | 删除资源 | ✓ | ✗ |

### 状态码速查

| 状态码 | 含义 | 前端处理 |
|--------|------|----------|
| 200 | 成功 | 显示数据 |
| 201 | 创建成功 | 跳转或显示 |
| 204 | 删除成功 | 刷新列表 |
| 400 | 参数错误 | 显示错误信息 |
| 401 | 未登录 | 跳转登录页 |
| 403 | 无权限 | 显示权限提示 |
| 404 | 资源不存在 | 显示 404 页面 |
| 500 | 服务器错误 | 显示错误页 |

### API 路径命名

| 资源 | 列表 | 详情 | 创建 | 更新 | 删除 |
|------|------|------|------|------|------|
| workflow | GET /workflows/ | GET /workflows/{id}/ | POST /workflows/ | PATCH /workflows/{id}/ | DELETE /workflows/{id}/ |
| agent | GET /agents/ | GET /agents/{id}/ | POST /agents/ | PATCH /agents/{id}/ | DELETE /agents/{id}/ |

---

*文档版本: 1.1.0*
*最后更新: 2026-05-09*
