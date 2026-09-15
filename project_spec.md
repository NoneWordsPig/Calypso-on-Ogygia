# Calypso on Ogygia
## Καλυψώ — Windows Desktop Companion & Hermes Agent Avatar

---

# 0. Project Vision

Calypso on Ogygia 是一个 Windows 桌面生命体项目。

主角是希腊神话中的 Καλυψώ（Calypso / 卡吕普索）。

她生活在一座名为 Ogygia 的像素风小岛上。

Ogygia 本身不是游戏窗口，而是 Windows 的真实桌面壁纸。

Calypso 以透明桌面 Sprite 的形式生活在壁纸之上。

用户正常使用 Windows 时：

- 桌面图标仍然正常工作
- 鼠标正常点击文件
- 桌面仍然是真正的 Windows 桌面
- 没有一个显眼的“游戏窗口”
- Calypso 看起来像本来就生活在桌面中

核心体验不是：

“打开一个桌宠程序。”

而是：

“我的桌面就是 Ogygia，而 Calypso 住在里面。”

---

# 1. Core Philosophy

这个项目不是完整的《星露谷物语》。

也不是把聊天机器人套上一层动画皮肤。

它的目标是：

> 给 Hermes / AI Agent 一个具有持续生活感的实体化存在。

Calypso 应该：

- 即使 Hermes 没运行，也照样生活
- 自己走路
- 自己发呆
- 自己去海边
- 自己钓鱼
- 自己睡觉
- 自己起床

Hermes 只是她拥有的能力之一。

Hermes 不控制她的普通生活。

---

# 2. Target Platform

Primary platform:

Windows 11

Primary display target:

2560 × 1600
16:10

当前 Ogygia 壁纸按照该分辨率设计。

但是代码结构不能把所有逻辑完全写死在 2560×1600 上。

应设计一个统一的 ScreenTransform / CoordinateMapper。

未来可以适配：

- DPI scaling
- 不同分辨率
- 不同显示缩放
- 可能的外接显示器

第一阶段只需要保证主显示器正确。

---

# 3. Technology Choice

最终应用不要使用 Godot。

不要使用 Electron。

不要运行 Chromium。

不要使用 WebView 作为桌宠主体。

推荐：

Python 3.12+
PySide6
Win32 API via ctypes / pywin32 when necessary

可选辅助库：

Pillow
numpy（仅确有必要时）
标准 Python 数据结构

尽可能减少第三方依赖。

---

# 4. Architecture

整体结构：

Windows Wallpaper
       │
       │ static
       ▼
Ogygia Island PNG

       +

Desktop Companion Runtime
       │
       ├── Calypso Sprite
       ├── Computer Overlay
       ├── Animation System
       ├── Navigation
       ├── Behavior State Machine
       ├── Time System
       └── Interaction

       +

Hermes
       │
       ▼
AgentBridge
       │
       ▼
Task Events

---

# 5. Wallpaper

Ogygia 地图直接作为 Windows 系统壁纸。

应用本身不要重复绘制完整的 2560×1600 地图。

静态地图由 Windows 负责。

程序只渲染：

- Calypso
- Computer state
- 少量未来动态特效
- 临时对话 UI

这样能够：

- 减少 GPU / CPU 开销
- 减少内存
- 保证桌面图标是真实 Windows 图标
- 保持真正的桌面体验

---

# 6. Desktop Icon Reserved Area

地图设计已经考虑 Windows 桌面文件夹。

屏幕左侧约两列桌面图标宽度：

必须主要是海洋。

该区域：

- 不放重要交互对象
- 不放 Calypso 的主要生活设施
- 不放密集地形
- 尽量保持视觉简单
- 桌面文件夹名称应该清晰可读

Calypso 可以偶尔经过附近，但不应该长期停留在那里。

---

# 7. Desktop Window Strategy

这是整个项目的重要技术问题。

绝对不要简单创建一个：

always-on-top fullscreen transparent window

因为那会导致 Calypso 永远浮在：

- VS Code
- Chrome
- 游戏
- 视频

