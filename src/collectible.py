import pygame
import os

class Collectible:
    """Collectible items like coins, keys, and potions"""

    def __init__(self, x, y, item_type, key_type='', value=10, heal=25, frames=4):
        self.x = x
        self.y = y
        self.item_type = item_type  # coin, key, potion
        self.key_type = key_type  # silver, golden (for keys)
        self.value = value  # coin value
        self.heal = heal  # healing amount for potions
        self.frames = frames

        # Size
        self.width = 16
        self.height = 16

        # Animation
        self.animation_timer = 0
        self.frame_index = 0
        self.frame_duration = 0.15

        # Load sprite
        self.sprite_frames = self._load_sprites()
        self.sprite = None
        self._update_sprite()

    def _load_sprites(self):
        """Load collectible sprites"""
        frames = []
        base_path = "assets/2D Pixel Dungeon Asset Pack/items and trap_animation"

        # Determine folder and file based on item type
        if self.item_type == 'coin':
            folder = "coin"
            # Coins are coin_1.png to coin_4.png
            for i in range(1, self.frames + 1):
                filepath = os.path.join(base_path, folder, f"coin_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)
        elif self.item_type == 'key':
            folder = "keys"
            if self.key_type == 'silver':
                # Silver keys are keys_2_1.png to keys_2_4.png
                for i in range(1, self.frames + 1):
                    filepath = os.path.join(base_path, folder, f"keys_2_{i}.png")
                    if os.path.exists(filepath):
                        sprite = pygame.image.load(filepath).convert_alpha()
                        frames.append(sprite)
            else:
                # Golden keys are keys_1_1.png to keys_1_4.png
                for i in range(1, self.frames + 1):
                    filepath = os.path.join(base_path, folder, f"keys_1_{i}.png")
                    if os.path.exists(filepath):
                        sprite = pygame.image.load(filepath).convert_alpha()
                        frames.append(sprite)
        elif self.item_type == 'potion':
            folder = "flasks"
            # Potions are flasks_1_1.png to flasks_1_4.png
            for i in range(1, self.frames + 1):
                filepath = os.path.join(base_path, folder, f"flasks_1_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)
        else:
            return [self._create_placeholder()]

        return frames if frames else [self._create_placeholder()]

    def _create_placeholder(self):
        """Create placeholder sprite"""
        surface = pygame.Surface((16, 16))

        if self.item_type == 'coin':
            surface.fill((255, 215, 0))  # Gold
        elif self.item_type == 'key':
            if self.key_type == 'silver':
                surface.fill((192, 192, 192))  # Silver
            else:
                surface.fill((255, 215, 0))  # Gold
        elif self.item_type == 'potion':
            surface.fill((255, 0, 0))  # Red

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

    def check_collision(self, player):
        """Check if player collects this item"""
        item_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        player_rect = player.get_rect()
        return item_rect.colliderect(player_rect)

    def collect(self, player):
        """Apply item effect to player"""
        if self.item_type == 'coin':
            player.add_score(self.value)
        elif self.item_type == 'key':
            player.add_key(self.key_type)
        elif self.item_type == 'potion':
            player.heal(self.heal)

    def render(self, surface, camera):
        """Render collectible sprite"""
        if self.sprite:
            screen_x, screen_y, scaled_w, scaled_h = camera.apply(self.x, self.y, self.width, self.height)

            if camera.zoom != 1.0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
                surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
            else:
                surface.blit(self.sprite, (int(screen_x), int(screen_y)))
