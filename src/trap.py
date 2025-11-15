import pygame
import os

class Trap:
    """Animated trap that damages player"""

    def __init__(self, x, y, trap_type, damage, frames, frame_duration):
        self.x = x
        self.y = y
        self.trap_type = trap_type  # peaks, arrow, flamethrower
        self.damage = damage
        self.frames = frames
        self.frame_duration = frame_duration

        # Size
        self.width = 16
        self.height = 16

        # Animation
        self.animation_timer = 0
        self.frame_index = 0

        # Damage cooldown (prevent instant death)
        self.damage_cooldown = {}  # Track last damage time per player
        self.damage_interval = 1.0

        # Load sprites
        self.sprite_frames = self._load_sprites()
        self.sprite = None
        self._update_sprite()

    def _load_sprites(self):
        """Load trap animation frames"""
        frames = []
        base_path = "assets/2D Pixel Dungeon Asset Pack/items and trap_animation"

        if self.trap_type == 'peaks':
            folder = "peaks"
            # Peaks are peaks_1.png to peaks_4.png
            for i in range(1, self.frames + 1):
                filepath = os.path.join(base_path, folder, f"peaks_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)
        elif self.trap_type == 'arrow':
            folder = "arrow"
            for i in range(1, self.frames + 1):
                filepath = os.path.join(base_path, folder, f"arrow_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)
        elif self.trap_type == 'flamethrower':
            folder = "flamethrower"
            for i in range(1, self.frames + 1):
                filepath = os.path.join(base_path, folder, f"flamethrower_{i}.png")
                if os.path.exists(filepath):
                    sprite = pygame.image.load(filepath).convert_alpha()
                    frames.append(sprite)
        else:
            return [self._create_placeholder()]

        return frames if frames else [self._create_placeholder()]

    def _create_placeholder(self):
        """Create placeholder sprite"""
        surface = pygame.Surface((16, 16))
        surface.fill((200, 0, 0))  # Red for danger
        return surface

    def _update_sprite(self):
        """Update current sprite frame"""
        if self.sprite_frames:
            self.sprite = self.sprite_frames[self.frame_index % len(self.sprite_frames)]

    def update(self, dt):
        """Update trap animation"""
        self.animation_timer += dt

        # Determine frame duration
        current_frame = self.frame_index % len(self.sprite_frames) if self.sprite_frames else 0

        if self.trap_type == 'peaks':
            # Frame 2 (peaks_3.png) is the safe frame - stay there much longer
            if current_frame == 2:
                frame_duration = self.frame_duration * 10  # Stay 10x longer on safe frame (1.5 seconds)
            else:
                # Frames 0,1,3 (peaks_1, peaks_2, peaks_4) animate fast
                frame_duration = self.frame_duration * 0.5  # Fast animation (0.075 seconds each)
        else:
            frame_duration = self.frame_duration

        if self.animation_timer >= frame_duration:
            self.animation_timer = 0
            self.frame_index += 1
            self._update_sprite()

    def check_collision(self, player):
        """Check if player is hit by trap"""
        trap_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        player_rect = player.get_rect()

        if trap_rect.colliderect(player_rect):
            # For peaks, only damage on dangerous frames (not frame 2 which is peaks_3.png)
            if self.trap_type == 'peaks':
                # Frame index 2 (peaks_3.png) is safe
                if self.frame_index % len(self.sprite_frames) == 2:
                    return False

            # Check damage cooldown
            current_time = pygame.time.get_ticks() / 1000.0
            player_id = id(player)

            if player_id not in self.damage_cooldown:
                self.damage_cooldown[player_id] = 0

            if current_time - self.damage_cooldown[player_id] >= self.damage_interval:
                self.damage_cooldown[player_id] = current_time
                return True

        return False

    def render(self, surface, camera):
        """Render trap sprite"""
        if self.sprite:
            screen_x, screen_y, scaled_w, scaled_h = camera.apply(self.x, self.y, self.width, self.height)

            if camera.zoom != 1.0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
                surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
            else:
                surface.blit(self.sprite, (int(screen_x), int(screen_y)))

