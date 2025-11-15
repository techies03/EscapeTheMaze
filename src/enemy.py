import pygame
import os
import random
from sound_manager import sound_manager

class Enemy:
    """Enemy character with AI, animations, and combat"""

    def __init__(self, x, y, enemy_type, collision_grid):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type  # skeleton1, skeleton2, vampire
        self.collision_grid = collision_grid

        # Size (enemies are 32x32 in the map)
        self.width = 24
        self.height = 24

        # Stats based on enemy type
        self._init_stats()

        # AI state
        self.state = 'idle'  # idle, movement, attack, death
        self.direction = random.choice(['left', 'right'])
        self.patrol_timer = 0
        self.patrol_interval = 2.0
        self.aggro_range = 80
        self.attack_range = 20
        self.is_aggroed = False

        # Animation
        self.animation_timer = 0
        self.frame_index = 0

        # Attack system
        self.attack_cooldown = 0
        self.attack_cooldown_max = 0.6
        self.is_attacking = False  # Currently executing attack animation
        self.attack_damage_frame = 6  # Frame index when damage is dealt (7th frame, 0-indexed)
        self.has_dealt_damage = False  # Track if damage was dealt this attack
        # Wind-up before attack starts (short delay)
        self.attack_windup_duration = 0.25  # seconds
        self.attack_windup_timer = 0.0
        # Play death sound only once
        self.death_sound_played = False
        # Load animations
        self.animations = self._load_animations()
        self.sprite = None
        self._update_sprite()

    def _init_stats(self):
        """Initialize stats based on enemy type"""
        if self.enemy_type == 'skeleton1':
            self.max_hp = 50
            self.speed = 40
            self.damage = 15
        elif self.enemy_type == 'skeleton2':
            self.max_hp = 75
            self.speed = 30
            self.damage = 20
        elif self.enemy_type == 'vampire':
            self.max_hp = 100
            self.speed = 50
            self.damage = 30
        else:
            self.max_hp = 50
            self.speed = 40
            self.damage = 15

        self.hp = self.max_hp

    def _load_animations(self):
        """Load enemy animations from Enemy_Animations_Set folder"""
        animations = {}
        base_path = "assets/Enemy_Animations_Set"

        # Map enemy types to file prefixes
        enemy_prefix = f"enemies-{self.enemy_type}"

        # Animation states
        anim_states = ['idle', 'movement', 'attack', 'death']

        for state in anim_states:
            filename = f"{enemy_prefix}_{state}.png"

            # Special case for skeleton2 movement
            if self.enemy_type == 'skeleton2' and state == 'movement':
                filename = f"{enemy_prefix}_movemen.png"  # Typo in asset name

            filepath = os.path.join(base_path, filename)

            if os.path.exists(filepath):
                sprite_sheet = pygame.image.load(filepath).convert_alpha()

                # Determine frame count
                frame_width = 32
                frame_height = 32

                # Special frame counts for skeleton1
                if self.enemy_type == 'skeleton1':
                    if state == 'attack':
                        frame_count = 9
                    elif state == 'death':
                        frame_count = 17
                    elif state == 'movement':
                        frame_count = 10
                    else:  # idle
                        frame_count = sprite_sheet.get_width() // frame_width
                else:
                    frame_count = sprite_sheet.get_width() // frame_width

                frames = []
                for i in range(frame_count):
                    try:
                        frame = sprite_sheet.subsurface(pygame.Rect(i * frame_width, 0, frame_width, frame_height))
                        # Scale up enemy sprites for better visibility
                        scaled_frame = pygame.transform.scale(frame, (int(frame_width * 1.5), int(frame_height * 1.5)))
                        frames.append(scaled_frame)
                    except:
                        break

                animations[state] = frames if frames else [self._create_placeholder()]
            else:
                animations[state] = [self._create_placeholder()]

        return animations

    def _create_placeholder(self):
        """Create placeholder sprite if assets missing"""
        surface = pygame.Surface((48, 48))  # 32 * 1.5

        # Different colors for different enemy types
        if self.enemy_type == 'skeleton1':
            surface.fill((200, 200, 200))
        elif self.enemy_type == 'skeleton2':
            surface.fill((150, 150, 150))
        elif self.enemy_type == 'vampire':
            surface.fill((150, 0, 0))
        else:
            surface.fill((100, 100, 100))

        return surface

    def _update_sprite(self):
        """Update current sprite based on state"""
        frames = self.animations.get(self.state, [self._create_placeholder()])
        if frames:
            if self.state == 'attack_windup':
                # Use first attack frame (telegraph) instead of placeholder list
                attack_frames = self.animations.get('attack', [self._create_placeholder()])
                self.sprite = attack_frames[0]
                return
            # For death animation, stop at last frame instead of looping
            if self.state == 'death':
                frame_idx = min(self.frame_index, len(frames) - 1)
            else:
                frame_idx = self.frame_index % len(frames)
            self.sprite = frames[frame_idx]

    def update(self, dt, player):
        """Update enemy AI and state"""
        if self.hp <= 0:
            # Just update death animation, don't do AI logic
            self._update_animation(dt)
            return

        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        # Handle wind-up state
        if self.state == 'attack_windup':
            self.attack_windup_timer += dt
            # If player leaves attack range during wind-up, cancel
            dx_cancel = player.x - self.x
            dy_cancel = player.y - self.y
            if (dx_cancel*dx_cancel + dy_cancel*dy_cancel) ** 0.5 > self.attack_range + 4:
                # Cancel windup and resume behavior
                self.state = 'idle'
                self.attack_windup_timer = 0
            elif self.attack_windup_timer >= self.attack_windup_duration:
                # Transition into actual attack animation
                self.state = 'attack'
                self.is_attacking = True
                self.frame_index = 0
                self.animation_timer = 0
                self.has_dealt_damage = False
                self.attack_windup_timer = 0
            # Update sprite only (no movement)
            self._update_sprite()
            return

        # Check distance to player
        dx = player.x - self.x
        dy = player.y - self.y
        distance = (dx * dx + dy * dy) ** 0.5

        # Aggro logic
        if distance < self.aggro_range:
            self.is_aggroed = True

        if self.is_aggroed:
            if distance < self.attack_range:
                # In attack range
                if not self.is_attacking and self.attack_cooldown <= 0:
                    # Start wind-up phase instead of immediate attack
                    self.state = 'attack_windup'
                    self.attack_windup_timer = 0
                elif self.is_attacking:
                    # Continue attack animation
                    self.state = 'attack'
                else:
                    # Waiting for cooldown
                    self.state = 'idle'
            else:
                # Chase player
                self.state = 'movement'
                self._move_towards_player(dt, player)
        else:
            # Patrol behavior
            self._patrol(dt)

        # Update animation
        self._update_animation(dt)

        # Check if we should deal damage during attack animation
        if self.is_attacking and not self.has_dealt_damage:
            current_frame = self.frame_index % len(self.animations.get('attack', [self._create_placeholder()]))
            if current_frame == self.attack_damage_frame:
                # Deal damage on the 7th frame (index 6)
                self.attack(player)
                self.has_dealt_damage = True

    def _patrol(self, dt):
        """Simple patrol behavior"""
        self.patrol_timer += dt

        if self.patrol_timer >= self.patrol_interval:
            self.patrol_timer = 0
            # Change direction randomly
            self.direction = random.choice(['left', 'right', 'idle'])

        if self.direction == 'left':
            self.state = 'movement'
            self._move(-self.speed * dt, 0)
        elif self.direction == 'right':
            self.state = 'movement'
            self._move(self.speed * dt, 0)
        else:
            self.state = 'idle'

    def _move_towards_player(self, dt, player):
        """Move towards player"""
        dx = player.x - self.x
        dy = player.y - self.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance > 0:
            # Normalize and move
            dx /= distance
            dy /= distance

            move_x = dx * self.speed * dt
            move_y = dy * self.speed * dt

            self._move(move_x, move_y)

    def _move(self, dx, dy):
        """Move enemy with collision detection"""
        # Try horizontal movement
        new_x = self.x + dx
        if not self._check_collision(new_x, self.y):
            self.x = new_x

        # Try vertical movement
        new_y = self.y + dy
        if not self._check_collision(self.x, new_y):
            self.y = new_y

    def _check_collision(self, x, y):
        """Check collision with tiles"""
        tile_size = 16
        hitbox_width = 16
        hitbox_height = 16

        start_tile_x = max(0, int(x / tile_size))
        end_tile_x = int((x + hitbox_width) / tile_size)
        start_tile_y = max(0, int(y / tile_size))
        end_tile_y = int((y + hitbox_height) / tile_size)

        for tile_y in range(start_tile_y, end_tile_y + 1):
            for tile_x in range(start_tile_x, end_tile_x + 1):
                if tile_y < len(self.collision_grid) and tile_x < len(self.collision_grid[0]):
                    if self.collision_grid[tile_y][tile_x]:
                        return True
        return False

    def _update_animation(self, dt):
        """Update animation frame"""
        self.animation_timer += dt

        frame_duration = 0.15
        if self.state == 'attack':
            frame_duration = 0.08  # Faster attack animation (reduced from 0.1)
        elif self.state == 'death':
            frame_duration = 0.12

        if self.animation_timer >= frame_duration:
            self.animation_timer = 0

            # For death animation, stop at last frame
            if self.state == 'death':
                death_frames = self.animations.get('death', [self._create_placeholder()])
                if self.frame_index < len(death_frames) - 1:
                    self.frame_index += 1
                # If at last frame, stay there (don't increment)
            else:
                self.frame_index += 1

            # Check if attack animation is complete
            if self.is_attacking and self.state == 'attack':
                attack_frames = self.animations.get('attack', [self._create_placeholder()])
                if self.frame_index >= len(attack_frames):
                    # Attack animation finished
                    self.is_attacking = False
                    self.attack_cooldown = self.attack_cooldown_max
                    self.frame_index = 0
                    self.state = 'idle'
        elif self.state == 'attack_windup':
            # No frame advancement during wind-up; just keep first frame
            self._update_sprite()
            return

        self._update_sprite()

    def take_damage(self, damage):
        """Take damage"""
        prev_hp = self.hp
        self.hp = max(0, self.hp - damage)
        if self.hp <= 0:
            # Trigger death state
            if self.state != 'death':
                self.state = 'death'
                self.frame_index = 0
                self.animation_timer = 0
                self.is_attacking = False
            # Play death SFX once at death time
            if not self.death_sound_played:
                sound_manager.play('enemy_death', volume=0.5, cooldown=0.05)
                self.death_sound_played = True

    def attack(self, player):
        """Attack the player"""
        if self.attack_cooldown <= 0:
            player.take_damage(self.damage)
            self.attack_cooldown = self.attack_cooldown_max

    def check_collision(self, player, for_attack=False):
        """Check if enemy collides with player. If for_attack and player is attacking, enlarge hitbox."""
        enemy_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        if for_attack and player.attacking:
            # Inflate enemy rect to make attacks connect more easily
            # Inflate horizontally and vertically (tweakable)
            enemy_rect = enemy_rect.inflate(16, 16)
        player_rect = player.get_rect()
        return enemy_rect.colliderect(player_rect)

    def get_rect(self):
        """Return enemy base rectangle (without inflation)."""
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def render(self, surface, camera):
        """Render enemy sprite"""
        if self.sprite:
            # Center sprite on enemy position
            sprite_width = self.sprite.get_width()
            sprite_height = self.sprite.get_height()

            render_x = self.x - (sprite_width - self.width) / 2
            render_y = self.y - (sprite_height - self.height)

            screen_x, screen_y, scaled_w, scaled_h = camera.apply(render_x, render_y, sprite_width, sprite_height)

            # Scale for zoom
            if camera.zoom != 1.0:
                scaled_sprite = pygame.transform.scale(self.sprite, (int(scaled_w), int(scaled_h)))
                surface.blit(scaled_sprite, (int(screen_x), int(screen_y)))
            else:
                surface.blit(self.sprite, (int(screen_x), int(screen_y)))

            # Draw HP bar
            if self.hp < self.max_hp:
                bar_width = 30 * camera.zoom
                bar_height = 4 * camera.zoom
                bar_x = screen_x
                bar_y = screen_y - 8 * camera.zoom

                # Background
                pygame.draw.rect(surface, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))

                # HP fill
                hp_ratio = self.hp / self.max_hp
                pygame.draw.rect(surface, (0, 200, 0), (bar_x, bar_y, bar_width * hp_ratio, bar_height))
