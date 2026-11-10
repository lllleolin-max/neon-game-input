# 接入指南

## 数据链路

```text
Neon Companion（局域网）
    → 官方 SDK：匹配的场景帧与注视
    → 官方 GazeMapper + 你绘制的四角标记
    → NeonInput：最新 Sample（画布坐标）
    → InputMonitor：有效性、新鲜度、恢复稳定时间、可计入停留的时长
    → Dwell：目标进入 / 停留触发 / 离开后重新武装
    → 你的游戏行为与光标绘制
```

核心库不依赖 Pygame。`demo.py`、`example_game.py`、`pygame_support.py` 是可选层。
`web.py` 与 `browser/` 提供本机网页示例；游戏状态不会保存在服务器上。

## 最小完整例子

运行 `python examples/minimal_pygame.py --mode mouse` 或 `--mode neon`。
它包括窗口事件循环、焦点检查、标记绘制、光标和一个停留按钮。安装独立项目后，
可以将这个文件复制进你自己的工程运行，不需要本仓库的其他源码目录。

核心接线：

```python
from neon_game_input import Surface, NeonInput, InputMonitor, Dwell, Rect

surface = Surface(1280, 720, marker_size=160, margin=24)
neon = NeonInput(surface).start()  # 默认发现；address="..." 可显式指定
monitor = InputMonitor(max_age=0.15, max_gap=0.10, recovery_seconds=0.20)
dwell = Dwell(seconds=0.6, release_seconds=0.18)
button = Rect(500, 280, 280, 160)

# 游戏循环，每帧：
sample = neon.poll(focused=True)  # 用实际窗口焦点替换 True
frame = monitor.step(sample)
event = dwell.update("start" if button.contains(frame.position) else None, frame)
if event == "start":
    print("Start requested")

# 退出时：
neon.close()
```

`NeonInput()` 本身不启动连接；调用 `start()` 或使用 `with NeonInput(...) as neon:`。
`close()` 默认不阻塞绘制线程，`close(timeout=1)` 可在退出阶段有限等待；返回值表示工作线程是否已经停止。
SDK 内部发现、校准或解码可能超出此时间，后台 daemon 线程返回后会在 `finally` 关闭设备。
关闭后的实例不能再次启动；创建新实例。`connected` 仅表示 SDK 会话建立，不代表已得到可用屏幕坐标。
`.error` 用于本机排障，文本可能带网络地址，公开前检查。

## 画布、标记和光标

默认画布 1280×720，四角 ID 依次为 0（左上）、1（右上）、2（右下）、3（左下）。
每个 PNG 是 tag36h11，160×160；中央黑色有效标记 128×128，白色静区每边 16 像素。
图案按官方 mapper 的角点顺序旋转了 180°，不要再翻转。

- `surface.marker_rects()`：绘制整个 PNG 的矩形。
- `surface.marker_vertices()`：交给 mapper 的黑色区域四角，不含白边。
- `surface.from_normalized(x,y)`：官方左下原点归一化坐标 → 左上原点像素。
- `surface.from_viewport(point, window_size)`：鼠标坐标反算，适用于居中、等比缩放和黑边。
- `surface.contains(point)`：判断是否在画布内。越界坐标保留为越界，避免把无命中硬夹到按钮上。

`marker_size` 必须为 10 的正整数倍。修改尺寸后，PNG、注册几何和目标画布必须同步。
保持黑白纯色、足够物理大小和完整静区，使用最近邻缩放；标记绘制在最上层，光标和 UI 不覆盖标记。
不要同时在场景相机视野里展示另一套相同 ID 的标记。

Pygame 可使用 `PygameOverlay(surface)`：先 `cursor(canvas, frame.position, now)`，最后 `markers(canvas)`。
传入 `None` 可立即清除光标与尾迹。光标头直接位于命中坐标，不额外平滑、不吸附目标。
构造 overlay 前需初始化 Pygame 显示窗口。

## 样本与时间

`Sample` 是不可变 dataclass：

| 字段 | 含义 |
| --- | --- |
| `source` | `neon` 或明确的 `mouse-simulation` |
| `sequence` | 本地发布序号，用于去重 |
| `position` | `(x,y)` 画布像素；无映射时 `None` |
| `valid` / `mapped` | 当前注视可用 / 已映射到画布 |
| `received_at` | 匹配样本取到时的本机 `time.monotonic()`，在 mapper 计算之前记录 |
| `device_timestamp` | 原设备 Unix 时间戳；仅用于记录或单调检查 |
| `reason` | 无效原因的稳定字符串，例如 `not_worn`、`markers_missing` |
| `markers` | 本次检测到的标记 ID |

不要用设备 Unix 时间减去本机单调时间。`age` 包含本机映射耗时，但不是完整设备到光标的端到端延迟。
工作线程仅保留最新样本。读取或重绘同一个样本不产生额外停留时长。

`InputFrame.usable` 允许显示新鲜光标；`ready` 还要求经过恢复稳定期，才允许交互。
`fresh` 表示新序号，`credit` 是可以累计的已观察时间。
断流、无效输入、过长采样间隔或渲染停顿后，不会追补停留时间。
显示布局变化时调用 `monitor.reset()`；退出/暂停期间继续向 `Dwell` 传递无效帧，以清除未完成停留。

`Dwell.update(target_id, frame)` 返回本次触发的目标 ID 或 `None`。目标是任意字符串，命中检测由游戏负责。
切换目标会清零停留。一次触发后，必须有有效输入离开全部交互目标才能重新触发；
丢失追踪不能当成“用户主动移开目光”。

## 网页接入

示例启动器：`neon-game-web --mode neon --port 8765 --companion-port 8080`。
服务器固定监听 `127.0.0.1`，HTTP 端口与 Companion 端口是不同参数。
不要直接将此开发服务器暴露到公网。

`GET /config` 提供画布与模式；`GET /health` 提供 `game_workers: 0`。
同来源 `WebSocket /samples` 输出最新样本：

```json
{"type":"sample","source":"neon","sequence":42,"position":[640,360],
 "valid":true,"mapped":true,"age":0.02,"reason":"","markers":[0,1,2,3]}
```

这是示意数据，不是硬件测量。浏览器用接收时钟、样本年龄与 ping 往返耗时估算本地新鲜度，
不把两个进程的时钟直接相减。`{ "type": "ping", "id": 1 }` 得到对应 `pong`。
桥接不发送视频、音频、校准原始数据或设备标识。页面失焦、标签隐藏或 socket 断开时清空输入。

`browser/input.mjs` 提供纯 JavaScript `InputMonitor` 和 `Dwell`，与 Python 版本共享行为测试向量。
若换成自己的 WebGL/Canvas 游戏，可复用这两个类及样本协议；沿用同来源、本机访问限制。
鼠标模式完全不创建 Neon 连接；真实模式断开后也不会自动降级成鼠标。

## 适用边界

当前默认严格要求四个标记同时检测到；`require_all_markers=False` 是专家选项，
不提供等效精度保证。单显示器、标记无遮挡、稳定布局是初始使用条件。
多显示器、混合 DPI、跨显示器拖动、长时间连接恢复和定量精度需各自实机验证。
