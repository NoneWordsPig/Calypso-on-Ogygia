# Calypso's Ogygia

Windows 桌面伴侣：Ogygia 壁纸负责环境，Python/PySide6 + Win32 负责 Calypso 和可交互物件。当前 production runtime 位于 `src/calypso`，使用透明的小型 Sprite/Object Window 和 dirty-region 更新；它不是 Godot 游戏窗口，也不使用 Electron/Chromium。

## 当前架构与边界

- `src/calypso`：生产代码。包含 physical-pixel 坐标变换、DPI、SpriteWindow、导航、行为/时间系统、ComputerController、FakeAgentBridge 和可选的 WorkerW desktop host。
- `app/`：旧 PyQt6 实现，仅作 reference/迁移材料，不是生产入口。
- Godot：legacy/reference；旧项目可在 git 历史 `00316a9^` 找到，保留在历史中，不删除、不作为当前运行方式。
- 第一阶段只使用本地行为和 FakeAgentBridge；没有真实 Hermes、HTTP 轮询、数据库、farming 或环境动画。

生产坐标以 2560×1600 canonical physical-pixel world 为基准。当前地图源图为 1312×816，导航数据为 16 px 网格；地图坐标、网格坐标与屏幕 physical pixels 之间统一由坐标变换层处理，Windows per-monitor DPI scaling 不应进入行为逻辑。资源和可复用数据仍在 `assets/`、`data/locations.json`、`data/navigation.json` 及相关配置中。

## 开发阶段

P0 启动；P1 真透明 Calypso、nearest-neighbor 和正确 frame anchor；P2 physical-pixel/DPI；P3 Debug Overlay 沿现有路线行走并切换四方向动画；P4 读取 `locations.json`，支持 `go_to(bed)`, `go_to(computer)`, `go_to(fishing)`；P5 IDLE/WALKING 本地生活循环；P6 Debug 加速时间、21:00 回床睡觉、06:00 起床；P7 ComputerController + FakeAgentBridge。

快捷键：F9 触发 fake task（打断当前行为、跑向电脑、`computer_on`、进入 WORKING），F10 结束 fake task（`computer_off`、离开电脑、恢复生活循环）。

## 安装与运行

需要 Python 3.12+（Windows）。

```powershell
python -m pip install -e .
# 或：python -m pip install -r requirements.txt

python -m calypso --debug-overlay
python -m calypso --desktop
python -m calypso --fake-task
python -m calypso --smoke 300
```

单元测试：

```powershell
python -m unittest discover -s tests -v
```

`--desktop` 的 WorkerW 挂接依赖真实 Windows 用户桌面 shell。在无可枚举的交互 shell（CI、headless 或自动化会话）中，程序会安全 fallback 到普通透明窗口；请在用户登录的 Windows session 中验证桌面行为。最终集成不依赖 always-on-top，不抢焦点、不进入正常 Alt+Tab，并应保留桌面文件和图标的点击能力；只有点击 Calypso 时才响应。

## 数据与资源

```text
assets/                 地图、色罩、Calypso 精灵及电脑贴图
data/locations.json      bed/computer/fishing 等世界点位
data/navigation.json     16 px 网格路线/可行走数据
src/calypso/             production runtime
app/                     legacy PyQt6 reference
tools/                   资源与导航构建工具
tests/                   runtime、导航、DPI、窗口、行为和时间测试
docs/screenshots/        已有调试截图
```

`assets/map/map.png` 是当前地图背景，`map_cover.jpg` 是导航色罩。需要重建导航时使用 `tools/build_navigation.py`；不要把 Godot 配置中的旧坐标直接当作生产屏幕坐标。

## 后续集成

Hermes AgentBridge 只在本地 P0–P7 稳定后接入；届时应替换 bridge 接口而不改动行为、导航、时间和窗口边界。本 README 不声称真实 Hermes 或最终 desktop integration 已完成。
