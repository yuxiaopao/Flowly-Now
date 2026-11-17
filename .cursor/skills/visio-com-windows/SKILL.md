---
name: visio-com-windows
description: Automate local Microsoft Visio on Windows with win32com. Use when generating .vsdx, dropping stencils, drawing shapes/connectors, exporting PNG, or when Visio COM hangs, arrows look wrong, or Word COM fails but Visio is installed.
---

# Windows 上的 Visio COM

Office 16 典型路径：`C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE`。

## 能用 / 不能用

- `Dispatch("Visio.Application")` 可用。
- 同机 Word COM 可能 `TYPE_E_CANTLOADLIBRARY`。Word 改用 `python-docx`；图画仍走 Visio。
- 列举 masters 后调用 `Quit` 会挂。需要重启时 `taskkill /F /IM VISIO.EXE`。

## 画线

- 一维箭头：`page.DrawLine(x1, y1, x2, y2)`，再设 `EndArrow`。
- `DrawPolyline` 得到二维形状，箭头会糊成方块。
- `ConnectorToolDataObject` 会自动直角改道。回程若仍从形状右侧胶水，会绕页一周。要直线就自己算端点，不要交给路由器。

## Drop 模具

中文 Gane-Sarson：`Visio Content\2052\GANESA_M.VSSX`，masters「流程」「接口」「数据存储」。

Drop 后把 `LocPinX/Y` 设为宽高一半，再写 `PinX/PinY`。存储类 master 的默认针脚经常不在中心。

## 导出

`page.Export(abs_png_path)`。先删旧 PNG。导出后用读图工具看，不要只信 COM 返回成功。
