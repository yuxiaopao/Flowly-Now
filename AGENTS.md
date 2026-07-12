# Cursor Agent 全局开发规范

> 强制要求：所有代码实现必须 100% 完整落地，禁止任何形式的省略、简化、阉割、绕过。

---

## 零、对话基本原则（优先级最高）

### 0.1 客观中立原则
- 后续所有对话，优先客观中立分析
- 拒绝迎合讨好，不提供无意义的情绪价值
- 基于事实和逻辑进行判断，不因用户喜好而调整判断
- 保持独立思考，不人云亦云

### 0.2 直言不讳原则
- 回答直接挑问题，不绕弯子
- 逻辑漏洞、认知偏差、不合理的地方，大胆直接指出来
- 不因担心冒犯而回避指出问题
- 问题不会因为不指出而消失，直言是对用户真正负责

---

## 一、全局梳理巡检规则

- 完整遍历项目全部文件，理清整体代码架构、目录层级、业务流转链路
- 全覆盖核查业务模块、接口方法、页面组件、配置文件、公共工具类所有代码内容
- 识别项目技术栈、框架版本、依赖关系、模块边界
- 梳理前后端数据流、组件层级、状态管理流向

---

## 二、死代码清理规则

### 清理范围
- 未调用函数（纯函数但无调用处）
- 闲置变量（定义后未使用）
- 废弃业务逻辑（已无业务场景的代码块）
- 注释封存代码（被注释掉但保留的代码）
- 无效引用（import 后未使用）
- 多余导入依赖（package.json 中未使用的依赖）

### 清理要求
- 仅保留正在使用的有效代码
- 精简项目体积，优化代码整洁度
- 杜绝代码冗余堆积
- 清理后验证功能不受影响

---

## 三、硬编码整改规则

### 排查范围
- 接口地址（API URL、Endpoint）
- 域名端口（Domain、Port）
- 路由地址（Route Path）
- 展示文案（Label、Message）
- 状态值（Status Code、State Value）
- 权限标识（Permission Key、Role）
- 资源路径（Asset Path、Image URL）
- 样式色值（Color Value、Size）
- 时间参数（Timeout、Interval）
- 分页数值（Page Size、Limit）
- 环境密钥（API Key、Token、Secret）
- 配置开关（Feature Flag）

### 整改要求
- 所有固定参数统一抽离
- 归类存入全局配置文件、环境变量、常量枚举、数据字典集中管控
- 彻底摒弃直接写死数值写法
- 全部改为动态读取配置
- 支持后期一键修改、灵活适配多环境

---

## 四、代码规范统一规则

### 统一范围
- 全局编码格式（UTF-8）
- 变量命名规范（camelCase/PascalCase/snake_case 统一）
- 函数命名规范（动词前缀、语义化命名）
- 注释书写规范（统一注释风格，不过度注释）
- 文件命名规范（统一大小写、连字符风格）
- 网络请求封装（统一 Axios/Fetch 封装方式）
- 全局状态管理（统一状态管理方案）
- 组件事件通信（统一 emit/props/redux 模式）

---

## 五、业务流程打通规则

- 打通前后端数据交互链路
- 打通组件传值链路（父子/兄弟/跨级组件）
- 打通页面跳转链路
- 打通全局状态同步链路
- 补齐缺失业务逻辑
- 完善全场景异常捕获与错误处理机制
- 补齐未完成的接口联调
- 完善数据流转完整性

---

## 六、交互体验完善规则

### 用户反馈交互
- 补齐加载动画（Loading、Skeleton）
- 补齐全操作弹窗（Modal、Drawer）
- 补齐结果提示（Toast、Message、Notification）

### 实用功能完善
- 完善权限校验逻辑
- 完善表单校验规则
- 完善数据回显机制
- 完善联动筛选逻辑

### 体验优化
- 修复交互卡顿
- 修复流程断层
- 修复数据不同步问题
- 保障操作流畅顺滑

---

## 七、硬性执行约束铁律

### 7.1 浏览器测试工具约束
- **禁止使用 `cursor-ide-browser` MCP 服务器进行任何形式的浏览器测试**
- 所有浏览器自动化测试操作，必须使用 `chrome-devtools` MCP 服务器
- 不得以任何理由绕过此约束，例如"更方便"、"功能类似"等
- 违反此约束的测试操作一律视为无效

### 7.2 完整性约束
- 严格依照以上所有规则逐条完整执行
- 严禁跳过、省略、简化、屏蔽、删减任意流程与逻辑
- 不得私自保留死代码
- 不得留存硬编码
- 不得简化交互逻辑
- 不得弱化功能实现

### 7.3 业务保护约束
- 不隐性修改原有业务规则
- 不阉割功能分支
- 所有正向流程完整实现
- 所有异常流程完整实现
- 所有边界场景完整实现

### 7.4 验收标准约束
- **架构轻量化** — 无冗余代码、无死代码、无无效依赖
- **代码易维护** — 命名规范统一、注释清晰、结构合理
- **业务易拓展** — 配置集中管理、模块解耦、接口标准化
- **交互全流畅** — 加载反馈完整、异常处理完善、流程无断层

**未达标不得终止优化。**

### 7.5 修改后全面测试再验收约束
- **凡修改代码，必须先自行完成全面测试，再向用户请求验收**
- 不得在未测试或测试未通过的情况下，向用户汇报「已完成」或请用户验收
- 测试范围须覆盖：
  - 本次变更涉及的核心业务正向流程
  - 相关异常与边界场景
  - 可能受影响的关联功能（回归验证）
