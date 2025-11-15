import pygame

from player import Player
from enemy import Enemy
from collectible import Collectible
from trap import Trap
from door import Door
from ladder import Ladder
from camera import Camera
from fog_of_war import FogOfWar
from map_loader import MapLoader
from sound_manager import sound_manager

class Game:
    """Main game class that manages game state and objects"""

    def __init__(self, initial_level: str = "maps/level1.tmx", screen=None):
        # Screen settings with zoom effect
        self.WINDOW_WIDTH = 960
        self.WINDOW_HEIGHT = 720
        if screen is not None:
            self.screen = screen
            pygame.display.set_caption("Escape The Maze")
        else:
            self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
            pygame.display.set_caption("Escape The Maze")

        # Game state
        self.paused = False
        self.game_over = False
        self.victory = False
        # Track score at start of current level for retry resets
        self.level_start_score = 0
        self.level_start_hp = 0  # HP at start of level (for retry restoration)
        # Request to exit back to main menu (handled by app)
        self.request_exit_to_menu = False

        # Track current level file
        self.current_level = initial_level

        # Pause menu state
        self.pause_menu_options = ["Resume", "Retry", "Main Menu", "Quit"]
        self.pause_menu_index = 0

        # Game Over menu state
        self.game_over_menu_options = ["Retry", "Quit"]
        self.game_over_menu_index = 0
        # Victory menu state
        self.victory = False
        self.victory_menu_options = ["Main Menu", "Quit"]
        self.victory_menu_index = 0

        # Load the map
        self.map_loader = MapLoader(self.current_level)

        # Game objects
        self.player = None
        self.enemies = []
        self.collectibles = []
        self.traps = []
        self.doors = []
        self.ladders = []

        # Camera with zoom for dungeon feel (3x zoom)
        self.camera = Camera(
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
            self.map_loader.map_width,
            self.map_loader.map_height,
            zoom=3.0  # 3x zoom for more immersive dungeon atmosphere
        )

        # HUD font
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)

        # Load game objects from map
        self._load_game_objects()
        # After initial load, record starting score and hp
        if self.player:
            self.level_start_score = self.player.score
            self.level_start_hp = self.player.hp

        # Fog of war for visibility effect (initialize AFTER player is loaded)
        self.fog_of_war = FogOfWar(
            self.map_loader.map_width,
            self.map_loader.map_height,
            tile_size=16,
            visibility_radius=96  # Player can see ~8 tiles around them
        )

        # Initialize fog of war with player's starting position
        if self.player:
            self.fog_of_war.update_visibility(self.player.x, self.player.y)

    def _pair_doors(self):
        """Pair up adjacent left/right doors so they open together"""
        for i, door in enumerate(self.doors):
            if door.paired_door:
                continue  # Already paired

            if door.orientation == 'left':
                # Look for adjacent right door
                for j, other_door in enumerate(self.doors):
                    if i != j and other_door.orientation == 'right' and not other_door.paired_door:
                        # Check if they're adjacent (within 20 pixels)
                        distance = ((door.x - other_door.x) ** 2 + (door.y - other_door.y) ** 2) ** 0.5
                        if distance < 20 and door.required_key == other_door.required_key:
                            door.set_paired_door(other_door)
                            other_door.set_paired_door(door)
                            # Determine if it's normal door or final door based on position
                            door_type = "final door" if door.y > 500 else "normal door"
                            print(f"Paired {door_type}s: {door.required_key} at ({door.x},{door.y}) and ({other_door.x},{other_door.y})")
                            break

    def _load_game_objects(self):
        """Load all game objects from the TMX map"""
        # Preserve existing player instance (for score, HP, etc.) across levels
        existing_player = self.player

        # If we are changing level, reset keys (silver/golden) but keep other stats
        if existing_player is not None:
            if hasattr(existing_player, 'inventory'):
                existing_player.inventory['silver'] = 0
                existing_player.inventory['golden'] = 0

        # Clear other objects
        self.enemies = []
        self.collectibles = []
        self.traps = []
        self.doors = []
        self.ladders = []

        objects = self.map_loader.get_objects()

        for obj in objects:
            obj_type = obj.get('obj_type', '')

            if obj_type == 'spawn' and obj.get('obj_name') == 'player_spawn':
                # If we already have a player (changing level), just move them to new spawn
                if existing_player is not None:
                    existing_player.x = obj['x']
                    existing_player.y = obj['y']
                    self.player = existing_player
                else:
                    # First level: create a new player
                    self.player = Player(obj['x'], obj['y'])

            elif obj_type == 'enemy':
                enemy_name = obj.get('obj_name', 'skeleton1')
                enemy = Enemy(obj['x'], obj['y'], enemy_name, self.map_loader.collision_grid)
                self.enemies.append(enemy)

            elif obj_type == 'collectible':
                item_type = obj.get('item', 'coin')
                collectible = Collectible(
                    obj['x'], obj['y'],
                    item_type,
                    obj.get('key_type', ''),
                    obj.get('value', 10),
                    obj.get('heal', 25),
                    obj.get('frames', 4)
                )
                self.collectibles.append(collectible)

            elif obj_type == 'trap':
                trap = Trap(
                    obj['x'], obj['y'],
                    obj.get('obj_name', 'peaks'),
                    obj.get('damage', 25),
                    obj.get('frames', 4),
                    obj.get('frame_duration', 0.15)
                )
                self.traps.append(trap)

            elif obj_type == 'door':
                door = Door(
                    obj['x'], obj['y'],
                    obj.get('required_key', 'silver'),
                    obj.get('count', 1),
                    obj.get('orientation', 'left'),
                    obj.get('gid', 67),  # Get GID from object
                    self.map_loader.tmx_data  # Pass TMX data for tile loading
                )
                self.doors.append(door)

            elif obj_type == 'ladder':
                ladder = Ladder(
                    obj['x'], obj['y'],
                    obj.get('destination', 'level2.tmx'),
                    obj.get('gid', 40),  # Get GID from object
                    self.map_loader.tmx_data  # Pass TMX data for tile loading
                )
                self.ladders.append(ladder)
                print(f"Loaded ladder at ({ladder.x}, {ladder.y}) with GID {ladder.gid}")

        # Pair up left/right doors that are adjacent
        self._pair_doors()


    def handle_event(self, event):
        """Handle input events"""
        if event.type == pygame.KEYDOWN:
            # If victory, handle Victory menu regardless of key
            if self.victory:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.victory_menu_index = (self.victory_menu_index - 1) % len(self.victory_menu_options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.victory_menu_index = (self.victory_menu_index + 1) % len(self.victory_menu_options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    selected = self.victory_menu_options[self.victory_menu_index]
                    if selected == "Main Menu":
                        self.request_exit_to_menu = True
                        # Let main handle music; just leave victory state
                        self.victory = False
                    elif selected == "Quit":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            # If game over, handle Game Over menu regardless of key
            if self.game_over:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.game_over_menu_index = (self.game_over_menu_index - 1) % len(self.game_over_menu_options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.game_over_menu_index = (self.game_over_menu_index + 1) % len(self.game_over_menu_options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    selected = self.game_over_menu_options[self.game_over_menu_index]
                    if selected == "Retry":
                        # Heal player on retry from Game Over
                        self._reload_current_level(heal_player=True)
                        self.game_over = False
                    elif selected == "Quit":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                # Do not process other controls while game over
                return

            if event.key == pygame.K_ESCAPE:
                # Toggle pause
                self.paused = not self.paused
                # Reset menu selection when pausing
                if self.paused:
                    self.pause_menu_index = 0

            # If paused, handle menu navigation instead of game controls
            if self.paused:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.pause_menu_index = (self.pause_menu_index - 1) % len(self.pause_menu_options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.pause_menu_index = (self.pause_menu_index + 1) % len(self.pause_menu_options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    selected = self.pause_menu_options[self.pause_menu_index]
                    if selected == "Resume":
                        self.paused = False
                    elif selected == "Retry":
                        # Restart current level (restore to level start HP and score)
                        self._reload_current_level(heal_player=False)
                        self.paused = False
                    elif selected == "Main Menu":
                        # Signal to app to return to main menu
                        self.request_exit_to_menu = True
                        # Do not stop music; keep it continuous
                        self.paused = False
                    elif selected == "Quit":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                # When paused, don't process other controls
                return

            # CHEAT MODE CONTROLS
            elif event.key == pygame.K_F1:
                # Give silver keys
                if self.player:
                    self.player.inventory['silver'] += 4
                    print("CHEAT: Added 4 silver keys")

            elif event.key == pygame.K_F2:
                # Give golden keys
                if self.player:
                    self.player.inventory['golden'] += 2
                    print("CHEAT: Added 2 golden keys")

            elif event.key == pygame.K_F3:
                # Full health
                if self.player:
                    self.player.hp = self.player.max_hp
                    print("CHEAT: Full health restored")

            elif event.key == pygame.K_F4:
                # Toggle invincibility
                if self.player:
                    self.player.invincible = not self.player.invincible
                    if self.player.invincible:
                        self.player.invincible_duration = 999999  # Basically infinite
                        print("CHEAT: Invincibility ON")
                    else:
                        self.player.invincible_duration = 1.0
                        print("CHEAT: Invincibility OFF")

            elif event.key == pygame.K_F5:
                # Kill all enemies
                if self.player:
                    for enemy in self.enemies:
                        enemy.hp = 0
                    print("CHEAT: All enemies killed")

            elif event.key == pygame.K_F6:
                # Teleport to end (near FinalDoor)
                if self.player:
                    self.player.x = 100
                    self.player.y = 520
                    print("CHEAT: Teleported to exit")

            elif event.key == pygame.K_e:
                # Interact with nearby ladder to change level or finish
                if self.player:
                    for ladder in self.ladders:
                        if ladder.check_collision(self.player):
                            ladder.interact(self.player)
                            # Determine destination
                            dest = ladder.destination
                            if isinstance(dest, str):
                                dest_str = dest.strip().strip('"')
                            else:
                                dest_str = str(dest)
                            # Victory if destination is finish
                            if dest_str.lower() in ("finish", "victory"):
                                self.victory = True
                                self.victory_menu_index = 0
                                return
                            # Otherwise change level normally
                            self._change_level(ladder.destination)
                            break

    def update(self, dt):
        """Update game state"""
        if self.paused or self.game_over or self.victory:
            return

        # Update player
        if self.player:
            keys = pygame.key.get_pressed()

            self.player.update(dt, keys, self.map_loader.collision_grid, self.doors)

            # Update camera to follow player
            self.camera.update(self.player.x, self.player.y)

            # Update fog of war based on player position
            self.fog_of_war.update_visibility(self.player.x, self.player.y)

            # Update map animations (torches, etc.)
            self.map_loader.update_animations(dt)

            # Update and check player collision with collectibles
            for collectible in self.collectibles[:]:
                collectible.update(dt)
                if collectible.check_collision(self.player):
                    # Play pickup SFX based on item
                    if collectible.item_type == 'coin':
                        sound_manager.play('coin', volume=0.4, cooldown=0.05)
                    elif collectible.item_type == 'potion':
                        sound_manager.play('potion', volume=0.5, cooldown=0.1)
                    elif collectible.item_type == 'key':
                        sound_manager.play('potion', volume=0.3, cooldown=0.1)  # reuse subtle chime
                    collectible.collect(self.player)
                    self.collectibles.remove(collectible)

            # Check player collision with traps
            for trap in self.traps:
                trap.update(dt)
                if trap.check_collision(self.player):
                    self.player.take_damage(trap.damage)

            # Update and check player collision with doors
            for door in self.doors:
                door.update(dt)
                # Try to open door if player is near it
                if door.check_collision(self.player):
                    door.try_open(self.player)
                # Door stays in list but won't block movement when is_open = True

            # Update and check player collision with ladders
            for ladder in self.ladders:
                ladder.update(dt)
                if ladder.check_collision(self.player):
                    # Show interaction message
                    ladder.show_message = True
                    ladder.message_timer = 0.1  # Keep showing while near

            # Check if player is dead
            if self.player.hp <= 0:
                sound_manager.play('player_death')
                self.game_over = True

        # Update enemies
        enemies_to_remove = []
        for enemy in self.enemies:
            enemy.update(dt, self.player)

            # Enemy attacks are now handled in enemy.update() when they're in attack range
            # No need to manually call attack on collision

            # Check if player is attacking enemy (use enlarged hitbox; apply damage once per attack)
            if self.player.attacking and not self.player.attack_damage_applied and enemy.check_collision(self.player, for_attack=True) and enemy.hp > 0:
                # Removed per-hit attack SFX; sound now plays at attack start
                enemy.take_damage(self.player.attack_damage)
                self.player.attack_damage_applied = True

            # Mark for removal if death animation is complete
            if enemy.hp <= 0 and enemy.state == 'death':
                death_frames = enemy.animations.get('death', [])
                if death_frames and enemy.frame_index >= len(death_frames) - 1:
                    enemies_to_remove.append(enemy)

        # Remove dead enemies
        for enemy in enemies_to_remove:
            self.enemies.remove(enemy)


    def render(self):
        """Render all game elements"""
        self.screen.fill((0, 0, 0))

        if self.player:
            # Create surface for world rendering with camera
            world_surface = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
            world_surface.fill((20, 15, 25))  # Dark purple background for dungeon atmosphere

            # Render all map layers (Background, Collision for walls, Decorations with animations)
            self.map_loader.render_layer(world_surface, "Background", self.camera)
            self.map_loader.render_layer(world_surface, "Collision", self.camera)
            self.map_loader.render_layer(world_surface, "Decorations", self.camera)


            # Render doors
            for door in self.doors:
                door.render(world_surface, self.camera, paused=self.paused)

            # Render ladders
            for ladder in self.ladders:
                ladder.render(world_surface, self.camera, paused=self.paused)

            # Render collectibles
            for collectible in self.collectibles:
                collectible.render(world_surface, self.camera)

            # Render traps
            for trap in self.traps:
                trap.render(world_surface, self.camera)

            # Render enemies
            for enemy in self.enemies:
                enemy.render(world_surface, self.camera)

            # Render player
            self.player.render(world_surface, self.camera)

            # Apply fog of war
            self.fog_of_war.render(world_surface, self.camera)

            # Draw world surface to screen
            self.screen.blit(world_surface, (0, 0))

            # Render HUD (on top of fog)
            self._render_hud()

        # Render pause/game over/victory screens
        if self.paused:
            self._render_pause_screen()
        elif self.victory:
            self._render_victory_screen()
        elif self.game_over:
            self._render_game_over_screen()

    def _render_hud(self):
        """Render the heads-up display"""
        # HP Bar
        hp_text = self.small_font.render(f"HP: {self.player.hp}/{self.player.max_hp}", True, (255, 255, 255))
        self.screen.blit(hp_text, (10, 10))

        # HP bar background
        hp_bar_width = 200
        hp_bar_height = 20
        pygame.draw.rect(self.screen, (100, 0, 0), (10, 35, hp_bar_width, hp_bar_height))

        # HP bar fill
        hp_ratio = max(0, self.player.hp / self.player.max_hp)
        pygame.draw.rect(self.screen, (0, 200, 0), (10, 35, int(hp_bar_width * hp_ratio), hp_bar_height))

        # HP bar border
        pygame.draw.rect(self.screen, (255, 255, 255), (10, 35, hp_bar_width, hp_bar_height), 2)

        # Score
        score_text = self.small_font.render(f"Score: {self.player.score}", True, (255, 215, 0))
        self.screen.blit(score_text, (10, 65))

        # Keys
        silver_key_text = self.small_font.render(f"Silver Keys: {self.player.inventory.get('silver', 0)}", True, (192, 192, 192))
        self.screen.blit(silver_key_text, (10, 95))

        golden_key_text = self.small_font.render(f"Golden Keys: {self.player.inventory.get('golden', 0)}", True, (255, 215, 0))
        self.screen.blit(golden_key_text, (10, 120))

        # Controls hint
        controls_text = self.small_font.render("WASD/Arrows: Move | SPACE: Attack | ESC: Pause", True, (150, 150, 150))
        self.screen.blit(controls_text, (self.WINDOW_WIDTH - 520, self.WINDOW_HEIGHT - 30))

    def _render_pause_screen(self):
        """Render pause overlay without overlapping text"""
        overlay = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        center_x = self.WINDOW_WIDTH // 2
        center_y = self.WINDOW_HEIGHT // 2

        # Title positioned higher up
        title_text = self.font.render("PAUSED", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(center_x, center_y - 140))
        self.screen.blit(title_text, title_rect)

        # Instruction (non-interactive) placed under title
        instruction_text = self.small_font.render("Press ESC to continue", True, (200, 200, 200))
        instruction_rect = instruction_text.get_rect(center=(center_x, center_y - 100))
        self.screen.blit(instruction_text, instruction_rect)

        # Menu options list (starts below instruction)
        option_start_y = center_y - 40
        spacing = 40  # vertical spacing between options
        for i, option in enumerate(self.pause_menu_options):
            is_selected = (i == self.pause_menu_index)
            color = (255, 255, 0) if is_selected else (220, 220, 220)
            prefix = "> " if is_selected else "  "
            option_text = self.small_font.render(prefix + option, True, color)
            option_rect = option_text.get_rect(center=(center_x, option_start_y + i * spacing))
            self.screen.blit(option_text, option_rect)

        # Navigation hint placed below options
        hint_y = option_start_y + len(self.pause_menu_options) * spacing + 20
        hint_text = self.small_font.render("Use W/S or Up/Down, Enter/Space to select", True, (230, 230, 230))
        hint_rect = hint_text.get_rect(center=(center_x, hint_y))
        self.screen.blit(hint_text, hint_rect)

    def _render_game_over_screen(self):
        """Render game over overlay with Retry/Quit menu"""
        overlay = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((60, 0, 0))
        self.screen.blit(overlay, (0, 0))

        title_text = self.font.render("GAME OVER", True, (255, 80, 80))
        title_rect = title_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 - 80))
        self.screen.blit(title_text, title_rect)

        score_text = self.small_font.render(f"Final Score: {self.player.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(score_text, score_rect)

        # Menu options
        for i, option in enumerate(self.game_over_menu_options):
            is_selected = (i == self.game_over_menu_index)
            color = (255, 255, 0) if is_selected else (220, 220, 220)
            prefix = "> " if is_selected else "  "
            option_text = self.small_font.render(prefix + option, True, color)
            option_rect = option_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 + i * 30))
            self.screen.blit(option_text, option_rect)

        hint_text = self.small_font.render("Use W/S or Up/Down, Enter/Space to select", True, (230, 230, 230))
        hint_rect = hint_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 + 70))
        self.screen.blit(hint_text, hint_rect)

    def _render_victory_screen(self):
        """Render victory overlay with final score and options"""
        overlay = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 60, 0))  # Dark green tone
        self.screen.blit(overlay, (0, 0))

        title_text = self.font.render("VICTORY!", True, (120, 255, 120))
        title_rect = title_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 - 80))
        self.screen.blit(title_text, title_rect)

        score_text = self.small_font.render(f"Final Score: {self.player.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(score_text, score_rect)

        # Menu options
        for i, option in enumerate(self.victory_menu_options):
            is_selected = (i == self.victory_menu_index)
            color = (255, 255, 0) if is_selected else (220, 220, 220)
            prefix = "> " if is_selected else "  "
            option_text = self.small_font.render(prefix + option, True, color)
            option_rect = option_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 + i * 30))
            self.screen.blit(option_text, option_rect)

        hint_text = self.small_font.render("Use W/S or Up/Down, Enter/Space to select", True, (230, 230, 230))
        hint_rect = hint_text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2 + 70))
        self.screen.blit(hint_text, hint_rect)

    def _change_level(self, destination):
        """Change current level to the given TMX destination."""
        # destination from TMX may contain extra quotes like '"level2.tmx"'
        if isinstance(destination, str):
            dest_str = destination.strip().strip('"')
        else:
            dest_str = str(destination)

        # Build relative path from maps folder if not already a path
        if not dest_str.lower().endswith(".tmx"):
            return  # invalid destination

        # If only filename is given, assume maps/ folder
        if "/" not in dest_str and "\\" not in dest_str:
            level_path = f"maps/{dest_str}"
        else:
            level_path = dest_str

        print(f"Changing level to {level_path}")

        # Load new map
        self.current_level = level_path
        self.map_loader = MapLoader(self.current_level)

        # Do not start menu music in-game
        # sound_manager.play_music('music_dungeon', loop=True, volume=0.35)
        # Recreate camera for new map size (keep same zoom)
        self.camera = Camera(
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
            self.map_loader.map_width,
            self.map_loader.map_height,
            zoom=self.camera.zoom
        )

        # Reload objects (this will also create a new player at the new spawn)
        self._load_game_objects()
        # Record score and HP at start of new level (carry over current values)
        if self.player:
            self.level_start_score = self.player.score
            self.level_start_hp = self.player.hp

        # Reset fog of war for new map
        self.fog_of_war = FogOfWar(
            self.map_loader.map_width,
            self.map_loader.map_height,
            tile_size=16,
            visibility_radius=128
        )
        if self.player:
            self.fog_of_war.update_visibility(self.player.x, self.player.y)

    def _reload_current_level(self, heal_player=False):
        """Reload the current level (used by Retry). heal_player=True for Game Over retries."""
        # Reload map loader
        self.map_loader = MapLoader(self.current_level)

        # Recreate camera for current map size (keep same zoom)
        self.camera = Camera(
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
            self.map_loader.map_width,
            self.map_loader.map_height,
            zoom=self.camera.zoom
        )

        # Reset flags
        self.game_over = False
        self.paused = False

        # Reload objects; this will keep player instance but move to spawn and reset keys
        self._load_game_objects()
        if self.player:
            if heal_player:
                # Game over retry: heal to full and set new level_start_hp
                self.player.hp = self.player.max_hp
                self.level_start_hp = self.player.hp
            else:
                # Normal retry: restore HP to level start value
                self.player.hp = min(self.player.max_hp, max(0, self.level_start_hp))
            # Reset score to level start
            self.player.score = self.level_start_score
            # Clear transient combat states
            if hasattr(self.player, 'invincible'):
                self.player.invincible = False
                self.player.invincible_timer = 0
            if hasattr(self.player, 'attacking'):
                self.player.attacking = False
            if hasattr(self.player, 'state'):
                self.player.state = 'idle'
            if hasattr(self.player, 'frame_index'):
                self.player.frame_index = 0
            if hasattr(self.player, 'animation_timer'):
                self.player.animation_timer = 0

        # Reset fog of war for this map
        self.fog_of_war = FogOfWar(
            self.map_loader.map_width,
            self.map_loader.map_height,
            tile_size=16,
            visibility_radius=128
        )
        if self.player:
            self.fog_of_war.update_visibility(self.player.x, self.player.y)
        # Do not start menu music in-game
        # sound_manager.play_music('music_dungeon', loop=True, volume=0.35)
