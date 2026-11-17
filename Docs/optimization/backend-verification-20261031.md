# 后端最终验证记录 · 2026-10-31

本文记录本轮后端源码冻结后的验证结果，供[应用交付记录](ai-team-product-delivery-20261031.md)引用。Docker 镜像、生产部署和 Chrome 最终验收由主代理另行汇总，本文不提前声明其结果。

## 最终完整回归

在项目实际 `.venv` 中执行标准入口，使用独立 SQLite 内存数据库、独立临时目录和单线程数值库配置：

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
& .venv/Scripts/python.exe tests/run_project_tests.py --basetemp E:/Flowly-now/.cache/pytest-host-final-delay-all-r2
```

最终结果为 **1410 passed、1 skipped、2 warnings、27 subtests passed，133.39 秒（2:13）**。已等待进程真正退出，**退出码为 0**，没有 access violation。完整日志：`.cache/backend-host-final-delay-all-r2.log`。

- 唯一跳过项是 `Backend/training/test_analytics.py::YoloAnalyticsTests::test_symlinked_report_cannot_escape_run_directory`：当前 Windows 账号无法创建符号链接。此项仍需要在具备符号链接能力的环境补测；本文不将其计为通过。
- 两条警告来自原有 VACE/Wan 微型量化前向回归。bitsandbytes 提示输入维度 32 未对齐 blocksize 64，使用较慢内核；测试实际通过。没有屏蔽警告或修改断言。
- 标准入口覆盖项目后端测试目录及 `Backend/training`。本轮没有通过显式重复追加 analytics 路径增加计数；独立 MySQL 并发测试不属于此 SQLite 总数，其结果由主代理另行汇总。

## 关键业务验证

| 范围 | 实际验证与边界 | 证据 |
| --- | --- | --- |
| M4 手工脚本与来源关联 | 脚本要求显式用户参数，创建真实 Workflow、WorkflowExecution 与 NodeExecution。三个微型样本实际执行 CPU `simple-bow` 检索索引，再经 profiler 连接站点生成；只替换站点外部生成边界。`--help` 无需初始化 Django。 | `tests/backend/test_m4_chain_smoke_cli.py`；`.cache/m4-clip-final.log`；最终完整回归 |
| CLIP actor / tenant | 普通非超级用户的检索、分类与站点链使用真实数据库来源记录；分类同时覆盖个人与团队成员执行。TrainingJob 的 actor、tenant、workflow、node、execution 从正在运行的授权记录继承，客户端 config 不能伪造。重模型分类边界使用测试替身，不能据此证明真实模型质量。 | `tests/backend/test_m4_chain_smoke_cli.py`；`tests/backend/test_site_workflow_provenance.py` |
| 工作流 SSE | **14 项**真实路由/执行器回归，覆盖 POST 输入、opaque 业务键、权限、preflight、版本与租户记录、并发门禁、失败终态和关闭连接。实际 Django ASGIHandler 在真实 input 节点仍被同步 barrier 阻塞时已发送前序事件；断线后在途节点允许完成，后续节点停止，记录为 interrupted。已发生的外部副作用不承诺撤回。 | `tests/backend/workflows/test_stream_execute.py`；`.cache/sse-asgi.log` |
| 延时配置与执行控制 | **55 项通过，4.87 秒**。固定/随机、ms/秒/分/时、旧 seconds 优先级与边界、跨午夜窗口及 wait/skip/execute 三策略均有验证。长等待最多每 0.2 秒检查一次控制；暂停保留剩余时长和未完成节点，恢复不重复已完成的循环体或并行兄弟节点。总 deadline 限制等待，取消/timeout 不被迟到结果覆盖。真实 HTTP 路由执行 200ms 流程，首末事件间隔至少 150ms。 | `tests/backend/workflows/test_delay_node.py`；`.cache/delay-final.log` |
| 关联回归 | delay、SSE、应用、子工作流、旧执行器、任务、执行完整性和 preflight 合跑：**167 passed、13 subtests passed，21.23 秒**。此结果是定向关联集，已包含于最终全量验证的覆盖范围，不与 1410 相加。 | `.cache/delay-associated.log` |

延时窗口使用服务端 Django 当前时区。窗口开始包含、结束不包含，支持跨午夜；相同起止时间或无效时间被明确拒绝。窗口外 `wait` 等待下一次开放后执行所配延时，`skip` 跳过延时，`execute` 立即执行所配延时。窗口等待暂停后按恢复时的墙钟重新判断窗口；已经开始的固定/随机延时继续其剩余时长。旧 `seconds` / `delay_seconds` 保留原有优先级、非法值回退和一小时上限，新 UI 单位不会被静默当成一秒或统一截成一小时。

## 全量发现并修复的测试隔离问题

最终回归的上一轮出现 **14 failed、1395 passed、1 skipped、27 subtests passed，126.53 秒**。14 个失败都指向 Torch 重新导入时缺少 `cuda` 属性；该进程随后异常退出。此次失败记录保留在 `.cache/backend-host-final-delay-all.log`，不作为通过证据。

已用最小组合复现：先运行新增 M4 检索链单项，再真实 `import torch`，结果 **1 passed、1 failed，7.54 秒**（`.cache/torch-cli-probe-red.log`）。原因是 M4 的外部生成测试 fixture 把全局 `threading.Thread` 类型替换成普通函数，破坏 Torch 惰性导入中的类型判断；CLIP 可选后端的异常回退留下了半初始化模块状态。

修复只涉及测试 fixture：改为替换 `Thread.start` 方法，仅使站点 `run_gen` 在测试中同步执行，其余线程沿原始 start 方法运行，保留标准 Thread 类型身份；新增类型身份回归。没有清空 `sys.modules`、预先导入 Torch 掩盖顺序问题、删测或屏蔽 CUDA 断言。M4 全部测试与真实 Torch 导入探针随后 **9/9 通过，4.44 秒**（`.cache/torch-cli-probe-green.log`），再执行上文完整标准回归并取得退出码 0。

## GPU 环境与安全限制

宿主保留的实际导入版本如下，未升级或替换 GPU 三包及 CUDA：

| 组件 | 保留版本 |
| --- | --- |
| torch | `2.10.0+cu128` |
| torchvision | `0.25.0+cu128` |
| transformers | `5.8.1` |
| CUDA runtime | `12.8` |

版本与路径核对记录为 `.cache/python-audit-model-import-before.json` / `.cache/python-audit-model-import-after.json`。本轮测试包含原有微型 GPU 量化前向兼容回归，但没有运行真实 GPU 长训练，也不能代替完整模型质量、长时间资源占用或故障恢复验收。

**保留的宿主 torch 2.10.0 源版本仍有两个已识别安全公告，不能声称整个宿主环境零漏洞。** 本地 `+cu128` / `+cpu` 后缀版本被审计工具跳过，也不能当作无漏洞证据。公共声明解析、CPU 构建固定版本和宿主 GPU 环境是不同的验证范围；本文不把其他范围的零公告结果套用到保留的 GPU 栈。

源码已冻结；以上记录不增加业务范围，不包含生产发布承诺。
