import pygame

class Camera:
    """Camera that follows the player with zoom support"""

    def __init__(self, width, height, map_width, map_height, zoom=1.0):
        self.width = width
        self.height = height
        self.map_width = map_width
        self.map_height = map_height
        self.zoom = zoom

        # Camera position (top-left corner in world coordinates)
        self.x = 0
        self.y = 0

    def update(self, target_x, target_y):
        """Update camera position to center on target"""
        # Calculate camera position to center target, accounting for zoom
        self.x = target_x - (self.width / (2 * self.zoom))
        self.y = target_y - (self.height / (2 * self.zoom))

        # Clamp camera to map bounds
        max_x = self.map_width - (self.width / self.zoom)
        max_y = self.map_height - (self.height / self.zoom)

        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))

    def apply(self, entity_x, entity_y, width=0, height=0):
        """
        Convert world coordinates to screen coordinates
        Returns (screen_x, screen_y, scaled_width, scaled_height)
        """
        screen_x = (entity_x - self.x) * self.zoom
        screen_y = (entity_y - self.y) * self.zoom
        scaled_width = width * self.zoom
        scaled_height = height * self.zoom

        return (screen_x, screen_y, scaled_width, scaled_height)

    def apply_rect(self, rect):
        """Apply camera transformation to a pygame Rect"""
        x, y, w, h = self.apply(rect.x, rect.y, rect.width, rect.height)
        return pygame.Rect(int(x), int(y), int(w), int(h))