之上。

这是错误行为。

目标：

Calypso 属于 Windows Desktop Layer。

当其他普通应用覆盖桌面时：

Calypso 应该自然被遮挡。

她应该感觉像“桌面的一部分”。

Desktop Integration 应作为单独模块实现：

desktop/
    desktop_host.py
    window_styles.py
    dpi.py

需要研究 Windows Shell：

Progman
WorkerW
SHELLDLL_DefView

寻找稳定、低侵入性的实现。

优先目标：

让 Calypso 的 HWND 位于桌面层级，而不是普通应用层。

不要盲目使用 HWND_TOPMOST。

---

# 8. Desktop Integration Development Strategy

不要一开始就陷入 WorkerW / Shell 调试。

开发分两层。

DEBUG MODE:

普通透明窗口。

优点：

- 可以调动画
- 可以调导航
- 可以调状态机
- 可以调坐标

DESKTOP MODE:

核心逻辑稳定后，再接入 Windows Desktop Layer。

必须做到：

同一套 Calypso / Behavior / Navigation 代码既可以运行在 Debug Mode，也可以运行在 Desktop Mode。

不要复制两套逻辑。

---

# 9. Transparent Rendering

Calypso Sprite 背景必须真正透明。

Qt 窗口：

- Frameless
- Transparent background
- 不显示标题栏
- 不显示任务栏图标
- 尽可能不出现在 Alt+Tab
- 不抢焦点
- 不主动激活

必要时使用 Win32：

WS_EX_TOOLWINDOW
WS_EX_NOACTIVATE
WS_EX_LAYERED

是否使用 WS_EX_TRANSPARENT 应根据具体交互策略决定。

不要因为实现鼠标穿透而导致 Calypso 永远无法点击。

---

# 10. Rendering Strategy

不要默认创建一个每帧重绘的 2560×1600 全屏透明窗口。

优先考虑：

小型 Sprite Window / Dirty Region Rendering。

Calypso 实际只有大约：

80–120 px height

因此：

一个大约 128×160 / 160×200 的透明窗口就足够容纳人物。

角色移动时：

移动窗口位置。

角色动画时：

只刷新该小窗口。

Computer overlay 也可以是一个独立小窗口。

这样能够大幅降低：

- compositor load
- repaint area
- GPU usage

---

# 11. DPI Awareness

这是硬要求。

Windows 显示缩放可能不是 100%。

必须在 QApplication 创建前处理 DPI Awareness。

优先使用：

Per Monitor DPI Awareness V2

并建立统一：

ScreenTransform

项目中的 world coordinates 不应该因为：

125%
150%
175%

Windows display scaling 而错位。

地图坐标最终以：

physical wallpaper pixel coordinates

为基准。

---

# 12. World Coordinate System

当前 Ogygia 原始地图：

2560 × 1600

定义：

左上角：

(0, 0)

右下角：

(2560, 1600)

所有游戏世界位置统一以：

(x, y)

表示。

这里的坐标表示：

壁纸中的实际像素位置。

不要让：

Qt logical coordinates
Windows physical coordinates
地图格子坐标

在程序中混在一起。

必须有单独转换层。

---

# 13. Existing Development Map

已有一张 Developer Reference Map。

其中曾标记：

- Walkable Paths
- Random Walk Areas
- Forbidden Areas
- Computer Area
- Bed Area
- Fishing Area
- Grid Coordinates

曾经参考的位置包括：

Computer ≈ (20, 15)
Bed ≈ (35, 28)
Fishing ≈ (22, 40)

注意：

这些是开发图的粗网格坐标。

不是最终 2560×1600 世界坐标。

Codex 必须根据当前实际地图 / locations.json 重新确认。

---

# 14. Navigation Philosophy

运行时完全不使用 Vision AI。

Calypso 不需要“看地图”。

地图是固定的。

因此所有导航信息应该在开发阶段预先定义。

推荐模型：

Waypoint Graph
+
Free Roam Polygons

而不是完整 TileMap。

---

# 15. Roads

