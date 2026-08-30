# Calypso's Ogygia

虚拟卡里普索桌面宠物：在“奥杰吉厄岛”地图上行走，并根据 Hermes 任务状态
（空闲 / 工作 / 成功 / 等待 / 审查 / 失败）表现不同行为。

本项目不使用 Godot。它采用 `参考/hermes-webui-desktop-companion` 的桌宠形态
（无边框置顶窗口 + 精灵图动画 + 每秒轮询状态源），并沿用 `残稿` 的地图、
作息与寻路机制。

## 快速开始

```powershell
# 依赖：Python 3.10+、PyQt6、Pillow（重建导航还需 numpy + scipy）
pip install PyQt6 Pillow numpy scipy

python -m app                 # 运行桌宠
python -m unittest discover -s tests   # 运行测试
python tools/build_navigation.py       # 重建数据/导航网格（可选）
```

启动后桌宠会出现在屏幕右下角（可拖动），自动开始：随机散步 → Hermes 状态驱动
的工作/庆祝/等待/审查，21:00 回床睡觉，06:00 起床。

## 行为状态机

| 状态 | 含义 | 优先级 | 精灵图动画（keeper） |
| --- | --- | --- | --- |
| WORKING | Hermes 正在工作：走到电脑边工作 | 6 | running |
| CELEBRATING | 任务成功：跳跃+挥手庆祝 | 5 | jumping → waving |
| WAITING | 需要操作/批准：原地等待 | 5 | waiting |
| REVIEW | 待审查：展示审查姿态 | 4 | review |
| FAILED | 任务失败：短暂沮丧 | 4 | failed |
| SLEEPING | 21:00-06:00 回床睡觉 | 3 | idle(慢速)+Zzz |
| WALKING | 沿道路行走（随机散步 / 前往目标） | 2 | running-left/right |
| IDLE | 空闲站立 | 1 | idle |

优先级满足约定：**工作 > 庆祝 > 睡眠 > 行走**（等待/审查/失败是参考项目自带的
补充状态，优先级可改 `data/config.json` 的 `behavior.priorities`）。

Hermes 状态映射（模拟或真实接口）：
`working→工作`、`success→庆祝`、`action_required→等待`、`ready→审查`、
`failed→失败`、`idle→空闲/散步`。

## Hermes 状态来源

- 默认 `mock`：内置模拟器循环 `空闲→工作→成功→空闲→等待→工作→成功→…`，
  无需真实 Hermes 即可演示完整状态机（时长在 `mock_hermes.loop` 中配置）。
- `http`：轮询参考项目 Hermes 桌面伴生端的 loopback 接口
  `GET http://127.0.0.1:17787/api/pet/attention`（`hermes.http_url` 可改）：
  `python -m app --provider http`。

## 地图与路径

- 地图：`assets/map/map.png`（1312×816，来自 `残稿/pictures/map`）。
- 行走：从地图的道路像素提取可走网格（16px 格 + A* 八方向寻路，含视线平滑），
  即“废稿”中绑定的地图道路。关键点位（电脑/床/钓鱼/篝火/出生点）来自
  `data/locations.json`，已全部验证互相可达。
- 导航数据 `data/navigation.json` 由 `tools/build_navigation.py` 生成；
  改地图后需重建。

## 素材

- 角色：`assets/sprites/keeper.webp`（Hermes Pet 默认皮 May，来自参考项目；
  8×9 宫格 192×208）。可切换 `courier.webp` / `shiba.webp`：
  修改 `data/config.json` 的 `resources.spritesheet`。
- 电脑：`assets/object/computer.png`（来自残稿，关/开两帧）。
- 封面图 `assets/map/map_cover.jpg` 保留自残稿，作为地图绑定参考。

## 调试快捷键

| 按键 | 作用 |
| --- | --- |
| F5 | 显示/隐藏 HUD |
| F8 | 快进 3 小时（测试睡觉/起床） |
| F9 | 强制工作（走到电脑） |
| F10 | 强制睡觉 |
| F11 | 强制起床 |
| F12 | 重置空闲 |
| Esc | 退出 |

窗口右键菜单提供同样的操作。

## 目录结构

```text
data/          配置、点位、导航网格
assets/        地图、角色、电脑贴图
app/           配置/精灵图/导航/行为/时间/Hermes状态/桌宠窗口
tools/         导航网格重建工具
tests/         单元测试（导航连通性、行为优先级、作息、状态映射）
docs/          截图与说明
```

## 运行验证

`python -m app --smoke 300` 可无交互跑 300 帧后自动退出，用于冒烟验证。
`docs/screenshots/` 有四个状态的实机截图。