- 测试手段须包括但不限于（按变更类型选用）：
  - Lint / 类型检查 / 构建编译
  - 单元测试、集成测试（项目已有则必须运行）
  - 接口联调（后端变更或前后端交互变更）
  - 浏览器功能验证（前端/UI 变更，须使用 chrome-devtools MCP，见 7.1）
- 测试发现问题须先自行修复并复测通过，再提交验收
- 向用户汇报时须附带**测试结果摘要**：测了什么、通过/失败情况、已知限制（如有）

---

## 八、冲突解决原则

- 若存在冲突逻辑，**优先遵循用户指定规则**
- 绝不自行做主绕过、屏蔽、废除既定规则
- 如遇问题应如实反馈给用户，等待明确指示后再处理

---

## 九、执行检查清单（每次实现后必查）

- [ ] 全局巡检：项目架构是否清晰？模块边界是否明确？
- [ ] 死代码清理：是否还有未使用函数/变量/导入？
- [ ] 硬编码整改：是否有遗漏的写死数值未抽离？
- [ ] 代码规范：命名/格式/写法是否统一？
- [ ] 业务流程：数据流/状态流/跳转流是否打通？
- [ ] 交互体验：加载/提示/校验是否完整？
- [ ] 功能完整：正向/反向/异常/边界场景是否全覆盖？
- [ ] 浏览器测试：是否使用了正确的 chrome-devtools MCP 而非 cursor-ide-browser？MCP 连接前是否已用独立 Profile 启动 Chrome 并确认调试端口 9222 监听？
- [ ] 全面测试：是否已对本次代码变更完成全面测试并通过？是否已在汇报中附带测试结果摘要？
- [ ] 客观分析：是否基于事实而非迎合？是否直接指出了所有问题？

---

## 十、Chrome DevTools MCP 连接规范

### 10.1 调试端口启动（Windows + 独立 Profile）

Chrome DevTools MCP (`user-chrome-devtools`) 需要 Chrome 以 `--remote-debugging-port=9222` 启动。**必须使用独立 Profile 目录**，否则会被现有 Chrome 进程占用导致端口不监听。

启动步骤：
1. 终止所有 Chrome：`taskkill /F /IM chrome.exe`
2. 创建独立目录（首次）：`New-Item -ItemType Directory -Force -Path "C:\Users\<user>\chrome-debug-profile"`
3. 启动 Chrome 并指定调试端口和独立 Profile：
   ```powershell
   # 正确方式：用 PowerShell Start-Process 的 -ArgumentList 单字符串形式
   Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"C:\Users\<user>\chrome-debug-profile`""
   ```
4. 等待 5 秒后验证：`node -e "require('http').get('http://127.0.0.1:9222/json/version', r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>console.log(d.substring(0,100)))})"`

> **关键教训**：`Start-Process -ArgumentList` 在 Windows 上必须用单字符串形式（参数连写），多参数数组形式会导致 Chrome launcher 丢弃所有参数。`cmd /c start` 也存在同样问题。正确写法即上面的单字符串形式。

### 10.2 MCP 配置

MCP 配置位于 `C:\Users\<user>\.cursor\mcp.json`，`chrome-devtools` 的 `browserUrl` 必须指向 `127.0.0.1` 而非 `localhost`（Windows 上 localhost 可能解析到 IPv6 导致连接失败）：

```json
"chrome-devtools": {
  "command": "npx",
  "args": ["-y", "chrome-devtools-mcp@latest", "--browserUrl=http://127.0.0.1:9222"]
}
```

### 10.3 排查流程
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"C:\Users\18984\chrome-debug-profile`""

| 症状 | 排查命令 | 解决方案 |
|------|---------|---------|
| `Could not connect to Chrome` | `Get-NetTCPConnection -LocalPort 9222` | Chrome 未监听端口，用 `cmd /c start` 启动独立 Profile 实例 |
| 端口监听但 MCP 连接超时 | `node -e "..."` 测试 HTTP | 去掉 MCP 中的 `--experimentalDevtools`，改用 `--browserUrl` |
| PowerShell `Start-Process -ArgumentList` 不生效 | 检查 `Get-CimInstance Win32_Process` 命令行 | Chrome launcher 会丢弃参数，改用 `cmd /c start "" "path" --args` |
| Chrome 闪退 | 检查进程退出码 | 加 `--no-sandbox --disable-gpu` 参数 |
| 无法连接现有 Chrome（已有窗口） | `Get-CimInstance Win32_Process -Filter` 查看命令行 | 必须启动新的独立 Chrome 实例 |
| `Protocol error (Target.getBrowserContexts): Not allowed` | 检查 WebSocket URL | MCP 应连接 `/devtools/browser/<id>` 而非 `/devtools/page/<id>` |
| `Network.enable timed out` | 检查 MCP 参数 | 去掉 `--experimentalDevtools` 标志 |

### 10.4 强制规则

- **严禁**使用 `cursor-ide-browser` MCP 做浏览器自动化测试
- 每次测试前必须确认：`chrome-devtools` MCP 已连接且 `navigate_page` 可用
- 前端服务断线后先验证 `http://localhost:5200` 再继续测试
- 后端断线后先验证 `http://127.0.0.1:8000/admin` 再继续测试

---

## 十一、违规处理

若发现自身有违反上述原则的行为，必须立即纠正并补全被省略/删减/绕过的部分。
