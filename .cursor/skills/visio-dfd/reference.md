# Visio COM 与走线几何

## 启动

```python
os.system("taskkill /F /IM VISIO.EXE >nul 2>&1")
time.sleep(1.6)
visio = win32com.client.Dispatch("Visio.Application")
visio.Visible = True
visio.AlertResponse = 6
stencil = visio.Documents.OpenEx(STENCIL, 4)  # visOpenDocked
```

页：A3/A4 横向常用 `PageWidth=420 mm`，`PageHeight=297 mm`，`PrintPageOrientation=2`。

## 正圆加工

```python
shp = page.DrawOval(x - r, y - r, x + r, y + r)
shp.Data1 = "circle"
```

`Drop` Gane-Sarson「流程」再把宽高拉成正方形 **不是** 正圆，仍是圆角矩形。

## 模具形状的针脚

Gane-Sarson「数据存储」的 Pin 往往不在几何中心。Drop 之后强制：

```python
shp.CellsU("LocPinX").ResultIU = w / 2
shp.CellsU("LocPinY").ResultIU = h / 2
shp.CellsU("PinX").ResultIU = x
shp.CellsU("PinY").ResultIU = y
```

否则按 Pin 算的直线会穿框。

## 边界点

圆：`center + u * (min(w,h)/2 * 0.98)`  
矩形：射线与 AABB 先碰到的边，`t = min((w/2)/|ux|, (h/2)/|uy|)`。

## 平行偏移

```text
u = dest - src  单位向量
p = (-uy, ux)
两端各加 p * offset
```

同一对上的去程和回程都用 **正** offset：方向相反时法向也反，两条线会分居中心线两侧。

大 offset 会让端点离开形状，看起来像「线没接到框」。要躲中间障碍，应 **挪开挡路的形状**，而不是把整条线平移到悬空。

## 不要做的事

| 做法 | 结果 |
|------|------|
| 回程仍从右侧 `GlueToPos(src, 1, y)` | 绕页 |
| `ConFixedCode=2` 指望它修好绕线 | 只是锁死错误路径 |
| `DrawPolyline` + `EndArrow` | 二维形状，箭头错位 |
| 三个加工/存储共线再连两端 | 中间被穿 |
| `Documents.Item.Quit` 在列举 masters 之后 | 进程挂起，杀 `VISIO.EXE` |

## 箭头

`EndArrow=13`（实心）。双向同一条线再设 `BeginArrow=13`。
