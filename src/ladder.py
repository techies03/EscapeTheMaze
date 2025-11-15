import pygame
from sound_manager import sound_manager

class Ladder:
    """Ladder/Exit that leads to the next level"""

    def __init__(self, x, y, destination, gid, tmx_data):
        self.x = x
        self.y = y
        self.destination = destination  # Next level file
        self.gid = gid  # Tile GID from TMX
        self.tmx_data = tmx_data

        # Size
        self.width = 16
        self.height = 16

        # Load sprite from TMX tileset
        self.sprite = self._load_sprite_from_tmx()

        # Interaction state
        self.show_message = False
        self.message_timer = 0

    def _load_sprite_from_tmx(self):
        """Load ladder sprite from TMX tileset using gid"""
        if self.tmx_data:
            tile_image = self.tmx_data.get_tile_image_by_gid(self.gid)
            if tile_image:
                return tile_image

        # Fallback: create simple colored sprite
        surface = pygame.Surface((self.width, self.height))
        surface.fill((150, 100, 50))  # Brown for ladder
        return surface

    def check_collision(self, player):
        """Check if player is near the ladder"""
        ladder_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        player_rect = player.get_rect()

        # Expand collision area slightly for interaction
        interaction_rect = ladder_rect.inflate(8, 8)

        return interaction_rect.colliderect(player_rect)

    def interact(self, player):
        """Player interacts with ladder to go to next level"""
        self.show_message = True
        self.message_timer = 2.0
        # Stage complete SFX
        sound_manager.play('stage_complete')
        print(f"TODO: Go to next level: {self.destination}")
        return True

    def update(self, dt):
        """Update ladder state"""
        if self.show_message:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.show_message = False

    def render(self, surface, camera, paused: bool = False):
        """Render ladder sprite; suppress interaction message while paused."""
        screen_x, screen_y, scaled_w, scaled_h = camera.apply(self.x, self.y, self.width, self.height)

        if camera.zoom != 1.0:
            scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
            surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
        else:
            surface.blit(self.sprite, (int(screen_x), int(screen_y)))

        # Show interaction message if needed and not paused
        if self.show_message and not paused:
            font = pygame.font.Font(None, 20)
            text = font.render("Press E to exit to next level", True, (255, 255, 0))

            text_x = screen_x - text.get_width() // 2 + scaled_w // 2
            text_y = screen_y - 20
            surface.blit(text, (int(text_x), int(text_y)))