地图中的道路：

主要用于长距离移动。

定义为：

一组节点 + 连接关系。

例如：

bed
 │
road_01
 │
crossroad
 ├── flower_field
 ├── computer
 └── coast
       │
   fishing_rock

节点可以使用：

(x, y)

edges 表示合法连接。

路径规划：

A*

图规模很小。

开销可忽略。

---

# 16. Straight Road Movement

之前已经提出：

道路上移动最好具有：

“沿直线走”的感觉。

因此：

路径本身可以存储为：

polyline

例如：

[
  [1230, 800],
  [1400, 800],
  [1400, 930]
]

Calypso 按线段移动。

不要用大量随机微小点导致走路像醉酒。

---

# 17. Free Roam Areas

除道路外，还存在：

random walk regions。

例如：

- 花田
- 草地
- 已允许的田地
- 海岸空地

表示为 Polygon。

进入区域后：

选择 polygon 内随机目标。

然后：

walk_to(random_point)

达到目标后：

idle 一段时间。

再决定下一行为。

---

# 18. Forbidden Areas

不能进入：

- Ocean
- Cliff
- Trees
- Waterfalls
- Rocks
- Map outside
- 明确的装饰障碍

因为使用预设 Graph / Polygon：

通常不需要实时 collision detection。

但 NavigationManager 应保证：

生成的路径只经过合法区域。

---

# 19. locations.json

所有关键位置集中存储。

不要把坐标散落到 Python 文件中。

推荐：

data/locations.json

结构可以重构，但至少包含：

{
  "points": {
    "bed": {},
    "computer": {},
    "campfire": {},
    "fishing_rock": {}
  },

  "paths": {},

  "free_roam_regions": {},

  "forbidden_regions": {}
}

每个 interaction point 最好区分：

visual_position

和：

character_interaction_position

例如电脑屏幕位置和 Calypso 坐下的位置不是同一点。

---

# 20. Calypso Visual Design

角色视觉方向已经基本确定。

Calypso：

- 年轻女性
- 长深蓝 / 青蓝色头发
- 蓝绿色长裙
- 海洋感
- 希腊神话感
- 温柔
- 神秘
- 有一定神性
- 但生活化

不要：

- 女仆风
- 现代都市服装
- 夸张战甲
- 过度二次元化

目标感觉：

“住在孤独海岛上的年轻女神。”

---

# 21. Sprite Assets

所有 Sprite：

PNG
True Alpha Channel

不要把灰白棋盘格当透明背景。

如果素材仍然有棋盘背景：

应先制作真正透明版本。

不要在运行时每帧抠图。

---

# 22. Pixel Art Rendering

必须保持 pixel art 清晰。

禁止：

bilinear interpolation
smooth scaling

所有缩放：

nearest neighbor

尽可能使用整数倍率。

如果原始 sprite 分辨率较高：

可以预处理成最终使用尺寸。

不要每帧实时 resize。

---

# 23. Character Anchor

Calypso 所有帧必须使用统一锚点。

推荐：

feet center

例如：

anchor = bottom center

这样：

角色换动画时：

头发长度
裙摆变化
动作变化

不会导致整个角色上下漂移。

移动坐标表示：

脚底所在世界位置。

---

# 24. Base Animations

MVP 至少支持：

idle_down
idle_up
idle_left
idle_right

walk_down
walk_up
walk_left
walk_right

sleep

work

未来：

fishing
plant
hoe
sit
stand_up
wake

---

# 25. Animation Frame Rate

不需要 60 FPS sprite animation。

推荐：

walk:

6–10 FPS

idle:

2–4 FPS 或静态

sleep:

1–2 FPS

work:

4–8 FPS

窗口位置更新可以：

30 FPS

甚至使用 delta-time movement。

---

# 26. Sleep Animation

睡眠 deliberately simple。

床保持静态。

Calypso 到达床后：

隐藏正常人物。

显示：

枕头上的小头部。

两帧循环：

inhale
exhale

头发可以有非常细微变化。

不需要：

