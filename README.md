# Calypso's Ogygia

Windows 桌面伴侣：Ogygia 壁纸负责环境，Python/PySide6 + Win32 负责 Calypso 和可交互物件。当前 production runtime 位于 `src/calypso`，使用透明的小型 Sprite/Object Window 和 dirty-region 更新；它不是 Godot 游戏窗口，也不使用 Electron/Chromium。

## 当前架构与边界

- `src/calypso`：生产代码。`behavior` 管理状态与优先级，`time` 读取本地时钟，`hermes` 读取任务快照，`navigation` 管路线与交互点，`desktop` 管窗口坐标和昼夜壁纸，`character`/`objects` 管显示与物件。
- `app/`：旧 PyQt6 实现，仅作 reference/迁移材料，不是生产入口。
- Godot：legacy/reference；旧项目可在 git 历史 `00316a9^` 找到，保留在历史中，不删除、不作为当前运行方式。
- 默认轮询本机 Hermes 状态；Hermes 未运行或短暂断线时，Calypso 仍继续普通生活。当前不使用数据库或 farming。

生产坐标以 2560×1600 canonical physical-pixel world 为基准。当前地图源图为 1312×816，导航数据为 16 px 网格；地图坐标、网格坐标与屏幕 physical pixels 之间统一由坐标变换层处理，Windows per-monitor DPI scaling 不应进入行为逻辑。资源和可复用数据仍在 `assets/`、`data/locations.json`、`data/navigation.json` 及相关配置中。

## 行为与时间

默认使用电脑本地时间：21:00 至次日 06:00 为睡眠时段。启动时若已是夜间，会立即去床边；06:00 离床。Hermes 有正在处理的回合时优先去电脑，电脑在她抵达操作点后亮起；回合在夜间结束后再回床。思考、执行工具和输出回复都算处理中的回合，单纯打开会话窗口不算。`DEBUG_TIME` 仍可在 `data/runtime_config.json` 中手动启用，用于加速调试。

电脑贴图使用 `computer` 点位，角色工作时使用桌前的 `computer_use` 点位，二者定义于 `data/locations.json`。白天闲逛时 Calypso 会走到 `fishing` 点位，依次抛竿、等待、收竿，单次持续 5–20 秒后离开。Hermes 任务和夜间睡眠会立即打断钓鱼。新增种花等活动时，在 `src/calypso/behavior/states.py` 添加状态及位置/动画配置，并在 `BehaviorManager` 增加进入条件；通用导航与计时不需要复制。

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
python -m calypso --status
```

双击根目录 `Calypso.cmd` 可切换运行状态。它通过 `logs/calypso.pid` 与
`logs/calypso.stop` 请求优雅退出；应用最多等待后台清理完成，不会盲杀未知进程。
一键脚本使用原生透明工具窗口模式；普通应用会覆盖桌宠，按 `Win+D` 返回桌面即可查看。
`--desktop` WorkerW 模式仅保留作实验用途，不作为默认启动方式。
默认读取 Hermes 端提供的 `%LOCALAPPDATA%/hermes/runtime/calypso_busy.json`。旧的 `active_sessions.json` 只代表打开的会话窗口，不能判断 Hermes 是否在处理请求，因此不再作为默认工作信号。`data/runtime_config.json` 仍可显式切换到兼容的 registry 或 HTTP provider。`--status` 可查看当前读取路径、忙碌回合数和本地时钟。F9/F10 继续提供本地调试任务开始/结束，不会覆盖 Hermes 的忙碌状态。

昼夜地图由 `src/calypso/desktop/wallpaper.py` 对 `assets/map/map.png` 做固定调色，并给篝火加局部暖光，生成到 `logs/wallpaper_night.bmp`；地形和导航坐标逐像素保持一致。角色在夜间使用同一套调色，避免在暗地图上突兀发亮。睡眠贴图由 `tools/build_sleep_head.py` 从原画提取头像，只叠加在地图自带的枕头和被褥上。21:00 换夜图、06:00 还原，退出时也还原启动前的日间壁纸路径。只有当前壁纸与项目日间地图内容相同时才接管，避免覆盖用户手动选择的其他壁纸。此功能在 `REAL_TIME` 模式下启用。

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

钓鱼与侧向走路精灵采用真正透明的 PNG，源图位于 `assets/source/`，运行时帧位于 `assets/calypso_v2/`。运行 `python tools/process_action_sheets.py` 可从生成的源图重建逐帧素材；`assets/calypso_v2/manifest.json` 中的 `fish_cast`、`fish_wait`、`fish_pull` 与行为阶段对应。钓鱼画面高度可通过运行配置中的 `fishing_height` 调整，默认 150 世界像素。

## Hermes 状态绑定

生产 Runtime 默认监听 `calypso_busy.json`，只统计 Hermes 正在处理的回合。Hermes 端尚需提供这个文件；请在 Hermes 的真实 `busy` 状态变化处维护所有忙碌 session ID。请求开始到结束期间都算 busy，包括思考、工具调用和回复；空闲窗口与常驻后台进程不进入列表。格式：

```json
{"version":1,"updated_at":1790431200.0,"busy_session_ids":["session-id"]}
```

`updated_at` 是每次写入时的 Unix 秒时间戳。Hermes 应由一个聚合器原子写文件（同目录临时文件后 `os.replace`），每 2 秒内刷新一次，即使正在等工具也刷新；结束、取消、失败或关闭回合时立即移除对应 ID，全部空闲时写空数组。Calypso 每秒轮询，连续两次读到空数组后离开电脑；文件缺失或超过 8 秒未更新也视为空闲，避免 Hermes 崩溃后永久工作。`--status` 可检查当前忙碌回合数。旧版 `active_sessions.json` 监听仍保留为显式配置兼容模式。

Hermes 桌面端已有 `apps/desktop/src/store/session-states.ts` 导出的 `$workingSessionIds`，由各 session 的 `state.busy` 汇总，能区分真正处理中的回合与闲置窗口。接入脚本应从 Hermes 的回合生命周期或这一聚合状态取值；若需要覆盖桌面端以外的 CLI/网关回合，请在 Hermes 后端聚合所有来源。文件写入须由具备文件系统权限的进程执行，桌面渲染进程可经 Hermes 自身 IPC 转交。
