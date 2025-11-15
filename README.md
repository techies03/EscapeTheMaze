# Escape The Maze – TMX Mechanics Overview

This document summarizes all gameplay mechanics, inferred behaviors, and runtime systems based on the TMX level provided. Everything is grouped by feature, with clear priorities and implementation hints.

---

## 🧍 Player Spawn & Initial Sizing

**TMX Data:**  
`object Player Spawn (id=8)`  
- `obj_name: player_spawn`  
- `x=62.66, y=46.66`  
- `width=19.33, height=20`

**Behaviour:**  
- Player spawns at this position when the level loads.  
- Treat `(x, y)` as the **mid-bottom anchor** of the player.

**Notes & Hints:**  
- Since tiles are **16×16**, player sprites should be ~16×24 in visual size.  
- Normalize the hitbox to tile units so movement feels consistent.

---

## 🧱 Tile Collision (Solid Layer)

**TMX:** `Collision` tile layer containing many solid tile indices (e.g., tile 79).

**Behaviour:**  
- Used for physics/collision checks for players, enemies, objects.

**Hints:**  
- Build a **collision grid** at runtime from this layer.  
- Resolve collisions separately on X and Y.  
- Use `pygame.Rect` for tile rects.

---

## 🚪 Doors (Locked Doors & Final Door)

**TMX Objects:** Door (id: 2, 3) and FinalDoor (id: 5)  
- `obj_type: door`  
- `required_key: silver/golden`  
- `count: 4 or 2`  
- Optional: `orientation`

**Behaviour:**  
- Doors remain locked until player has enough keys.  
- Interacting/overlapping checks if:  
  `inventory[required_key] >= count`

**Hints:**  
- When unlocked: remove collision, play animation.  
- `orientation` may determine which sprite animation to play.

---

## 🔑 Collectible Keys (Silver & Golden)

**TMX Objects:** id 11–16  
- `obj_type: collectible`  
- `item: key`  
- `key_type: silver/golden`  
- `frames: 4`

**Behaviour:**  
- Picking up a key increases inventory of that key type.  
- Used to unlock doors above.

**Hints:**  
- Remove key object after pickup.  
- Update HUD to show counts.

---

## 🪙 Coins / Score Items

**TMX Objects:** many (id 19..22, 30..36)  
- `item: coin`  
- `value: 10`  
- `frames: 4`

**Behaviour:**  
- Increases score on pickup.  
- Animated coins provide visual feedback.

**Hints:**  
- Play coin SFX.  
- Spawn small particle effects if desired.

---

## 🧪 Potions (Healing Items)

**TMX Objects:** id 39, 40  
- `item: potion`  
- `heal: 25`  
- `frames: 4`

**Behaviour:**  
- Heal player HP by given value.  
- Could be auto-use or stored.

**Hints:**  
- If instant-use: flash HP bar.  
- If stored: show count on HUD.

---

## 🪜 Ladder / Level Transition

**TMX:** Ladder (id=18)  
- `obj_type: ladder`  
- `destination: "level2.tmx"`

**Behaviour:**  
- Touching/interacting loads the next level.  
- Player respawns at the next level’s spawn point.

**Hints:**  
- Implement fade-out → load → fade-in.  
- Ensure camera resets properly.

---

## 💀 Enemies (Skeletons)

**TMX Objects:** ids 45, 46, 47, 59, 61  
- `obj_type: enemy`  
- `obj_name: skeleton1`  
- Tile size 32×32

**Behaviour:**  
- Spawn enemy at given coordinates.

**Hints:**  
- Suggested simple AI:  
  - idle → patrol → chase  
  - chase when player within radius  
- Make collision hitbox smaller than sprite for fairness.

---

## ⚠️ Traps (Spikes / Peaks)

**TMX Objects:** ids 86–110  
- `obj_type: trap`  
- `obj_name: peaks`  
- `damage: 25`  
- `frames: 4`  
- `frame_duration: 0.15`

**Behaviour:**  
- Animated spike traps.  
- Damage player when overlapping during “active” frames.

**Hints:**  
- Give player **i-frames** so spikes don’t kill instantly.  
- Use `AnimatedTrap` class with timing.

---

## 🎞️ Object Animation System

Many objects include:
- `frames`
- `frame_duration`

**Behaviour:**  
Use these properties to drive animations (coins, keys, potions, traps).

**Hints:**  
- Implement a reusable `AnimatedEntity` base class.  
- Avoid hardcoded sprite paths; use tileset frame indices.

---

## 🗂️ Object Types & Runtime Grouping

Common TMX prop: `obj_type`  
Examples:  
`door`, `spawn`, `collectible`, `ladder`, `enemy`, `trap`

**Behaviour:**  
- The map loader should create the correct class based on `obj_type`.

**Example:**  
```python
if obj.properties['obj_type'] == 'collectible':
    spawn Collectible(obj)
```

## 📏 Hitbox Sizes & Visual Alignment

TMX uses different object sizes:

- Keys / Coins / Potions → **16×16**
- Enemies → **32×32**
- Player spawn → **~19×20**

**Hints:**
- Standardize hitboxes (e.g., player width 12–14 px) so movement feels fair and consistent.

**Use:**
```python
rect.inflate(-n, -m)
```
## 🧭 HUD & Feedback

TMX implies the need for a basic heads-up display (HUD) showing:
- Silver key count
- Golden key count
- Score
- HP bar
- Door locked/unlocked messages
- Pickup notifications

**Behaviour:**
The HUD should always reflect:
- `player.inventory`
- `player.hp`
- `player.score`

## 🎥 Map Size & Camera Behavior

Map dimensions: **50 × 38** tiles (16 px each).

**Behaviour:**
- The camera follows the player.
- Camera must **clamp** to map boundaries so it never shows outside the world.

**Formula:**
```python
camera_offset = player.center - (screen_w/2, screen_h/2)
camera_offset = clamp(camera_offset, map_bounds)
```

## 🛠️ Developer Debug Tools

Useful debug features for development:
- Draw object IDs above each object
- Toggle visibility of the collision layer
- Show collision hitboxes
- Highlight object groups (doors, traps, collectibles, etc.)
These tools make gameplay tuning and level testing much easier.

## 🧩 Balance & Design Notes

Based on map content:
- Silver keys required → **4**
- Golden keys required → **2**
- Potion heal → **25**
- Spike damage → **25**
- Ideal player max HP → **100** (multiple of 25)
Enemies are sparse, so a simple patrol → chase AI suits the map well.

## 🧱 Minimum Runtime Classes Needed

| Class           | Purpose                            |
| --------------- | ---------------------------------- |
| **Player**      | Movement, HP, inventory, i-frames  |
| **TileMap**     | Layer rendering, collision grid    |
| **Door**        | Key checks, locked/open animations |
| **Collectible** | Coins, keys, potions pickup logic  |
| **Enemy**       | AI, hitbox, movement               |
| **Trap**        | Animated spike logic + damage      |
| **Ladder**      | Level transition to next map       |