- 掀被子
- 翻身
- 完整爬床动画

第一版保持简单。

---

# 27. Computer

桌子已经画进地图。

不要重复创建桌子。

动态对象只需要：

computer_off
computer_on

或者甚至：

screen_off
screen_on

叠加在壁纸中的电脑位置。

ComputerController：

turn_on()
turn_off()

以后可以支持：

set_working()
notification()

---

# 28. Computer Visual State

没有任务：

OFF

屏幕暗。

收到任务：

ON

屏幕亮。

推荐：

蓝绿色轻微发光。

不要做非常刺眼的霓虹效果。

Computer overlay 同样尽可能是小型透明 Sprite Window。

---

# 29. Behavior State Machine

至少包含：

IDLE
WALKING
FISHING
WORKING
SLEEPING

可以额外内部状态：

GOING_TO_BED
GOING_TO_COMPUTER
GOING_TO_FISH
RETURNING

但是不要把 FSM 设计得过度复杂。

---

# 30. Behavior Architecture

推荐：

BehaviorManager

负责决定：

“她现在要做什么。”

NavigationManager

负责决定：

“怎么走过去。”

Animator

负责决定：

“现在显示哪个动画。”

CharacterController

负责：

“实际位置和移动。”

不要把全部逻辑塞进一个 1500 行文件。

---

# 31. Ordinary Life

没有任务时：

Calypso 自己生活。

一个典型循环：

IDLE
↓
选择活动
↓
选择目的地
↓
WALKING
↓
到达
↓
IDLE / FISHING / other
↓
等待
↓
再次选择

行为间隔必须自然。

不要：

每两秒随机换方向。

---

# 32. Idle

需要大量发呆。

因为真实生活感的重要组成部分就是：

“不是什么时候都在干活。”

可以：

- 看海
- 站在花田
- 站在树旁
- 坐着
- 发呆

时间：

随机。

例如：

5–60 seconds

具体参数应配置化。

---

# 33. Random Behavior

不要使用 LLM。

使用：

weighted local scheduler。

例如：

IDLE
WALK
FLOWER_AREA
COAST
FISHING
CAMPFIRE

概率配置化。

不要写死在多个 if 中。

---

# 34. Fishing

只有指定 Fishing Spot 能钓鱼。

主要地点：

海边礁石。

流程未来：

walk_to(fishing_spot)
↓
cast
↓
wait
↓
pull
↓
leave

单次 fishing duration：

5–20 seconds

这里的随机是本地 RNG。

不调用 AI。

---

# 35. Fishing Interruption

如果 Hermes Task 在钓鱼期间到达：

Fishing 属于可立即打断行为。

第一版可以：

直接结束 fishing 状态。

未来有动画后：

播放 quick pull / cancel。

然后：

GOING_TO_COMPUTER。

---

# 36. Time System

需要独立：

TimeManager

两种时间模式：

DEBUG_TIME
REAL_TIME

开发：

加速时间。

例如：

30 sec real = 1 game hour

正式桌宠：

使用系统真实时间。

---

# 37. Sleep Schedule

正式：

21:00

Calypso 准备睡觉。

流程：

21:00
↓
GOING_TO_BED
↓
bed interaction point
↓
SLEEPING

06:00
↓
WAKE
↓
恢复普通生活

---

# 38. Sleep / Task Conflict

如果 21:00 时正在执行 Hermes Task：

不要强制杀死任务。

规则：

WORKING task continues
↓
task finished
↓
if current time >= 21:00
↓
go to bed

任务优先于立即睡觉。

但下一步必须睡觉。

---

# 39. Task Priority

行为优先级：

ACTIVE_HERMES_TASK
>
SLEEP_REQUIREMENT
>
SPECIAL_ACTION
>
NORMAL_ACTIVITY
>
IDLE

其中 Hermes Task 是最高即时优先级。

---

# 40. Hermes Task Behavior

收到任务：

Calypso 应该：

