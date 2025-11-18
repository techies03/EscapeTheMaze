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
        # animated_tiles: canonical_gid -> animation data
        self.animated_tiles = {}
        # animated_aliases: alias_gid -> canonical_gid (used when different maps use different GIDs)
        # NOTE: This dictionary is instance-specific and cleared for each new map load
        self.animated_aliases = {}
        self._load_animated_tiles()

        # Level-specific GIDs to skip rendering (useful for removing specific decorations per level)
        # Configure which GIDs should NOT be rendered in the Decorations layer for specific levels
        skip_rendering_config = {
            'maps/level2.tmx': {36, 35, 42},  # Don't render torch/sidetorch/candlestick tiles in level 2
            'maps\\level2.tmx': {36, 35, 42},  # Windows path variant
        }

        # Determine which GIDs to skip for this level
        self.skip_gids = set()
        map_filename = os.path.basename(self.tmx_data.filename) if hasattr(self.tmx_data, 'filename') else None
        if map_filename:
            for config_path, gids in skip_rendering_config.items():
                if config_path.endswith(map_filename) or map_filename in config_path:
                    self.skip_gids = gids
                    print(f"Skipping GIDs {gids} in Decorations layer for {map_filename}")
                    break

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
        """Load animated tile frames for specific GIDs based on level configuration"""
        base_path = "assets/2D Pixel Dungeon Asset Pack/items and trap_animation/torch"

        # Level-specific configuration: which GIDs should be animated per level
        # This prevents the same GID from being incorrectly animated in different levels
        # where it might represent different decorations
        level_animation_config = {
            'maps/level1.tmx': {36, 35, 42},  # torch, sidetorch, candlestick
            'maps\\level1.tmx': {36, 35, 42},  # Windows path variant
            'maps/level2.tmx': set(),          # no animations in level 2
            'maps\\level2.tmx': set(),         # Windows path variant
        }

        # Determine which GIDs should be animated for this specific map
        map_filename = os.path.basename(self.tmx_data.filename) if hasattr(self.tmx_data, 'filename') else None

        # Try to match the level config - check both with and without 'maps/' prefix
        allowed_gids = None
        for config_path, gids in level_animation_config.items():
            if map_filename and (config_path.endswith(map_filename) or map_filename in config_path):
                allowed_gids = gids
                break

        # If no specific config found, find decorations layer and collect used GIDs
        # Then allow all defined animation GIDs that are present (backward compatibility)
        if allowed_gids is None:
            decorations_layer = None
            for layer in self.tmx_data.layers:
                if hasattr(layer, 'name') and layer.name == 'Decorations':
                    decorations_layer = layer
                    break

            used_gids = set()
            if decorations_layer:
                for y in range(self.tmx_data.height):
                    for x in range(self.tmx_data.width):
                        raw = decorations_layer.data[y][x]
                        if raw:
                            masked = raw & ~FLIP_MASK
                            used_gids.add(masked)

            # Default to all animation GIDs that are used in decorations
            allowed_gids = used_gids & {36, 35, 42}

        # Define potential animations with their expected GIDs
        animation_definitions = {
            36: {'name': 'torch', 'pattern': 'torch_{}.png'},
            35: {'name': 'sidetorch', 'pattern': 'side_torch_{}.png'},
            42: {'name': 'candlestick', 'pattern': 'candlestick_2_{}.png'}
        }

        # Only load animations for GIDs that are allowed for this level
        for gid, anim_def in animation_definitions.items():
            if gid not in allowed_gids:
                # Skip loading animation for GIDs not configured for this map
                continue

            frames = []
            pattern = anim_def['pattern']
            for i in range(1, 5):
                filename = pattern.format(i)
                filepath = os.path.join(base_path, filename)
                if os.path.exists(filepath):
                    frame = pygame.image.load(filepath).convert_alpha()
                    frames.append(frame)

            if frames:
                self.animated_tiles[gid] = {
                    "frames": frames,
                    "frame_duration": 0.15,
                    "timer": 0.0,
                    "current_frame": 0
                }
                print(f"Loaded animation for GID {gid} ({anim_def['name']}): {len(frames)} frames")

        # After loading animations, try to automatically alias any other GIDs used in this map's
        # Decorations layer to the canonical animation GIDs by comparing tile images.
        # NOTE: This is disabled by default to prevent cross-level animation bleeding
        # self._auto_alias_animated_gids()

    def _surfaces_equal(self, a, b):
        """Return True if two pygame surfaces have identical pixel data and size."""
        if a is None or b is None:
            return False
        if a.get_size() != b.get_size():
            return False
        try:
            # Use RGBA string compare which is reliable for identical images
            return pygame.image.tostring(a, 'RGBA') == pygame.image.tostring(b, 'RGBA')
        except Exception:
            # Fallback to pixel-by-pixel compare (slower)
            w, h = a.get_size()
            for x in range(w):
                for y in range(h):
                    if a.get_at((x, y)) != b.get_at((x, y)):
                        return False
            return True

    def _auto_alias_animated_gids(self):
        """Scan the Decorations layer for tile GIDs whose tile images match known animation frames
        and automatically register alias mappings so animations appear regardless of GID offsets
        between maps/tilesets.
        """
        # Build reference first-frame images for each canonical animation (if available)
        refs = {}
        for canonical_gid, anim in list(self.animated_tiles.items()):
            frames = anim.get('frames', [])
            if frames:
                refs[canonical_gid] = frames[0]

        if not refs:
            return

        # Find decorations layer
        decorations_layer = None
        for layer in self.tmx_data.layers:
            if hasattr(layer, 'name') and layer.name == 'Decorations':
                decorations_layer = layer
                break

        if not decorations_layer:
            return

        # Collect unique masked GIDs used in this layer
        used_masked_gids = set()
        for y in range(self.tmx_data.height):
            for x in range(self.tmx_data.width):
                raw = decorations_layer.data[y][x]
                if raw:
                    masked = raw & ~FLIP_MASK
                    used_masked_gids.add(masked)

        # For each used gid not already a canonical animation, compare its tile image
        for gid in used_masked_gids:
            if gid in self.animated_tiles or gid in self.animated_aliases:
                continue
            tile_img = self.tmx_data.get_tile_image_by_gid(gid)
            if tile_img is None:
                continue
            # Compare to each reference
            for canonical_gid, ref_img in refs.items():
                try:
                    if self._surfaces_equal(tile_img, ref_img):
                        self.add_animated_gid_alias(canonical_gid, gid)
                        print(f"Auto-aliased animation: alias {gid} -> canonical {canonical_gid}")
                        break
                except Exception:
                    continue

    def add_animated_gid_alias(self, source_gid: int, alias_gid: int):
        """Alias an already-loaded animation (source_gid) to another gid (alias_gid).

        This registers alias_gid to be treated as source_gid during rendering and animation updates.
        It does not duplicate animation data (avoids double-updating timers).
        """
        if source_gid in self.animated_tiles and alias_gid not in self.animated_tiles and alias_gid not in self.animated_aliases:
            self.animated_aliases[alias_gid] = source_gid
            print(f"Added animated GID alias: {alias_gid} -> {source_gid}")

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
                print(f"  animated_aliases contains masked_gid? {masked in self.animated_aliases}")
                if masked in self.animated_tiles:
                    anim = self.animated_tiles[masked]
                    print(f"  Animation: {len(anim['frames'])} frames loaded")
                elif masked in self.animated_aliases:
                    canon = self.animated_aliases[masked]
                    anim = self.animated_tiles.get(canon)
                    print(f"  Animation (via alias to {canon}): {len(anim['frames']) if anim else 0} frames loaded")
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
        # Only update canonical animation entries (avoid double-updating if aliases exist)
        for gid, anim_data in list(self.animated_tiles.items()):
            if anim_data["frames"]:
                anim_data["timer"] += dt

                if anim_data["timer"] >= anim_data["frame_duration"]:
                    anim_data["timer"] = 0.0
                    num_frames = len(anim_data["frames"])
                    anim_data["current_frame"] = (anim_data["current_frame"] + 1) % num_frames


    def _get_animation_for_gid(self, gid):
        """Resolve gid to canonical animation data if present (considering aliases).
        Returns (canonical_gid, anim_data) or (None, None).
        """
        if gid in self.animated_tiles:
            return gid, self.animated_tiles[gid]
        if gid in self.animated_aliases:
            canon = self.animated_aliases[gid]
            return canon, self.animated_tiles.get(canon)
        return None, None

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

                    # Skip rendering specific GIDs in Decorations layer if configured
                    if layer_name == "Decorations" and gid in self.skip_gids:
                        continue

                    # Determine flip flags from raw_gid (Tiled flags)
                    flip_h = bool(raw_gid & FLIPPED_HORIZONTALLY_FLAG)
                    flip_v = bool(raw_gid & FLIPPED_VERTICALLY_FLAG)
                    flip_d = bool(raw_gid & FLIPPED_DIAGONALLY_FLAG)

                    tile_image = None

                    # Resolve animation using canonical gid (consider aliases)
                    canon_gid, anim_data = self._get_animation_for_gid(gid)
                    if anim_data and anim_data["frames"]:
                        frames = anim_data["frames"]
                        current_frame = anim_data["current_frame"]
                        tile_image = frames[current_frame % len(frames)]
                    else:
                        # Try raw_gid as fallback (some maps may store different bits)
                        canon_gid2, anim_data2 = self._get_animation_for_gid(raw_gid)
                        if anim_data2 and anim_data2["frames"]:
                            frames = anim_data2["frames"]
                            current_frame = anim_data2["current_frame"]
                            tile_image = frames[current_frame % len(frames)]
                        else:
                            # Render static tile (pytmx returns image already flipped)
                            tile_image = self.tmx_data.get_tile_image_by_gid(raw_gid)

                    if tile_image is None:
                        continue

                    # For animated tiles, we need to apply flips manually to match Tiled placement
                    if (canon_gid is not None) or (raw_gid in self.animated_aliases) or (raw_gid in self.animated_tiles):
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
