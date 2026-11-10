# 故障排查

先区分三件事：**SDK 已连接、已收到眼动、已定位游戏画布**。它们不是同一状态。

| 状态 | 检查 |
| --- | --- |
| `dependency_missing` | 在实际运行的虚拟环境安装 `.[neon]`，不要混用系统 Python |
| `discovering` / `device_not_found` | Companion 开启实时数据；两设备同网段，网络不隔离客户端；发现不可用时传 `--address` |
| `device_error` | 核对 Companion 当前地址、端口与应用防火墙权限；查看 `NeonInput.error` 的本机信息 |
| `unsupported_device` | 本版只接受 Neon 硬件版本 `2` / `2.0`，不接入 Pupil Core 或 Invisible |
| `not_worn` | 戴好眼镜并确认 Companion 中佩戴状态正常 |
| `markers_missing` | 看见全部四角，调大窗口或全屏；避免反光、遮挡、重复 ID 标记或过小的显示尺寸 |
| `surface_not_located` | 确保绘制资源和注册的几何完全一致；不要把整个 PNG 的白边注册为黑色标记 |
| `stale_sample` / `processing_too_slow` | 检查本机性能与网络；不能通过累计旧样本绕过丢失处理 |
| `window_unfocused` | 回到游戏窗口；恢复期结束后才会继续累计时间 |

## 只检查连接

```powershell
neon-game-check --seconds 15
# 或使用真实 Companion 地址替换文档地址：
neon-game-check --address 192.0.2.1 --seconds 15
```

输出 SDK 是否建立会话，以及各类状态计数；退出码 0 表示连接曾建立，1 表示未建立。
该工具不显示标记，因此在没有其他标记画布时报告 `markers_missing` 是正常的。
`sdk_connected: true` 不表示屏幕映射、硬件精度或游戏交互已验收。
避免同时运行多个设备读取器；检查游戏眼控请直接使用游戏窗口。
工具不改网络、防火墙、相机或项目配置，也不保存图像、注视坐标和设备 ID。

## 停留触发看起来没反应

每次触发后先看向目标外，再看回目标。停留计时使用新样本间隔，不使用绘制帧数。
连续重绘旧样本、断流、恢复稳定期或失焦都不会触发。光标能显示与能计入停留是分开的条件。

## 网页页面很小或看不见标记

使用浏览器的 Fullscreen 按钮或放大窗口，使四角标记有足够物理尺寸。
窄手机画面只用于模拟界面预览，不代表已通过真实 Neon 定位。
页面加载后模拟游戏不依赖服务器；真实模式需要服务器持续转发样本。
遇到连接断开，页面会自动尝试重连，但不会伪造新的注视。

## 依赖警告

当前验证的 NumPy 2.5 与上游 screen-gaze / surface-tracker 会产生修改 `shape` 的弃用提示。
映射测试通过，项目未屏蔽提示或修改第三方源码。升级依赖后应重跑官方映射测试。
Windows/Python 3.12 可用 `requirements-windows-py312.lock.txt` 复现本次版本组合。