停止普通生活
↓
进入 GOING_TO_COMPUTER
↓
提高移动速度
↓
跑向电脑
↓
到达 interaction point
↓
computer_on
↓
WORKING
↓
Hermes 执行
↓
task_finished
↓
computer_off
↓
离开电脑
↓
恢复生活

---

# 41. Running to Computer

第一版不需要独立跑步 sprite。

可以：

walk animation
+
更高 animation FPS
+
更高 movement speed

制造：

“赶去工作”的感觉。

以后有专门 run sprites 再替换。

---

# 42. Short Animation Interruption

收到任务时：

IDLE:
立即中断

WALKING:
立即重新规划路线

FISHING:
允许中断

非常短的不可中断动画：
等当前 animation cycle / action ending 完成后立即走

不要让角色因为任务在原地卡几十秒。

---

# 43. Hermes Integration

Hermes 必须完全与桌宠运行时解耦。

Calypso Desktop 不依赖 Hermes 才能启动。

Hermes：

可以关闭
可以重启
可以崩溃

Calypso：

依然正常生活。

---

# 44. Process Architecture

推荐：

Calypso Desktop Process

和：

Hermes Process

完全分离。

通信：

localhost socket
WebSocket
HTTP
named pipe

根据 Hermes 当前实际接口选择。

不要为了理论纯洁度自己发明复杂协议。

---

# 45. AgentBridge

建立：

hermes/agent_bridge.py

对 BehaviorManager 暴露统一事件：

task_started(task_id, metadata)
task_progress(...)
task_finished(task_id, result)
task_failed(task_id, error)

桌宠核心只关心：

task started
task ended

不需要知道 Hermes 内部 Agent 结构。

---

# 46. First Version Hermes

Hermes 不是当前 MVP。

先制作 FakeAgentBridge。

例如：

F9:

fake_task_start()

F10:

fake_task_finish()

可以完整测试：

Calypso
↓
跑电脑
↓
工作
↓
离开

之后再换真实 Hermes。

---

# 47. User Interaction

未来：

点击 Calypso：

弹出一个小型对话框。

不是打开巨大主窗口。

风格：

轻量
贴近人物
像游戏 NPC 对话

例如：

┌─────────────────────┐
│ Καλυψώ               │
│                     │
│ 今天有什么神谕？     │
│                     │
│ [_________________] │
└─────────────────────┘

输入后发送 Hermes。

---

# 48. Click Behavior

平时：

桌面不能被大面积透明窗口挡住。

用户需要正常：

双击文件
拖图标
右键桌面
框选
操作桌面

因此交互命中区域只能是：

Calypso sprite bounding / alpha region

或极小 interaction region。

不要用一个 2560×1600 QWidget 吞掉鼠标。

---

# 49. No Focus Stealing

这是硬要求。

Calypso：

不应该因为：

走路
动画
电脑亮起

抢走：

VS Code
Chrome
游戏

的键盘焦点。

只有用户主动点击对话框时：

才允许获得输入焦点。

---

# 50. Hermes Future Inputs

长期目标包括：

Desktop click
↓
Hermes

以及：

微信
↓
Hermes
↓
AgentBridge
↓
Calypso Task

即使任务从手机发来：

桌面上的 Calypso 也应该：

收到任务
↓
跑电脑
↓
开始工作

---

# 51. Farming System — Future

最初完整构想还包括：

未开垦土地
↓ hoe
开垦土地

开垦土地
↓ 3 days no operation
未开垦土地

开垦土地
↓ planting
小花
↓ 1 day
花苞
↓ 1 day
花朵
↓ 1 day
开垦土地

只有未开垦土地可以 hoe。

这是 Phase 2+。

MVP 不实现。

---

# 52. Future Character Actions

长期动作清单：

standing × 4 direction

walking × 4

fishing:
cast
wait
pull

farming:
hoe
crouch plant

rest:
sit
stand
sleep
wake

work:
sit at computer
typing
leave

不要一开始实现全部。

---

# 53. Environment Animation

地图里已经画有：

海浪
树
花
草

第一版：

完全静态。

不要为了动画重新拆整个地图。

未来需要环境生命感时优先：

