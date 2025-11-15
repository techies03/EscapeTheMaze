import pygame
import numpy as np

class FogOfWar:
    """Fog of War system that reveals map as player explores"""

    def __init__(self, map_width, map_height, tile_size=16, visibility_radius=96):
        self.map_width = map_width
        self.map_height = map_height
        self.tile_size = tile_size
        self.visibility_radius = visibility_radius

        # Grid to track explored areas (in tile coordinates)
        self.grid_width = int(map_width / tile_size) + 1
        self.grid_height = int(map_height / tile_size) + 1

        # Player position for fog calculation
        self.player_x = 0
        self.player_y = 0

        # Fog surface for rendering
        self.fog_surface = None
        self.needs_update = True

    def update_visibility(self, player_x, player_y):
        """Update visibility based on current player position (follows player, not exploration)"""
        # Store player position for rendering
        self.player_x = player_x
        self.player_y = player_y
        self.needs_update = True

    def render(self, surface, camera):
        """Render fog of war on the given surface"""
        if self.needs_update or self.fog_surface is None:
            self._update_fog_surface(camera)
            self.needs_update = False

        # Blend fog surface onto the main surface using alpha blending
        surface.blit(self.fog_surface, (0, 0))

    def _update_fog_surface(self, camera):
        """Update the fog surface based on distance from player"""
        # Create fog surface if it doesn't exist
        if self.fog_surface is None:
            self.fog_surface = pygame.Surface((camera.width, camera.height))
            self.fog_surface = self.fog_surface.convert_alpha()

        # Fill with transparent
        self.fog_surface.fill((0, 0, 0, 0))

        # Calculate visible tile range in screen space
        start_tile_x = max(0, int(camera.x / self.tile_size) - 1)
        end_tile_x = min(self.grid_width, int((camera.x + camera.width / camera.zoom) / self.tile_size) + 2)
        start_tile_y = max(0, int(camera.y / self.tile_size) - 1)
        end_tile_y = min(self.grid_height, int((camera.y + camera.height / camera.zoom) / self.tile_size) + 2)

        # Get player tile position
        player_tile_x = int(self.player_x / self.tile_size)
        player_tile_y = int(self.player_y / self.tile_size)
        tile_radius = self.visibility_radius / self.tile_size

        # Draw fog based on distance from player (follows player)
        for grid_x in range(start_tile_x, end_tile_x):
            for grid_y in range(start_tile_y, end_tile_y):
                # Calculate distance from player
                dx = grid_x - player_tile_x
                dy = grid_y - player_tile_y
                distance = (dx * dx + dy * dy) ** 0.5

                # Calculate fog darkness based on distance from player
                if distance > tile_radius:
                    # Outside visibility radius - full fog
                    fog_alpha = 180
                elif distance > tile_radius * 0.7:
                    # Edge of visibility - gradient fog
                    fade_ratio = (distance - tile_radius * 0.7) / (tile_radius * 0.3)
                    fog_alpha = int(180 * fade_ratio)
                else:
                    # Inside visibility - no fog
                    continue

                # Convert tile to screen coordinates
                world_x = grid_x * self.tile_size
                world_y = grid_y * self.tile_size
                screen_x, screen_y, tile_w, tile_h = camera.apply(world_x, world_y, self.tile_size, self.tile_size)

                # Draw fog tile
                fog_rect = pygame.Rect(int(screen_x), int(screen_y), int(tile_w) + 1, int(tile_h) + 1)
                pygame.draw.rect(self.fog_surface, (0, 0, 0, fog_alpha), fog_rect)

