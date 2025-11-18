# Escape The Maze

A small top‑down dungeon crawler built with Pygame and TMX maps. Find keys, unlock doors, avoid traps and enemies, and reach the exit ladder to escape. Includes a main menu, level select, and an in‑menu Instructions screen.

## Features
- TMX maps via PyTMX with animated tiles and decorations
- Player movement, combat, HP, score, and inventory (silver/golden keys)
- Doors with key requirements, spike traps, collectibles (coins, potions, keys)
- Enemies with simple AI and death animations
- Fog of war effect and a camera with zoom
- Menu system: Main Menu, Level Select, and Instructions
- Sound effects and music with a central Sound Manager (mute toggle in menu)

## Controls
- Move: W/A/S/D or Arrow Keys
- Attack: Space
- Interact/Use: E (e.g., ladders)
- Pause: Esc (Resume/Retry/Main Menu/Quit)

Menu navigation
- Up/Down or W/S to move the selection
- Enter/Space to select
- Esc to go back

Instructions screen
- From the Main Menu, choose “Instructions” to see an in‑game quick guide with controls and tips.

## Developer shortcuts (kept enabled, not shown in HUD)
These are available for testing but hidden from the on‑screen HUD:
- F1: Give silver keys
- F2: Give golden keys
- F3: Restore full HP
- F4: Toggle invincibility
- F5: Kill all enemies
- F6: Teleport near exit

## Install
1) Python 3.10+ is recommended
2) Install dependencies from requirements.txt
3) Ensure assets and maps folders remain in place

Quick setup (Windows, cmd):

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run
From the project root (Windows, cmd):

```bat
.venv\Scripts\activate
python src\main.py
```

Alternative (if you prefer the launcher):

```bat
py src\main.py
```

## Assets Packs
- https://pixel-poem.itch.io/dungeon-assetpuck

## Project structure (high level)
- `src/` – game code
  - `main.py` – app entry with menus and state management
  - `game.py` – game loop, entities, HUD, screens
  - `map_loader.py` – TMX loading, animated tiles, layers
  - `player.py`, `enemy.py`, `door.py`, `ladder.py`, `trap.py`, `collectible.py` – gameplay entities
  - `sound_manager.py` – music/SFX loading and playback
  - `camera.py`, `fog_of_war.py` – rendering helpers
- `maps/` – TMX levels (e.g., `level1.tmx`, `level2.tmx`)
- `assets/` – sprites, tilesets, and UI art (plus optional `assets/menu_bg.png` for menu background)
- `sounds/` – audio files

## Troubleshooting
- If you get an audio device error, try updating Pygame and your audio drivers, or set a different SDL audio driver in the environment.
- Window is too large? Change `window_size` in `src/main.py`.
- Performance: running without a debugger and closing other heavy apps can help. Ensure your Python and Pygame versions are up‑to‑date.

---

## Design/Mechanics Notes (detailed TMX overview)

The following section is the original mechanics overview for this project. It documents how TMX properties map to runtime behaviors and is useful for level design and implementation reference.

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
