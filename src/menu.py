import pygame
from typing import List, Callable

from sound_manager import sound_manager

class MenuOption:
    def __init__(self, label: str, action: Callable[[], None]):
        self.label = label
        self.action = action

class BaseMenu:
    def __init__(self, screen: pygame.Surface, title: str, options: List['MenuOption'], background: pygame.Surface | None = None):
        self.screen = screen
        self.title = title
        self.options = options
        self.index = 0
        self.font_title = pygame.font.Font(None, 56)
        self.font_option = pygame.font.Font(None, 36)
        self.font_hint = pygame.font.Font(None, 24)
        # Background handling
        self._background_raw: pygame.Surface | None = None
        self._background_prepared: pygame.Surface | None = None
        if background is not None:
            self.set_background(background)

    def set_background(self, surface: pygame.Surface | None):
        self._background_raw = surface.copy() if surface is not None else None
        self._background_prepared = None  # Reset so it will be rebuilt

    def _prepare_background(self):
        if self._background_raw is None:
            self._background_prepared = None
            return
        width, height = self.screen.get_size()
        # Scale raw to screen size if needed
        bg = pygame.transform.smoothscale(self._background_raw, (width, height))
        # Fast blur by downscaling then upscaling
        small_w = max(1, width // 8)
        small_h = max(1, height // 8)
        small = pygame.transform.smoothscale(bg, (small_w, small_h))
        blurred = pygame.transform.smoothscale(small, (width, height))
        # Darken overlay
        overlay = pygame.Surface((width, height), flags=pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))  # semi-transparent black
        blurred.blit(overlay, (0, 0))
        self._background_prepared = blurred

    def _render_gradient_fallback(self):
        width, height = self.screen.get_size()
        # Brighter vertical gradient background
        top = (30, 30, 45)
        bottom = (10, 10, 20)
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top[0] * (1 - t) + bottom[0] * t)
            g = int(top[1] * (1 - t) + bottom[1] * t)
            b = int(top[2] * (1 - t) + bottom[2] * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (width, y))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if 0 <= self.index < len(self.options):
                    self.options[self.index].action()

    def render(self):
        width, height = self.screen.get_size()
        # Background
        if self._background_raw is not None and self._background_prepared is None:
            self._prepare_background()
        if self._background_prepared is not None:
            self.screen.blit(self._background_prepared, (0, 0))
        else:
            self._render_gradient_fallback()

        # Title
        title_surf = self.font_title.render(self.title, True, (255, 255, 255))
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height // 2 - 180)))
        # Options
        start_y = height // 2 - 60
        spacing = 44
        for i, opt in enumerate(self.options):
            selected = (i == self.index)
            color = (255, 215, 0) if selected else (220, 220, 220)
            prefix = '> ' if selected else '  '
            surf = self.font_option.render(prefix + opt.label, True, color)
            self.screen.blit(surf, surf.get_rect(center=(width // 2, start_y + i * spacing)))
        # Hints
        hint = self.font_hint.render('Use W/S or Up/Down, Enter/Space to select', True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(width // 2, height - 40)))

class MainMenu(BaseMenu):
    def __init__(self, screen: pygame.Surface, on_start_level: Callable[[str], None], on_open_level_select: Callable[[], None], on_open_instructions: Callable[[], None], on_quit: Callable[[], None], background: pygame.Surface | None = None):
        self.on_start_level = on_start_level
        self.on_open_level_select = on_open_level_select
        self.on_open_instructions = on_open_instructions
        self.on_quit = on_quit
        super().__init__(screen, 'Escape The Maze', [
            MenuOption('Start Game (Level 1)', lambda: self.on_start_level('maps/level1.tmx')),
            MenuOption('Level Select', self.on_open_level_select),
            MenuOption('Instructions', self.on_open_instructions),
            MenuOption('Mute: ' + ('ON' if sound_manager.is_muted() else 'OFF'), self._toggle_mute),
            MenuOption('Quit', self.on_quit),
        ], background=background)

    def _toggle_mute(self):
        sound_manager.toggle_mute()
        # Update the label text for the mute option
        for i, opt in enumerate(self.options):
            if opt.label.startswith('Mute:'):
                self.options[i] = MenuOption('Mute: ' + ('ON' if sound_manager.is_muted() else 'OFF'), self._toggle_mute)
                break

class LevelSelectMenu(BaseMenu):
    def __init__(self, screen: pygame.Surface, levels: List[str], on_select: Callable[[str], None], on_back: Callable[[], None], background: pygame.Surface | None = None):
        self.levels = levels
        self.on_select = on_select
        self.on_back = on_back
        opts = [MenuOption(level, lambda l=level: self.on_select(l)) for level in levels]
        opts.append(MenuOption('Back', self.on_back))
        super().__init__(screen, 'Select Level', opts, background=background)

class InstructionsMenu(BaseMenu):
    def __init__(self, screen: pygame.Surface, on_back: Callable[[], None], background: pygame.Surface | None = None):
        self.on_back = on_back
        # Keep a single option for consistent BaseMenu handling
        super().__init__(screen, 'Instructions', [
            MenuOption('Back', self.on_back),
        ], background=background)
        # Predefined, already-wrapped instruction lines
        self._lines = [
            'Goal: Find the exit ladder and escape the maze.',
            'Avoid enemies or defeat them when needed.',
            '',
            'Controls:',
            '- Move: W/A/S/D or Arrow Keys',
            '- Attack: Space',
            '- Interact / Use: E',
            '- Pause / Exit to Menu: Esc',
            '',
            'Tips:',
            '- Watch your health. Use potions when you find them.',
            '- Coins are for score—pick them up!',
            '- Some traps are subtle. Move carefully.',
            '- Sound cues can warn you about threats.',
        ]
        self._text_font = pygame.font.Font(None, 28)

    def handle_event(self, event: pygame.event.Event):
        # Support BaseMenu navigation and also quick back with ESC/BACKSPACE
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.on_back()
            return
        super().handle_event(event)

    def render(self):
        # Render background and title via BaseMenu, but suppress option list first
        width, height = self.screen.get_size()
        if self._background_raw is not None and self._background_prepared is None:
            self._prepare_background()
        if self._background_prepared is not None:
            self.screen.blit(self._background_prepared, (0, 0))
        else:
            self._render_gradient_fallback()

        # Title
        title_surf = self.font_title.render(self.title, True, (255, 255, 255))
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, 80)))

        # Instruction text block
        x_margin = 120
        y_start = 150
        line_h = 30
        for i, line in enumerate(self._lines):
            color = (230, 230, 230) if not line.endswith(':') else (255, 215, 0)
            surf = self._text_font.render(line, True, color)
            self.screen.blit(surf, (x_margin, y_start + i * line_h))

        # Back option at bottom for consistency
        back_text = 'Press Esc to go Back or select: Back'
        hint_surf = self.font_hint.render(back_text, True, (200, 200, 200))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(width // 2, height - 60)))

        # Draw the single Back option centered (optional)
        opt = self.options[0]
        surf = self.font_option.render('> ' + opt.label, True, (255, 215, 0))
        self.screen.blit(surf, surf.get_rect(center=(width // 2, height - 100)))
