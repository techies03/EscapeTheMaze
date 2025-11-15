import pygame
import pytmx
import os

# Flip mask constants for pytmx tile GIDs
FLIPPED_HORIZONTALLY_FLAG = 0x80000000
FLIPPED_VERTICALLY_FLAG   = 0x40000000
FLIPPED_DIAGONALLY_FLAG   = 0x20000000
FLIP_MASK = FLIPPED_HORIZONTALLY_FLAG | FLIPPED_VERTICALLY_FLAG | FLIPPED_DIAGONALLY_FLAG

class MapLoader:
    """Loads and manages TMX map data"""

    def __init__(self, tmx_file):
        # Load TMX file
        self.tmx_data = pytmx.load_pygame(tmx_file)

        # Map dimensions
        self.map_width = self.tmx_data.width * self.tmx_data.tilewidth
        self.map_height = self.tmx_data.height * self.tmx_data.tileheight

        # Create collision grid from Collision layer
        self.collision_grid = self._create_collision_grid()

        # Load animated tiles (torches, etc.) - each GID tracks its own state
        self.animated_tiles = {}
        self._load_animated_tiles()

        # Debug: Verify animations are set up correctly (comment out if not needed)
        # self.debug_tile_at(13, 3, "Decorations")

    def _create_collision_grid(self):
        """Create a 2D grid for collision detection"""
        collision_layer = None
        for layer in self.tmx_data.layers:
            if hasattr(layer, 'name') and layer.name == "Collision":
                collision_layer = layer
                break

        if not collision_layer:
            return [[False] * self.tmx_data.width for _ in range(self.tmx_data.height)]

        grid = []
        for y in range(self.tmx_data.height):
            row = []
            for x in range(self.tmx_data.width):
                tile = collision_layer.data[y][x]
                # Non-zero tiles are solid (especially tile 79 which is the border)
                row.append(tile != 0)
            grid.append(row)

        return grid

    def _load_animated_tiles(self):
        """Load animated tile frames for specific GIDs"""
        base_path = "assets/2D Pixel Dungeon Asset Pack/items and trap_animation/torch"

        # Map GID -> animation data with frames, timer, and current frame per GID
        # IMPORTANT: Use the actual GIDs that pytmx returns (35, 36, 42) not the raw TMX values
        # Based on debug scan: 36=torch, 35=sidetorch, 42=candlestick
        self.animated_tiles = {
            36: {"frames": [], "frame_duration": 0.15, "timer": 0.0, "current_frame": 0},  # torch
            35: {"frames": [], "frame_duration": 0.15, "timer": 0.0, "current_frame": 0},  # sidetorch
            42: {"frames": [], "frame_duration": 0.15, "timer": 0.0, "current_frame": 0}   # candlestick
        }

        # Load torch frames (torch_1.png to torch_4.png) → GID 36
        for i in range(1, 5):
            filepath = os.path.join(base_path, f"torch_{i}.png")
            if os.path.exists(filepath):
                frame = pygame.image.load(filepath).convert_alpha()
                self.animated_tiles[36]["frames"].append(frame)

        # Load side_torch frames (side_torch_1.png to side_torch_4.png) → GID 35
        for i in range(1, 5):
            filepath = os.path.join(base_path, f"side_torch_{i}.png")
            if os.path.exists(filepath):
                frame = pygame.image.load(filepath).convert_alpha()
                self.animated_tiles[35]["frames"].append(frame)

        # Load candlestick frames (candlestick_2_1.png to candlestick_2_4.png) → GID 42
        for i in range(1, 5):
            filepath = os.path.join(base_path, f"candlestick_2_{i}.png")
            if os.path.exists(filepath):
                frame = pygame.image.load(filepath).convert_alpha()
                self.animated_tiles[42]["frames"].append(frame)

        torch_frames = len(self.animated_tiles[36]['frames'])
        side_frames = len(self.animated_tiles[35]['frames'])
        candle_frames = len(self.animated_tiles[42]['frames'])

        print(f"Loaded animated tiles:")
        print(f"  GID 36 (torch): {torch_frames} frames")
        print(f"  GID 35 (sidetorch): {side_frames} frames")
        print(f"  GID 42 (candlestick): {candle_frames} frames")

        if torch_frames == 0 or side_frames == 0 or candle_frames == 0:
            print("WARNING: Some animation frames failed to load! Check file paths.")

    def debug_tile_at(self, map_x, map_y, layer_name="Decorations"):
        """Debug function to check raw/masked GIDs at a specific tile location"""
        for l in self.tmx_data.layers:
            if hasattr(l, "name") and l.name == layer_name:
                raw = l.data[map_y][map_x]
                masked = raw & ~FLIP_MASK
                print(f"\nLayer {layer_name} tile at ({map_x},{map_y}):")
                print(f"  raw_gid={raw}, masked_gid={masked}")
                print(f"  animated_tiles has raw_gid? {raw in self.animated_tiles}")
                print(f"  animated_tiles has masked_gid? {masked in self.animated_tiles}")
                if masked in self.animated_tiles:
                    anim = self.animated_tiles[masked]
                    print(f"  Animation: {len(anim['frames'])} frames loaded")
                return
        print(f"Layer {layer_name} not found.")

    def get_objects(self):
        """Get all objects from the object layers"""
        objects = []

        for layer in self.tmx_data.layers:
            if isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    obj_data = {
                        'x': obj.x,
                        'y': obj.y,
                        'width': obj.width,
                        'height': obj.height,
                        'name': obj.name,
                        'type': obj.type,
                    }

                    # Add GID if object has a tile image
                    if hasattr(obj, 'gid'):
                        obj_data['gid'] = obj.gid


                    # Add properties
                    if hasattr(obj, 'properties'):
                        obj_data.update(obj.properties)

                    objects.append(obj_data)

        return objects

    def update_animations(self, dt):
        """Update animation frame for each animated tile GID independently"""
        for gid, anim_data in self.animated_tiles.items():
            if anim_data["frames"]:
                anim_data["timer"] += dt

                if anim_data["timer"] >= anim_data["frame_duration"]:
                    anim_data["timer"] = 0.0
                    num_frames = len(anim_data["frames"])
                    anim_data["current_frame"] = (anim_data["current_frame"] + 1) % num_frames



    def render_layer(self, surface, layer_name, camera):
        """Render a specific tile layer"""
        layer = None
        for l in self.tmx_data.layers:
            if hasattr(l, 'name') and l.name == layer_name:
                layer = l
                break

        if not layer or not hasattr(layer, 'data'):
            return

        # Calculate visible tile range
        start_x = max(0, int(camera.x / self.tmx_data.tilewidth) - 1)
        end_x = min(self.tmx_data.width, int((camera.x + camera.width / camera.zoom) / self.tmx_data.tilewidth) + 2)
        start_y = max(0, int(camera.y / self.tmx_data.tileheight) - 1)
        end_y = min(self.tmx_data.height, int((camera.y + camera.height / camera.zoom) / self.tmx_data.tileheight) + 2)

        # Render visible tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                raw_gid = layer.data[y][x]
                if raw_gid:
                    # Strip flip bits to get base GID
                    gid = raw_gid & ~FLIP_MASK

                    # Determine flip flags from raw_gid (Tiled flags)
                    flip_h = bool(raw_gid & FLIPPED_HORIZONTALLY_FLAG)
                    flip_v = bool(raw_gid & FLIPPED_VERTICALLY_FLAG)
                    flip_d = bool(raw_gid & FLIPPED_DIAGONALLY_FLAG)

                    tile_image = None

                    # Check if this is an animated tile (try masked gid first, then raw)
                    if gid in self.animated_tiles and self.animated_tiles[gid]["frames"]:
                        # Render animated frame using this GID's current frame
                        anim_data = self.animated_tiles[gid]
                        frames = anim_data["frames"]
                        current_frame = anim_data["current_frame"]
                        tile_image = frames[current_frame % len(frames)]
                    elif raw_gid in self.animated_tiles and self.animated_tiles[raw_gid]["frames"]:
                        # Try with raw GID if masked didn't work
                        anim_data = self.animated_tiles[raw_gid]
                        frames = anim_data["frames"]
                        current_frame = anim_data["current_frame"]
                        tile_image = frames[current_frame % len(frames)]
                    else:
                        # Render static tile (pytmx returns image already flipped)
                        tile_image = self.tmx_data.get_tile_image_by_gid(raw_gid)

                    if tile_image is None:
                        continue

                    # For animated tiles, we need to apply flips manually to match Tiled placement
                    if (gid in self.animated_tiles or raw_gid in self.animated_tiles):
                        try:
                            # Apply diagonal flip as a 90-degree rotation approximation if present
                            if flip_d:
                                # Tiled diagonal flip is a transpose; a 90 deg rotation approximates it for most orthogonal cases
                                tile_image = pygame.transform.rotate(tile_image, -90)
                                # After rotation, a horizontal flip becomes vertical and vice versa; swap flags
                                flip_h, flip_v = flip_v, flip_h
                            if flip_h or flip_v:
                                tile_image = pygame.transform.flip(tile_image, flip_h, flip_v)
                        except Exception:
                            # If any transform fails, fall back to unflipped frame
                            pass

                    # Calculate world position
                    world_x = x * self.tmx_data.tilewidth
                    world_y = y * self.tmx_data.tileheight

                    # Apply camera transformation
                    screen_x, screen_y, tile_w, tile_h = camera.apply(
                        world_x, world_y,
                        self.tmx_data.tilewidth,
                        self.tmx_data.tileheight
                    )

                    # Scale tile image if zoomed
                    if camera.zoom != 1.0:
                        scaled_image = pygame.transform.scale(
                            tile_image,
                            (int(tile_w), int(tile_h))
                        )
                        surface.blit(scaled_image, (int(screen_x), int(screen_y)))
                    else:
                        surface.blit(tile_image, (int(screen_x), int(screen_y)))

    def is_collision(self, x, y, width, height):
        """Check if a rectangle collides with solid tiles"""
        # Convert world coordinates to tile coordinates
        start_tile_x = max(0, int(x / self.tmx_data.tilewidth))
        end_tile_x = min(self.tmx_data.width - 1, int((x + width) / self.tmx_data.tilewidth))
        start_tile_y = max(0, int(y / self.tmx_data.tileheight))
        end_tile_y = min(self.tmx_data.height - 1, int((y + height) / self.tmx_data.tileheight))

        # Check if any tile in the range is solid
        for tile_y in range(start_tile_y, end_tile_y + 1):
            for tile_x in range(start_tile_x, end_tile_x + 1):
                if self.collision_grid[tile_y][tile_x]:
                    return True

        return False
