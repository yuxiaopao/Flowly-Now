---
name: visio-dfd
description: Draw software-engineering data-flow diagrams in local Microsoft Visio via COM (Yourdon circles or Gane-Sarson), with straight or orthogonal flows. Use when the user asks for 数据流图, DFD, Visio, .vsdx, Gane-Sarson, Yourdon, 正圆加工, 走线, or to redraw messy connectors.
---

# 用本地 Visio 画数据流图

不要用 Pillow/matplotlib 冒充「Visio 图」。用户给出 Office 路径时，用本机 `VISIO.EXE` + `win32com`。

默认交付：`.vsdx` + 每页导出 PNG。改完必须读 PNG 看走线，不能只看脚本。

## 符号（听用户最后一句）

| 用户说的 | 加工 | 实体 | 存储 | 数据流 |
|---------|------|------|------|--------|
| 正圆 / Yourdon / 别用圆角方形 | `DrawOval` 等宽等高 | 方框 | 开口矩形 | **直线**（默认） |
| Gane-Sarson / 模具 | `GANESA_M.VSSX`「流程」 | 「接口」 | 「数据存储」 | 正交或直线，以用户为准 |
| 走线太乱 / 别折线 / 用直线 | 保持加工形状 | 同左 | 同左 | **只画直线**，禁止 visio 自动直角改道 |

中文模具：`C:\Program Files\Microsoft Office\root\Office16\Visio Content\2052\GANESA_M.VSSX`。

## 生成循环

1. `taskkill /F /IM VISIO.EXE`，删旧 vsdx，再 COM 启动。
2. 画完 `SaveAs` + `page.Export(png)`。
3. 用 Read 打开每张 PNG。穿框、绕页、箭头在错误一端 = 未完成。
4. 改脚本再跑。列出 masters 后 `Quit` 可能挂死，直接杀进程。

本机 Word COM 可能失败；Visio `Visio.Application` 16.0 可用。

## 直线数据流（优先）

从中心指向目标，交于圆周或矩形边，再 `DrawLine`。

- 成对进出：同一对形状用垂直于连心线的 `offset`，两条平行直线。
- 读写存储：一条线，两端箭头（`EndArrow=13`，`BeginArrow=13`）。
- **禁止** `ConnectorToolDataObject` + `ShapeRouteStyle=1` 画回程：Visio 会从形状右侧出发绕一整圈。
- **禁止** `DrawPolyline` 当箭头线：得到的是二维形状，箭头会变成白方块。分段用 `DrawLine`。
- 不要把三个形状放在同一条中心线上（例如 4.3、4.6、D6 同 x），直线必穿中间那个。

几何与 COM 细节见 [reference.md](reference.md)。

## 布局（先摆位置，再连线）

分层：左实体 → 中加工 → 右存储/外部服务。1 层图让外部实体只贴一个加工，避免回程横穿整页。

作业口径：顶层=加工 0；0 层=1.0–5.0；垂直模板（短剧/苗绣/CUMCM）属于 2.3，不是 0 层。用户在语创 1 层只与 2.1 交换数据。

## 验收

- 加工是用户要的形状（正圆或 Gane-Sarson），不是「看起来圆的圆角方」。
- 没有直角折返绕页。
- 直线不穿过无关圆/存储；标签不压在符号上。
- vsdx 能用本机 Visio 打开。
