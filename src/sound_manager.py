import pygame
import os
import time
import numpy as np

class SoundManager:
    """Global sound manager to control master mute/volume and play SFX/music.
    Scans assets/sounds for .wav/.ogg files and exposes them by basename key.
    """
    def __init__(self):
        self.muted = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.aliases: dict[str, str] = {}
        self.last_played: dict[str, float] = {}
        self.default_volume = 0.3
        self._speed_cache: dict[tuple[str, float], str] = {}
        self._current_music_path: str | None = None
        self._current_music_loop: bool = True
        self.sound_paths: dict[str, str] = {}
        self.debug_enabled: bool = False
        self._music_channel_index: int | None = None
        self._music_channel: pygame.mixer.Channel | None = None
        self._using_channel_music: bool = False

    def enable_debug(self, enabled: bool = True):
        self.debug_enabled = bool(enabled)

    def debug_dump(self, resolve_key_name: str | None = None):
        try:
            print("[SND] mixer init:", pygame.mixer.get_init())
        except Exception as e:
            print("[SND] mixer get_init error:", e)
        print("[SND] muted:", self.muted)
        print("[SND] loaded sound keys:", list(self.sounds.keys()))
        print("[SND] sound_paths:", self.sound_paths)
        if resolve_key_name:
            resolved = self.resolve_key(resolve_key_name)
            print(f"[SND] resolve('{resolve_key_name}') ->", resolved)
            print("[SND] sound_paths.get(resolved) ->", self.sound_paths.get(resolved))

    def init_mixer(self):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except Exception:
            # Ignore audio backend errors to keep app running
            pass

    def load_defaults(self, base_path: str = os.path.join('assets', 'sounds')):
        """Load all supported audio files from base_path and register aliases."""
        self.init_mixer()
        if not os.path.isdir(base_path):
            return
        if self.debug_enabled:
            print(f"[SND] Loading sounds from: {base_path}")
        for name in os.listdir(base_path):
            path = os.path.join(base_path, name)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in ('.wav', '.ogg', '.mp3'):
                continue
            key = os.path.splitext(name)[0]
            try:
                snd = pygame.mixer.Sound(path)
                self.sounds[key] = snd
                self.sound_paths[key] = path  # remember exact path
                if self.debug_enabled:
                    print(f"[SND] Loaded: {key} from {path}")
            except Exception as e:
                if self.debug_enabled:
                    print(f"[SND] Failed to load {path}: {e}")
                continue
        # Aliases for friendlier keys
        self.aliases.update({
            'coin': 'coin_sound_effect',
            'potion': 'potion_sound_effect',
            'walk': 'walking_sound_effect',
            'attack': 'player_attack_sound_effect',
            'player_death': 'player_dead_sound_effect',
            'enemy_death': 'skeleton_dead_sound_effect',  # default
            'stage_complete': 'stage_completed_sound_effect',
            'music_dungeon': 'dungeon_theme_sound_effect',
        })
        # Create and map a faster skeleton death variant if source exists
        if 'skeleton_dead_sound_effect' in self.sounds:
            fast_key = 'skeleton_dead_sound_effect_fast'
            if fast_key not in self.sounds:
                try:
                    self._create_sped_up_version('skeleton_dead_sound_effect', fast_key, factor=1.5)
                    self._speed_cache[('skeleton_dead_sound_effect', 1.5)] = fast_key
                except Exception:
                    pass
            # Remap enemy_death alias to the faster variant by default
            if fast_key in self.sounds:
                self.aliases['enemy_death'] = fast_key
        if self.debug_enabled:
            print("[SND] Aliases:", self.aliases)

    def _create_sped_up_version(self, src_key: str, new_key: str, factor: float = 1.5):
        """Create a sped-up version of a loaded sound using numpy resampling."""
        resolved = self.resolve_key(src_key)
        snd = self.sounds.get(resolved)
        if snd is None:
            return False
        # Extract sample array
        arr = pygame.sndarray.array(snd)
        # Handle mono or stereo (shape: (n,) or (n, channels))
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        frames, channels = arr.shape
        new_frames = max(1, int(frames / max(0.01, factor)))
        x_old = np.linspace(0, frames - 1, num=frames)
        x_new = np.linspace(0, frames - 1, num=new_frames)
        new_arr = np.zeros((new_frames, channels), dtype=np.float32)
        for c in range(channels):
            new_arr[:, c] = np.interp(x_new, x_old, arr[:, c].astype(np.float32))
        # Clip to int16 range and cast back
        if arr.dtype == np.int16:
            new_arr = np.clip(new_arr, -32768, 32767).astype(np.int16)
        else:
            # Fallback: normalize to -1..1 float32 if unsupported dtype
            maxv = np.max(np.abs(new_arr)) or 1.0
            new_arr = (new_arr / maxv).astype(np.float32)
        # Restore original shape if mono
        if channels == 1:
            new_arr = new_arr.reshape(-1)
        # Create new Sound
        new_snd = pygame.sndarray.make_sound(new_arr)
        self.sounds[new_key] = new_snd
        return True

    def resolve_key(self, key: str) -> str:
        if key in self.sounds:
            return key
        return self.aliases.get(key, key)

    def toggle_mute(self):
        self.muted = not self.muted
        self.apply()
        return self.muted

    def set_mute(self, mute: bool):
        self.muted = bool(mute)
        self.apply()

    def is_muted(self) -> bool:
        return self.muted

    def apply(self):
        """Apply current mute state to mixer volumes."""
        try:
            if pygame.mixer.get_init() is None:
                return
            volume = 0.0 if self.muted else 1.0
            try:
                pygame.mixer.music.set_volume(volume)
            except Exception:
                pass
            try:
                num_channels = pygame.mixer.get_num_channels()
                for ch_idx in range(num_channels):
                    ch = pygame.mixer.Channel(ch_idx)
                    ch.set_volume(volume)
            except Exception:
                pass
        except Exception:
            pass

    def play(self, key: str, volume: float | None = None, cooldown: float | None = None):
        """Play an SFX by key or alias. Optional per-call volume and cooldown throttle."""
        if self.muted:
            return
        resolved = self.resolve_key(key)
        snd = self.sounds.get(resolved)
        if snd is None:
            return
        if cooldown is not None:
            now = time.time()
            last = self.last_played.get(resolved, 0.0)
            if now - last < cooldown:
                return
            self.last_played[resolved] = now
        try:
            if volume is not None:
                orig = snd.get_volume()
                snd.set_volume(max(0.0, min(1.0, volume)))
                snd.play()
                snd.set_volume(orig)
            else:
                snd.play()
        except Exception:
            pass

    def _get_music_channel(self) -> pygame.mixer.Channel | None:
        try:
            # Ensure we have enough channels; reserve the last one
            total = pygame.mixer.get_num_channels() or 0
            target = max(8, total)
            if total < target:
                pygame.mixer.set_num_channels(target)
            idx = target - 1
            ch = pygame.mixer.Channel(idx)
            self._music_channel_index = idx
            self._music_channel = ch
            if self.debug_enabled:
                print(f"[SND] Using music channel index: {idx}")
            return ch
        except Exception as e:
            if self.debug_enabled:
                print("[SND] Failed to get music channel:", e)
            return None

    def play_music(self, key_or_path: str, loop: bool = True, volume: float | None = None):
        """Play background music from a loaded key or direct path. If the same track is already playing, don't restart it; just update volume."""
        if self.muted:
            return
        try:
            if self.debug_enabled:
                print(f"[SND] play_music called with: {key_or_path}")
            path = key_or_path
            resolved = self.resolve_key(key_or_path)
            if self.debug_enabled:
                print(f"[SND] Resolved key: {resolved}")
            # If it's a loaded sound key, prefer the exact stored path
            if resolved in self.sound_paths:
                path = self.sound_paths[resolved]
                if self.debug_enabled:
                    print(f"[SND] Using stored path: {path}")
            elif not os.path.isabs(path) and resolved in self.sounds:
                # Try to find file on disk by common base folder
                base_path = os.path.join('assets', 'sounds')
                for ext in ('.ogg', '.mp3', '.wav'):
                    candidate = os.path.join(base_path, resolved + ext)
                    if os.path.exists(candidate):
                        path = candidate
                        if self.debug_enabled:
                            print(f"[SND] Found by extension search: {path}")
                        break
            if not os.path.isabs(path):
                # Maybe the caller passed a key; search filesystem
                base_path = os.path.join('assets', 'sounds')
                for ext in ('.ogg', '.mp3', '.wav'):
                    candidate = os.path.join(base_path, key_or_path + ext)
                    if os.path.exists(candidate):
                        path = candidate
                        if self.debug_enabled:
                            print(f"[SND] Found by fallback search: {path}")
                        break

            # Idempotent: if same path already playing
            if self._current_music_path == path:
                if self._using_channel_music:
                    if self._music_channel and self._music_channel.get_busy():
                        if volume is not None:
                            self._music_channel.set_volume(max(0.0, min(1.0, volume)))
                        if self.debug_enabled:
                            print("[SND] Music already playing on channel; volume updated")
                        return
                else:
                    if pygame.mixer.get_init() is not None and pygame.mixer.music.get_busy():
                        if volume is not None:
                            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
                        if self.debug_enabled:
                            print("[SND] Music already playing via mixer.music; volume updated")
                        return

            # Try standard music backend first
            try:
                if self.debug_enabled:
                    print(f"[SND] Loading music via mixer.music: {path}")
                pygame.mixer.music.load(path)
                if volume is not None:
                    pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
                pygame.mixer.music.play(-1 if loop else 0)
                if self.debug_enabled:
                    print(f"[SND] Playing music (loop={loop}) via mixer.music: {path}")
                self._current_music_path = path
                self._current_music_loop = loop
                self._using_channel_music = False
                return
            except Exception as e_music:
                if self.debug_enabled:
                    print(f"[SND] mixer.music failed: {e_music}")
                # Fall through to channel-based playback

            # Channel-based fallback
            snd: pygame.mixer.Sound | None = None
            # If resolved key loaded, reuse it; else try to load as Sound
            snd = self.sounds.get(resolved)
            if snd is None and os.path.exists(path):
                try:
                    snd = pygame.mixer.Sound(path)
                    # Do not store permanently to sounds dict for now
                except Exception as e_snd:
                    if self.debug_enabled:
                        print(f"[SND] Channel fallback failed to load Sound: {e_snd}")
                    return
            ch = self._music_channel or self._get_music_channel()
            if ch is None or snd is None:
                if self.debug_enabled:
                    print("[SND] No music channel or Sound available for fallback")
                return
            # Stop current playback on channel if any
            try:
                ch.stop()
            except Exception:
                pass
            # Set volume and play
            if volume is not None:
                ch.set_volume(max(0.0, min(1.0, volume)))
            ch.play(snd, loops=-1 if loop else 0)
            if self.debug_enabled:
                print(f"[SND] Playing music via Channel fallback (loop={loop}): {path}")
            self._current_music_path = path
            self._current_music_loop = loop
            self._using_channel_music = True
        except Exception as e:
            if self.debug_enabled:
                print(f"[SND] play_music error: {e}")
            pass

    def stop_music(self):
        try:
            if self._using_channel_music and self._music_channel:
                self._music_channel.stop()
            else:
                pygame.mixer.music.stop()
        except Exception:
            pass
        finally:
            self._current_music_path = None
            self._using_channel_music = False

    def set_enemy_death_speed(self, factor: float = 2.0) -> bool:
        """Create or reuse a sped-up skeleton death sound and map enemy_death alias to it.
        Returns True on success, False if source not found or creation failed.
        """
        base_key = 'skeleton_dead_sound_effect'
        if base_key not in self.sounds:
            return False
        cache_key = (base_key, float(factor))
        if cache_key in self._speed_cache:
            self.aliases['enemy_death'] = self._speed_cache[cache_key]
            return True
        # Create a new variant name that encodes factor
        suffix = str(factor).replace('.', 'p')
        new_key = f"{base_key}_fast_{suffix}"
        try:
            ok = self._create_sped_up_version(base_key, new_key, factor=factor)
            if ok is False:
                return False
            self._speed_cache[cache_key] = new_key
            self.aliases['enemy_death'] = new_key
            return True
        except Exception:
            return False

# Singleton-like instance
sound_manager = SoundManager()
