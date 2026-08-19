# Calypso Sprite Sheet Scan

Result of scanning every PNG in `pictures/Calypso/` on 2026-08-19. The scan
does **not** assume 64×64 frames or a fixed frame count: frames are located by
finding fully transparent column gutters, then each content run is cropped to
its tight bounding box. `sleep.png` has no gutters and is treated as a single
wide frame.

## Summary

| Sheet | Size | Alpha channel | Layout | Frames | Frame sizes (per frame) | Gutter pitch |
| --- | --- | --- | --- | --- | --- | --- |
| `front_walk.png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 156×378, 173×379, 184×378, 155×379 | 297, 294, 307 |
| `back_walk.png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 149×379, 171×378, 176×378, 154×379 | 274, 304, 312 |
| `left_walk.png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 162×380, 182×379, 148×380, 160×380 | 292, 352, 266 |
| `right_walk.png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 166×378, 153×378, 182×378, 148×379 | 287, 313, 302 |
| `front_rest.png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 259×337, 257×338, 254×337, 260×337 | 304, 301, 294 |
| `back_rest .png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 258×337, 257×338, 253×338, 259×337 | 303, 301, 295 |
| `sleep.png` | 1312×816 | RGBA, yes | 1 row × 1 col | 1 | 1276×291 (single frame) | — |
| `typing.png` | 1312×816 | RGBA, yes | 1 row × 4 col | 4 | 230×379, 240×379, 237×379, 234×378 | 322, 332, 315 |

All sheets are `1312×816` RGBA. Between 67% and 86% of each sheet is fully
transparent padding; 11 000–20 000 pixels per sheet are semi-transparent
(anti-aliased edges). Every sheet is single-row; none uses a second row.

## Key findings

1. **No fixed grid.** Frames in the same sheet vary in size (e.g.
   `front_walk.png`: 155×379 → 184×378) and the spacing between frame origins
   is irregular (266–352 px). Slicing these sheets with a uniform grid would
   clip or mis-center the frames.
2. **`sleep.png` is one frame.** It is a single connected content region
   (1276×291) with no transparent vertical separator anywhere, so it must not
   be split into two half-frames.
3. **Standing vs. lying heights differ.** Rest frames are ~338 px tall, walk
   and typing frames ~378–380 px, the sleep pose only 291 px. Animations are
   bottom-aligned to a common 380 px cell so feet stay planted on the same
   point across animations.
4. **`back_rest .png` contains a space** before `.png`; it is referenced with
   that exact name.

## Frame bounding boxes (x0, y0, x1, y1)

`front_walk.png`

```
#0 (132, 202, 287, 579)   #1 (429, 201, 601, 579)
#2 (723, 202, 906, 579)   #3 (1030, 201, 1184, 579)
```

`back_walk.png`

```
#0 (134, 201, 282, 579)   #1 (408, 202, 578, 579)
#2 (712, 202, 887, 579)   #3 (1024, 201, 1177, 579)
```

`left_walk.png`

```
#0 (112, 201, 273, 580)   #1 (404, 201, 585, 579)
#2 (756, 201, 903, 580)   #3 (1022, 201, 1181, 580)
```

`right_walk.png`

```
#0 (126, 201, 291, 578)   #1 (413, 202, 565, 579)
#2 (726, 201, 907, 578)   #3 (1028, 201, 1175, 579)
```

`front_rest.png`

```
#0 (77, 203, 335, 539)    #1 (381, 202, 637, 539)
#2 (682, 203, 935, 539)   #3 (976, 203, 1235, 539)
```

`back_rest .png`

```
#0 (78, 203, 335, 539)    #1 (381, 202, 637, 539)
#2 (682, 202, 934, 539)   #3 (977, 203, 1235, 539)
```

`sleep.png`

```
#0 (18, 242, 1293, 532)
```

`typing.png`

```
#0 (51, 235, 280, 613)    #1 (373, 235, 612, 613)
#2 (705, 235, 941, 613)   #3 (1020, 235, 1253, 612)
```

## AnimatedSprite2D animations

`scenes/calypso.tscn` contains the `AnimatedSprite2D` node. In
`scripts/calypso.gd`, `_build_sprite_frames()` loads each sheet and builds
`SpriteFrames` animations at runtime using the same detection above:

| Animation | Source sheet | Frames | FPS (config) |
| --- | --- | --- | --- |
| `walk_down` | `front_walk.png` | 4 | `movement/walk_fps` (8) |
| `walk_up` | `back_walk.png` | 4 | `movement/walk_fps` (8) |
| `walk_left` | `left_walk.png` | 4 | `movement/walk_fps` (8) |
| `walk_right` | `right_walk.png` | 4 | `movement/walk_fps` (8) |
| `idle_down` | `front_rest.png` | 4 | `movement/idle_fps` (4) |
| `idle_up` | `back_rest .png` | 4 | `movement/idle_fps` (4) |
| `sleep` | `sleep.png` | 1 | `movement/sleep_fps` (2) |
| `typing` | `typing.png` | 4 | `movement/walk_fps` (8) |

Each frame texture is cut to its tight bounding box, horizontally centered on
a per-animation canvas, and bottom-aligned on the common 380 px cell height so
every pose stands on the same baseline. The `AnimatedSprite2D` offset is set to
`-cell_height/2`, and the character's visual width used for scaling comes only
from the four walk sheets.

> Fix included in this pass: `SpriteSheetUtils._tight_rect()` previously
> assigned `max_y = y` instead of `maxi(max_y, y)`, so every frame's bottom
> edge was clipped to the bottom of the frame's *rightmost* content column
> (feet were cut off). The measured heights above are the true tight
> bounding boxes after the fix.

Re-run the scan any time with:

```
godot --headless --path . --script res://scripts/tools/scan_calypso_sheets.gd
```