small overlay
particles
shader-like effects

例如：

- 少量浪花
- 飘落花瓣
- 小叶子
- 海面闪光
- 篝火火星

这些应该是轻量 embellishment。

---

# 54. Performance Goal

用户同时会运行：

Hermes
Codex
VS Code
Chrome
Python
其他开发工具

机器 RAM 约 16 GB。

因此 Calypso Desktop 必须非常克制。

目标：

Idle CPU ≈ ~0%
Walking CPU very low
No continuous AI inference
No browser runtime
No full-screen 60 FPS redraw

Memory：

尽量低。

不要引入：

Electron
Chromium
local LLM
vision runtime
Docker
database server

---

# 55. Event Driven Design

不要用：

while True:
    repaint_entire_screen()

优先：

Qt Timer
events
state transitions
scheduled callbacks

静止状态：

不需要高频更新。

行走时：

30 FPS movement 足够。

Sleep：

几乎不需要位置 update。

---

# 56. Logging

需要简单日志。

例如：

logs/calypso.log

记录：

app start
state transitions
navigation failures
task events
Hermes connection
exceptions

不要打印每一帧。

---

# 57. Configuration

建立：

config.json / config.toml

至少可以配置：

debug_mode
time_mode
time_scale
walk_speed
run_speed
animation_fps
sleep_time
wake_time
logging_level
Hermes endpoint

不要把这些散落为 magic numbers。

---

# 58. Persistence

第一版不需要数据库。

如果需要保存少量状态：

JSON 足够。

例如：

last_position
last_state
preferences

甚至第一版完全不存也可以。

不要引入 SQLite，除非以后真的需要历史数据。

---

# 59. Proposed Project Structure

Calypso's Ogygia/
│
├── README.md
├── PROJECT_SPEC.md
├── requirements.txt
├── pyproject.toml
│
├── src/
│   └── calypso/
│       │
│       ├── app.py
│       ├── config.py
│       │
│       ├── character/
│       │   ├── controller.py
│       │   ├── animator.py
│       │   └── sprite_window.py
│       │
│       ├── behavior/
│       │   ├── manager.py
│       │   ├── states.py
│       │   └── scheduler.py
│       │
│       ├── navigation/
│       │   ├── manager.py
│       │   ├── graph.py
│       │   └── geometry.py
│       │
│       ├── time/
│       │   └── time_manager.py
│       │
│       ├── desktop/
│       │   ├── desktop_host.py
│       │   ├── window_styles.py
│       │   ├── dpi.py
│       │   └── coordinate_mapper.py
│       │
│       ├── objects/
│       │   └── computer.py
│       │
│       ├── interaction/
│       │   └── dialogue.py
│       │
│       └── hermes/
│           ├── agent_bridge.py
│           └── fake_bridge.py
│
├── assets/
│   │
│   ├── wallpaper/
│   │   ├── ogygia.png
│   │   └── ogygia_dev.png
│   │
│   ├── calypso/
│   │   ├── idle/
│   │   ├── walk/
│   │   ├── sleep/
│   │   ├── work/
│   │   └── fishing/
│   │
│   ├── objects/
│   │   ├── computer_off.png
│   │   └── computer_on.png
│   │
│   └── effects/
│
├── data/
│   └── locations.json
│
├── config/
│   └── config.toml
│
├── logs/
│
└── tests/

具体目录可根据现有项目调整。

不要为了满足文档而无意义重命名所有现有文件。

---

# 60. Existing Project

项目可能已经存在旧实现。

不要假设是空项目。

首先扫描：

- 当前目录
- 所有代码
- 所有 JSON
- 所有图片
- Godot 旧文件
- 路线数据
- 已有 movement 实现

如果已经存在可复用：

- route data
- locations
- sprite animation
- state logic

应该迁移或复用。

不要重新手抄。

---

# 61. Legacy Godot Code

如果发现已有 Godot 项目：

不要立刻删除。

旧 Godot 版本可以作为：

reference implementation

尤其已有：

- route
- walking
- location
- behavior

