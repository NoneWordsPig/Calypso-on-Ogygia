# Calypso's Ogygia

Godot 4.x 2D 桌面桌宠（第一阶段）。

## 运行

1. 用 Godot 4.3+ 打开 `project.godot`（编辑器首次打开会自动导入素材）。
2. 直接运行主场景 `scenes/main.tscn`。
3. F9 = 打开电脑，F10 = 关闭电脑。

## 说明

- 地图使用 `pictures/map/map.png`（1312×816，实际素材分辨率，未缩放）。
- 世界坐标 = 地图像素坐标。
- 窗口默认全屏，地图通过 `canvas_items` 拉伸模式等比缩放铺满屏幕（不变形）。
- 角色自动缩放到与道路等宽（道路宽度在 `data/config.json` 的 `display.road_width` 中调整）。
- 角色动画帧从 `pictures/Calypso/*.png` 自动检测（无需硬编码帧数/尺寸），nearest-neighbor 渲染。
- 地图关键位置与可行走区域在 `data/locations.json`，改配置即可。
- 游戏倍率等设置（默认 1 游戏小时 = 30 秒现实时间）在 `data/config.json`。
- 21:00 Calypso 自动回床睡觉，06:00 起床继续活动。
- WORKING / FISHING 状态已留好接口（`BehaviorManager.request_work()` / `request_fishing()`），等待后续 Hermes 接入。
