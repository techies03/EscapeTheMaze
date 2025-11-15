import pygame
import os
import math
from sound_manager import sound_manager

class Player:
    """Player character with movement, combat, and inventory"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 16
        self.height = 24

        # Stats
        self.max_hp = 100
        self.hp = self.max_hp
        self.speed = 80  # pixels per second
        self.attack_damage = 30
        self.score = 0

        # Inventory
        self.inventory = {
            'silver': 0,
            'golden': 0
        }

        # Movement state
        self.velocity_x = 0
        self.velocity_y = 0
        self.facing = 'down'  # down, up, left, right

        # Animation state
        self.state = 'idle'  # idle, run, attack, death
        self.animation_timer = 0
        self.frame_index = 0
        self.attacking = False
        self.attack_timer = 0
        self.attack_duration = 0.3

        # Invincibility frames (for taking damage)
        self.invincible = False
        self.invincible_timer = 0
        self.invincible_duration = 1.0

        # Debug flag for collision diagnostics
        self.debug_collision = False

        # Load animations
        self.animations = self._load_animations()

        # Current sprite
        self.sprite = None
        self._update_sprite()

        # Feet hitbox size (narrower and shorter than logical size)
        self.feet_width = 10
        self.feet_height = 8

        # Track if damage dealt in current attack
        self.attack_damage_applied = False

    def _load_animations(self):
        """Load player sprite animations from RPG_Hero folder"""
        animations = {}
        base_path = "assets/RPG_Hero"

        # Animation types and their frame counts
        anim_types = {
            'idle': 4,
            'run': 6,
            'attack': 7,  # Attack has 7 frames
            'death': 9
        }

        directions = ['down', 'up', 'left', 'right']

        for anim_type, frame_count in anim_types.items():
            for direction in directions:
                key = f"{anim_type}_{direction}"
                frames = []

                # Try to load sprite sheet
                sprite_path = os.path.join(base_path, anim_type, f"{anim_type}_{direction}_40x40.png")

                if os.path.exists(sprite_path):
                    sprite_sheet = pygame.image.load(sprite_path).convert_alpha()
                    frame_width = 40
                    frame_height = 40

                    # Extract frames from sprite sheet
                    for i in range(frame_count):
                        frame = sprite_sheet.subsurface(pygame.Rect(i * frame_width, 0, frame_width, frame_height))
                        # Scale to 3x size (40x40 -> 120x120)
                        scaled_frame = pygame.transform.scale(frame, (frame_width * 3, frame_height * 3))
                        frames.append(scaled_frame)

                animations[key] = frames if frames else [self._create_placeholder()]

        return animations

    def _create_placeholder(self):
        """Create a placeholder sprite if assets are missing"""
        surface = pygame.Surface((120, 120))  # 40 * 3
        surface.fill((0, 150, 255))  # Blue color for player
        return surface

    def _update_sprite(self):
        """Update current sprite based on state and animation"""
        anim_key = f"{self.state}_{self.facing}"
        frames = self.animations.get(anim_key, [self._create_placeholder()])

        if frames:
            self.sprite = frames[self.frame_index % len(frames)]

    def update(self, dt, keys, collision_grid, doors=None):
        """Update player state"""
        if self.hp <= 0:
            self.state = 'death'
            return

        # Update invincibility
        if self.invincible:
            self.invincible_timer += dt
            if self.invincible_timer >= self.invincible_duration:
                self.invincible = False
                self.invincible_timer = 0

        # Handle attack
        if self.attacking:
            self.attack_timer += dt
            if self.attack_timer >= self.attack_duration:
                self.attacking = False
                self.attack_timer = 0
                self.state = 'idle'
                self.attack_damage_applied = False  # ready for next attack

        # Handle input
        if not self.attacking:
            self._handle_input(keys)
            self._handle_movement(dt, collision_grid, doors)

        # Update animation
        self._update_animation(dt)

    def _handle_input(self, keys):
        """Handle keyboard input"""
        # Movement
        self.velocity_x = 0
        self.velocity_y = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity_x = -1
            self.facing = 'left'
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity_x = 1
            self.facing = 'right'

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.velocity_y = -1
            self.facing = 'up'
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.velocity_y = 1
            self.facing = 'down'

        # Update state based on movement
        if self.velocity_x != 0 or self.velocity_y != 0:
            self.state = 'run'
        else:
            self.state = 'idle'

        # Attack
        if keys[pygame.K_SPACE] and not self.attacking:
            self.attacking = True
            self.state = 'attack'
            self.frame_index = 0
            self.animation_timer = 0
            self.attack_damage_applied = False  # reset damage flag at attack start
            # Play attack SFX at attack start (even if no hit occurs)
            sound_manager.play('attack', volume=0.5)

    def _handle_movement(self, dt, collision_grid, doors=None):
        """Handle player movement with collision detection"""
        if self.velocity_x == 0 and self.velocity_y == 0:
            return

        # Normalize diagonal movement
        if self.velocity_x != 0 and self.velocity_y != 0:
            self.velocity_x *= 0.707
            self.velocity_y *= 0.707

        # Calculate movement (could be fractional)
        move_x = self.velocity_x * self.speed * dt
        move_y = self.velocity_y * self.speed * dt

        # Attempt stepped movement to avoid getting stuck on one-pixel collisions
        self._step_move(move_x, move_y, collision_grid, doors)

    def _step_move(self, move_x, move_y, collision_grid, doors):
        """Move in small steps (fractional) up to the requested delta until a collision occurs.
        This preserves smooth sub-pixel movement while preventing the player from being blocked
        prematurely when sliding along walls (fixes asymmetric up/down behavior).
        """
        # Number of steps is the ceiling of the largest absolute delta in pixels
        steps = max(1, int(math.ceil(max(abs(move_x), abs(move_y)))))

        step_x = move_x / steps
        step_y = move_y / steps

        for i in range(steps):
            new_x = self.x + step_x
            new_y = self.y + step_y

            # If both axes clear, apply both
            if not self._check_collision(new_x, new_y, collision_grid, doors):
                self.x = new_x
                self.y = new_y
                continue

            # If combined blocked, try moving X only
            if not self._check_collision(new_x, self.y, collision_grid, doors):
                self.x = new_x
                continue

            # Try moving Y only
            if not self._check_collision(self.x, new_y, collision_grid, doors):
                self.y = new_y
                continue
            else:
                # If moving downward and blocked, snap to the top edge of the blocking tile
                if step_y > 0:
                    feet_new = self._feet_rect_at(self.x, new_y)
                    tile_size = 16
                    blocking_row = max(0, (feet_new.bottom - 1) // tile_size)
                    tile_top = blocking_row * tile_size
                    # Place bottom of player at tile_top
                    self.y = tile_top - self.height
                # For other directions, just stop (could add snapping similarly)

            # Blocked on both or Y-only with snap applied, optional debug and stop
            if self.debug_collision:
                print(f"[DEBUG] Blocked movement at step {i+1}/{steps}, snapped Y to {self.y:.2f}" if step_y>0 else f"[DEBUG] Blocked movement at step {i+1}/{steps}")
            break

    def _feet_rect_at(self, x, y):
        """Compute the collision rectangle at the player's feet for a given top-left (x,y)."""
        offset_x = (self.width - self.feet_width) // 2
        offset_y = self.height - self.feet_height
        return pygame.Rect(int(x + offset_x), int(y + offset_y), int(self.feet_width), int(self.feet_height))

    def _check_collision(self, x, y, collision_grid, doors=None):
        """Check if player collides with tiles or doors, using the feet hitbox."""
        feet = self._feet_rect_at(x, y)

        # Calculate tile range based on feet rect
        tile_size = 16
        start_tile_x = max(0, feet.left // tile_size)
        end_tile_x = feet.right - 1
        end_tile_x = max(0, end_tile_x // tile_size)
        start_tile_y = max(0, feet.top // tile_size)
        end_tile_y = feet.bottom - 1
        end_tile_y = max(0, end_tile_y // tile_size)

        # Clamp to grid bounds
        max_y = len(collision_grid) - 1
        max_x = len(collision_grid[0]) - 1 if collision_grid and collision_grid[0] else 0
        end_tile_x = max(0, min(end_tile_x, max_x))
        end_tile_y = max(0, min(end_tile_y, max_y))

        # Check tile collision
        for tile_y in range(start_tile_y, end_tile_y + 1):
            for tile_x in range(start_tile_x, end_tile_x + 1):
                if collision_grid[tile_y][tile_x]:
                    return True

        # Check door collision (if doors provided)
        if doors:
            for door in doors:
                if door.blocks_movement(feet):  # pass the feet rect
                    return True

        return False

    def _update_animation(self, dt):
        """Update animation frame"""
        self.animation_timer += dt

        # Frame duration based on state
        if self.state == 'run':
            frame_duration = 0.1
        elif self.state == 'attack':
            frame_duration = self.attack_duration / 7  # 7 frames for attack
        else:
            frame_duration = 0.15

        if self.animation_timer >= frame_duration:
            self.animation_timer = 0
            self.frame_index += 1

        self._update_sprite()

    def take_damage(self, damage):
        """Take damage from enemies or traps"""
        if not self.invincible and self.hp > 0:
            self.hp = max(0, self.hp - damage)
            self.invincible = True
            self.invincible_timer = 0

    def heal(self, amount):
        """Heal player"""
        self.hp = min(self.max_hp, self.hp + amount)

    def add_key(self, key_type):
        """Add a key to inventory"""
        if key_type in self.inventory:
            self.inventory[key_type] += 1

    def has_keys(self, key_type, count):
        """Check if player has enough keys"""
        return self.inventory.get(key_type, 0) >= count

    def remove_keys(self, key_type, count):
        """Remove keys from inventory"""
        if key_type in self.inventory:
            self.inventory[key_type] -= count

    def add_score(self, points):
        """Add to player score"""
        self.score += points

    def get_rect(self):
        """Get player collision rectangle (feet) for interactions/collisions."""
        return self._feet_rect_at(self.x, self.y)

    def render(self, surface, camera):
        """Render player sprite"""
        if self.sprite:
            # Calculate screen position
            sprite_width = self.sprite.get_width()
            sprite_height = self.sprite.get_height()

            # Center sprite on player position
            render_x = self.x - (sprite_width / camera.zoom - self.width) / 2
            render_y = self.y - (sprite_height / camera.zoom - self.height)

            screen_x, screen_y, scaled_w, scaled_h = camera.apply(render_x, render_y, sprite_width / camera.zoom, sprite_height / camera.zoom)

            # Scale sprite for zoom
            if camera.zoom != 1.0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
                surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
            else:
                surface.blit(self.sprite, (int(screen_x), int(screen_y)))