的数据和逻辑可以参考。

但新的桌面运行时使用：

PySide6 / native Windows overlay。

不要同时维护两个 production runtime。

---

# 62. Development Phases

## Phase 0 — Audit

先理解项目。

检查：

当前文件
图片
alpha
sprite sheets
坐标
JSON
路线
旧代码

运行现有版本。

记录：

已经能做什么
哪里报错
哪些资产缺失

然后直接继续。

---

## Phase 1 — Minimal Sprite

先只做：

Debug transparent window

显示 Calypso。

确认：

alpha
nearest scaling
frame alignment
animation

---

## Phase 2 — Coordinates

实现：

ScreenTransform
DPI Awareness
2560×1600 world coordinate mapping

让 Calypso 可以准确站在：

bed
computer
fishing rock

位置。

---

## Phase 3 — Movement

实现：

position
velocity
direction
walk animation

让她沿手工 route 移动。

---

## Phase 4 — Navigation

加载 locations.json。

实现：

waypoint graph
A*

并支持：

go_to("bed")
go_to("computer")
go_to("fishing")

---

## Phase 5 — Random Life

实现：

IDLE
WALKING

weighted behavior scheduler。

让她能够自然生活。

---

## Phase 6 — Sleep

实现：

TimeManager。

测试加速时间。

21:00:
go bed

06:00:
wake up

sleep breathing animation。

---

## Phase 7 — Computer / Fake Task

实现 ComputerController。

F9:
fake task start

Calypso:
run to computer
computer on
WORKING

F10:
task finish
computer off
resume life

---

## Phase 8 — Fishing

实现指定礁石钓鱼。

5–20s。

支持 task interrupt。

---

## Phase 9 — Desktop Integration

核心行为稳定后：

把 debug window 接到 Windows desktop layer。

实现：

不 topmost
不抢 focus
不覆盖普通 apps
正常桌面操作

---

## Phase 10 — Click Interaction

角色点击：

small dialogue

其他区域完全不干扰桌面。

---

## Phase 11 — Hermes

FakeAgentBridge 换成真实 AgentBridge。

不要改 BehaviorManager API。

---

# 63. MVP Completion Criteria

MVP 完成后：

Windows 桌面壁纸是 Ogygia。

Calypso：

- 自然出现在桌面
- 四方向走路
- 不模糊
- 沿合法路线移动
- 随机发呆
- 随机活动
- 21:00 睡觉
- 06:00 起床
- 可以去指定礁石钓鱼
- Fake Task 到达后立即跑向电脑
- 工作时电脑亮
- Fake Task 完成后离开
- 不依赖 Hermes
- 不妨碍正常桌面操作
- 不浮在普通应用上面
- 不抢焦点
- 资源消耗非常低

达到这些条件后：

才开始真正 Hermes integration。

---

# 64. Code Quality

优先：

simple
readable
debuggable
modular

不要过度工程。

不要：

ECS
microservices
Docker
message broker
database server
复杂 dependency injection framework

这是一个桌面生命体项目。

不是企业 SaaS。

---

# 65. Codex Working Style

不要只给用户代码建议。

你是项目主开发工程师。

工作循环：

inspect
→ understand
→ implement
→ run
→ observe
→ fix
→ test
→ continue

只要可以自动完成：

就自己完成。

不要每修改一个 Python 文件就停下来要求用户批准下一步。

除非：

- 会删除大量文件
- 会破坏用户数据
- 缺少关键视觉资产
- 必须由用户做产品决策
- 涉及账户授权

否则继续开发。

---

# 66. Final Product Feeling

最终打开电脑：

用户不应该产生：

“我的桌宠软件开着。”

而应该觉得：

“这是我的桌面。”

左边：

正常文件夹。

中央和右侧：

Ogygia。

而某个时刻：

Calypso 正在花田里走。

过一会：

她坐在海边。

晚上：

她睡着。

手机给 Hermes 发任务后：

用户回到桌面。

看到：

她已经坐到了电脑前。

这就是项目最终应该实现的体验。