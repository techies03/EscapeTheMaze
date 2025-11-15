import pygame
import sys
sys.path.insert(0, '..')

pygame.init()
# Need to create a display for pytmx to work
screen = pygame.display.set_mode((800, 600))

from map_loader import MapLoader

print("Testing map loader...")
try:
    loader = MapLoader("maps/level1.tmx")
    print("SUCCESS: Map loaded!")
    print(f"Objects found: {len(loader.get_objects())}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

pygame.quit()

