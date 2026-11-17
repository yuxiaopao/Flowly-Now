# 本地 API、Worker 与 Beat 生命周期

本入口用于项目本机开发与调试，不替代生产 `docker-compose.prod.yml`、数据库备份或正式发布流程。前端仍单独启动。无参数行为为启动本项目 API、Celery Worker 和 Beat；不再先停止现有进程，不清 Redis、Celery 队列或未确认消息。

## 前置条件

1. 在项目 `.venv` 安装共同依赖，配置 `Backend/.env`，准备数据库和 Redis。
2. 按部署流程备份并显式运行 `Backend/manage.py migrate`。启动器只检查迁移计划，发现未应用迁移会报告 `pending_migrations` 并停止启动；不会自动迁移业务库。
3. 配置实际使用的模型、知识库和外部服务。基础设施就绪不证明模型能回答，启动器始终返回 `models: "not_checked"`，也不会读取登录 token 或替你选用个人模型密钥。

## PowerShell 命令

在项目根目录运行：

```powershell
# 兼容旧入口：启动/精确复用本项目 API、Worker、Beat
.\Scripts\start-flowly-services.ps1

# 分项状态和机器可读结果
.\Scripts\start-flowly-services.ps1 -Action status -Json

# 独立控制角色
.\Scripts\start-flowly-services.ps1 -Action start -Services worker,beat
.\Scripts\start-flowly-services.ps1 -Action restart -Services worker
.\Scripts\start-flowly-services.ps1 -Action stop -Services beat

# 显式停止全部：Beat → Worker → API
.\Scripts\start-flowly-services.ps1 -Action stop

# 调整启动参数需对全部服务显式 restart
.\Scripts\start-flowly-services.ps1 -Action restart -ApiPort 8001 -Workers 4
```

默认监听 `127.0.0.1:8000`，Worker 使用 threads pool，并发 2。地址、端口和并发数的已验证非密钥参数保存在本项目状态目录；后续无参数的 status/stop 使用该记录，无需重复填写端口。原有未纳管进程只有在完整命令、解释器和工作目录均匹配时才会精确复用；发现本项目同角色的不同参数进程会拒绝重复启动并报告冲突，不会直接杀进程。

也可以使用项目 Python 入口：

```powershell
.venv\Scripts\python.exe Scripts\local_service_cli.py --action status --json
.venv\Scripts\python.exe Scripts\local_service_cli.py --action start --services worker beat
```

退出码：`0` 表示所选基础设施已取得就绪证据，或所选进程已确认停止；`2` 表示进程未运行/未就绪或证据不全；`1` 表示配置、归属或操作失败。输出中的 `product_ready` 为 null，不代表全产品可以发布。

## 证据与归属

| 角色 | 启动器确认的证据 | 不据此宣称 |
| --- | --- | --- |
| API | 本机 `/api/health/` 携带配置的 `HEALTHCHECK_HOST` 或 `ALLOWED_HOSTS` 主机头，非重定向响应，数据库和 Redis/cache 均 connected | 每个业务路由、模型、向量库都可用 |
| Worker | 当前工作区专属完整节点名称实际响应 bounded ping | 任意其他 Worker 的响应等于本项目就绪 |
| Beat | 当前 PID、创建时间、工作区和完整命令匹配的新鲜调度 tick 心跳 | 仅进程存在即调度就绪，或每个业务周期都已完成 |

start/status 会检查目标配置及数据库迁移状态，访问本机健康接口，并向本项目唯一 Worker 节点发送控制 ping。stop 不要求 Django 配置可加载，便于修复配置错误后仍能停止自己启动的服务。启动后未就绪的存活进程会保留归属记录与日志，供诊断和显式停止，不会被冒充成功或清空其队列。

状态和日志位于 `.cache/local-services/`。每个进程记录包含工作区指纹、PID、创建时间、实际解释器、完整启动参数和工作目录；停止前重新核对。PID 已复用、身份改变、工作区不符、归属无法确认时拒绝操作。生命周期锁由操作系统管理，控制器崩溃后自动释放，不靠盲目删除其他进程的锁恢复。Windows 虚拟环境产生的原生 Python 子进程按实际归属处理，系统控制台 host 不是进程杀除目标。

停止会向已验证进程树发送终止信号并确认退出；超时会报告失败，不悄悄强杀或启动替代进程。停止/重启并不撤回已发生的外部副作用，请先按业务流程处理正在运行的任务。当前入口没有 purge、删除 unacked 或停止其他项目的命令选项。

## 2026-11-01 验证与隔离记录

测试通过公开生命周期操作使用真实临时 helper 进程，覆盖幂等复用、独立角色、跨项目和 PID 复用拒绝、启动失败、真实控制器崩溃恢复、并发启动及不明参数冲突。真实 Celery 测试只使用临时 filesystem broker 和 memory result backend：Beat 实际投递、Worker 实际完成任务，另一个未消费队列逐字节保留，结束后相关进程全部停止。

第一轮 Celery fixture 发生过一次环境隔离错误：构建环境中的删除标记在最终合并时丢失，导致父环境 broker 地址被恢复。日志确认测试 Worker 意外连接 Redis，在 Mingle 握手阶段失败退出，Beat 未启动；没有执行 purge/delete，未观察到业务 task 接收/执行。不能据此宣称完全没有控制通道临时元数据。之后未再次连接该 Redis 诊断或补偿，也未清理其数据；残留 fixture 进程核查为 0。

修复后，删除语义通过最终实际子进程验证；fixture 采用环境 allowlist，并在任何 Django/Celery 导入前以纯标准库 guard 验证临时路径、manifest/token、filesystem broker、memory backend、唯一队列和节点。错误地址、真实项目路径和身份不符均在连接前拒绝。后续真实 Worker/Beat 验证均经过此门禁。

本域最终定向测试 25 项全部通过；关键日志为 `.cache/local-services-final-r6.log`、`.cache/local-service-env-proof.log`、`.cache/local-service-guard-proof.log`、`.cache/local-services-isolated-worker-r2.log`。实际 PowerShell 入口另在复制的临时工作区验证 stop/status/start 配置失败路径；该工作区通过 import guard 禁止 Django/Celery/Redis/Kombu 导入，没有操作现有服务或队列。
