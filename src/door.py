import pygame
from sound_manager import sound_manager

class Door:
    """Door that requires keys to open"""

    def __init__(self, x, y, required_key, count, orientation, gid, tmx_data):
        self.x = x
        self.y = y
        self.required_key = required_key  # silver, golden
        self.count = count  # number of keys required
        self.orientation = orientation  # left, right, up, down
        self.gid = gid  # Tile GID from TMX
        self.tmx_data = tmx_data  # TMX data to get tile image

        # Size
        self.width = 16
        self.height = 16

        # State
        self.is_open = False
        self.message_timer = 0
        self.show_message = False

        # For paired doors (left/right)
        self.paired_door = None

        # Load sprite from TMX tileset
        self.sprite = self._load_sprite_from_tmx()

    def _load_sprite_from_tmx(self):
        """Load door sprite from TMX tileset using gid"""
        if self.tmx_data:
            tile_image = self.tmx_data.get_tile_image_by_gid(self.gid)
            if tile_image:
                return tile_image

        # Fallback: create simple colored sprite
        surface = pygame.Surface((self.width, self.height))
        if self.required_key == 'silver':
            surface.fill((192, 192, 192))
        elif self.required_key == 'golden':
            surface.fill((255, 215, 0))
        else:
            surface.fill((139, 69, 19))
        return surface

    def set_paired_door(self, other_door):
        """Set a paired door (for left/right doors that open together)"""
        self.paired_door = other_door

    def blocks_movement(self, player_rect):
        """Check if door blocks player movement (only when closed)"""
        if self.is_open:
            return False

        door_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        return door_rect.colliderect(player_rect)

    def check_collision(self, player):
        """Check if player is near the door"""
        door_rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # Expand collision area slightly for interaction
        interaction_rect = door_rect.inflate(8, 8)
        player_rect = player.get_rect()

        return interaction_rect.colliderect(player_rect)

    def try_open(self, player):
        """Try to open door with player's keys"""
        if self.is_open:
            return True

        if player.has_keys(self.required_key, self.count):
            # Player has enough keys, open door
            player.remove_keys(self.required_key, self.count)
            self.is_open = True
            self.show_message = True
            self.message_timer = 2.0  # Show message for 2 seconds
            # Play open SFX (reuse potion chime subtly)
            sound_manager.play('potion', volume=0.3, cooldown=0.05)

            # Also open paired door (e.g., left/right doors open together)
            if self.paired_door:
                self.paired_door.is_open = True
                self.paired_door.show_message = True
                self.paired_door.message_timer = 2.0

            return True
        else:
            # Not enough keys
            self.show_message = True
            self.message_timer = 2.0
            # Removed walk fallback sound for now
            return False

    def update(self, dt):
        """Update door state"""
        if self.show_message:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.show_message = False

    def render(self, surface, camera, paused: bool = False):
        """Render door (only if not open). When paused, suppress floating messages."""
        if not self.is_open:
            screen_x, screen_y, scaled_w, scaled_h = camera.apply(self.x, self.y, self.width, self.height)

            if camera.zoom != 1.0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
                surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
            else:
                surface.blit(self.sprite, (int(screen_x), int(screen_y)))

            # Show message if needed (only when not paused)
            if self.show_message and not paused:
                font = pygame.font.Font(None, 20)
                if self.is_open:
                    text = font.render("Door Opened!", True, (0, 255, 0))
                else:
                    text = font.render(f"Need {self.count} {self.required_key} keys", True, (255, 0, 0))

                text_x = screen_x - text.get_width() // 2 + scaled_w // 2
                text_y = screen_y - 20
                surface.blit(text, (int(text_x), int(text_y)))
