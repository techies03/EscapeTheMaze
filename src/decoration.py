import pygame
import os

class Decoration:
    """Animated decorations like torches, candles, etc."""

    def __init__(self, x, y, decoration_type, gid, frames=4):
        self.x = x
        self.y = y
        self.decoration_type = decoration_type  # torch, sidetorch, candlesticklong
        self.gid = gid  # Tile GID from TMX
        self.frames_count = frames

        # Size
        self.width = 16
        self.height = 16

        # Animation
        self.animation_timer = 0
        self.frame_index = 0
        self.frame_duration = 0.15  # Flickering animation

        # Load sprites
        self.sprite_frames = self._load_sprites()
        self.sprite = None
        self._update_sprite()

    def _load_sprites(self):
        """Load decoration animation frames"""
        frames = []
        base_path = "assets/2D Pixel Dungeon Asset Pack/items and trap_animation/torch"

        # Determine file pattern based on decoration type
        if self.decoration_type == 'torch':
            # torch_1.png to torch_4.png
            for i in range(1, self.frames_count + 1):
                filepath = os.path.join(base_path, f"torch_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)

        elif self.decoration_type == 'sidetorch':
            # side_torch_1.png to side_torch_4.png
            for i in range(1, self.frames_count + 1):
                filepath = os.path.join(base_path, f"side_torch_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)

        elif self.decoration_type == 'candlesticklong':
            # candlestick_2_1.png to candlestick_2_4.png
            for i in range(1, self.frames_count + 1):
                filepath = os.path.join(base_path, f"candlestick_2_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)

        return frames if frames else [self._create_placeholder()]

    def _create_placeholder(self):
        """Create placeholder sprite"""
        surface = pygame.Surface((16, 16))
        surface.fill((255, 150, 0))  # Orange for fire
        return surface

    def _update_sprite(self):
        """Update current sprite frame"""
        if self.sprite_frames:
            self.sprite = self.sprite_frames[self.frame_index % len(self.sprite_frames)]

    def update(self, dt):
        """Update animation"""
        self.animation_timer += dt

        if self.animation_timer >= self.frame_duration:
            self.animation_timer = 0
            self.frame_index += 1
            self._update_sprite()

    def render(self, surface, camera):
        """Render decoration sprite"""
        if self.sprite:
            screen_x, screen_y, scaled_w, scaled_h = camera.apply(self.x, self.y, self.width, self.height)

            if camera.zoom != 1.0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
                surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
            else:
                surface.blit(self.sprite, (int(screen_x), int(screen_y)))

