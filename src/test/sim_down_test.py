import os, sys, math
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from map_loader import MapLoader
from player import Player

pygame.init()
# minimal display for convert_alpha
pygame.display.set_mode((1,1))

ml = MapLoader("maps/level1.tmx")
grid = ml.collision_grid

# Find a walkable cell with a solid tile directly below it
pair = None
for y in range(len(grid)-1):
    for x in range(len(grid[0])):
        if not grid[y][x] and grid[y+1][x]:
            pair = (x, y)
            break
    if pair:
        break

if not pair:
    print("No walkable-above/solid-below pair found")
    sys.exit(0)

x, y = pair
# Place player near the bottom of the walkable tile, centered horizontally
px = x*16 + 0  # left align
py = y*16 + 0  # top of tile
p = Player(px, py)
# Disable loading heavy animations for speed (frames are already loaded in __init__)

# Move the player downward in many small steps
dt = 1/60.0
p.velocity_x = 0
p.velocity_y = 1
# Step 120 frames (~2 sec)
for i in range(120):
    p._handle_movement(dt, grid, doors=None)

# Compute the max y where the player's bottom should be <= top of solid tile
expected_bottom = (y+1)*16  # top of solid tile
actual_bottom = p.y + p.height
print(f"Pair at tile ({x},{y}) below is solid. Expected bottom <= {expected_bottom}, actual bottom={actual_bottom:.2f}, player y={p.y:.2f}")
print(f"delta(bottom - expected)={actual_bottom-expected_bottom:.2f} (<= 0 is correct)")

pygame.quit()

