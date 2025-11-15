import pygame
import sys
import os
from game import Game
from menu import MainMenu, LevelSelectMenu
from sound_manager import sound_manager

LEVELS = [
    'maps/level1.tmx',
    'maps/level2.tmx',
]


def main():
    """Main entry point for the game with menu system"""
    pygame.init()

    # Initialize sound system and load sounds
    # sound_manager.enable_debug(True)  # Debug disabled for normal runs
    sound_manager.load_defaults()
    # sound_manager.debug_dump('music_dungeon')  # Debug disabled
    # Make enemy death sound faster (2.0x); fallback gracefully
    try:
        sound_manager.set_enemy_death_speed(2.0)
    except Exception:
        pass
    # Play menu music (menu-only)
    sound_manager.play_music('music_dungeon', loop=True, volume=0.3)

    # Create a single window/screen reused across menus and game
    window_size = (960, 720)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Escape The Maze")

    clock = pygame.time.Clock()
    running = True

    # App states: 'menu', 'level_select', 'game'
    state = 'menu'
    game: Game | None = None

    # Background surface for menus (captured from gameplay or static image)
    menu_background: pygame.Surface | None = None

    # Try to load a default menu background image if available
    def load_static_menu_bg() -> pygame.Surface | None:
        try:
            path = os.path.join('assets', 'menu_bg.png')
            if os.path.exists(path):
                img = pygame.image.load(path).convert()
                return img
        except Exception:
            pass
        return None

    menu_background = load_static_menu_bg()

    def rebuild_menus():
        nonlocal main_menu, level_select_menu
        # Ensure menu music is playing when menus are rebuilt
        sound_manager.play_music('music_dungeon', loop=True, volume=0.5)
        main_menu = MainMenu(screen, start_level, open_level_select, quit_app, background=menu_background)
        level_select_menu = LevelSelectMenu(screen, LEVELS, start_level, lambda: switch_state('menu'), background=menu_background)

    # Callback handlers for menu actions
    def start_level(level_path: str):
        nonlocal state, game
        # Stop menu music on entering game
        try:
            sound_manager.stop_music()
        except Exception:
            pass
        game = Game(initial_level=level_path, screen=screen)
        state = 'game'

    def open_level_select():
        nonlocal state
        state = 'level_select'

    def quit_app():
        nonlocal running
        running = False

    def switch_state(new_state: str):
        nonlocal state
        state = new_state

    # Create menu instances initially (with static background if any)
    main_menu = MainMenu(screen, start_level, open_level_select, quit_app, background=menu_background)
    level_select_menu = LevelSelectMenu(screen, LEVELS, start_level, lambda: switch_state('menu'), background=menu_background)

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if state == 'game' and game is not None:
                game.handle_event(event)
            elif state == 'menu' and main_menu is not None:
                main_menu.handle_event(event)
            elif state == 'level_select' and level_select_menu is not None:
                level_select_menu.handle_event(event)

        if not running:
            break

        if state == 'game' and game is not None:
            game.update(dt)
            # If the game requests exit to menu (via pause option), capture background and go back
            if game.request_exit_to_menu:
                try:
                    # Capture last rendered frame as background
                    menu_background = screen.copy()
                except Exception:
                    if menu_background is None:
                        menu_background = load_static_menu_bg()
                game = None
                # Ensure menu music resumes when returning to menu
                sound_manager.play_music('music_dungeon', loop=True, volume=0.5)
                rebuild_menus()
                state = 'menu'
        else:
            # Menus don't have update logic right now
            pass

        # Render current state
        if state == 'game' and game is not None:
            game.render()
        elif state == 'menu' and main_menu is not None:
            main_menu.render()
        elif state == 'level_select' and level_select_menu is not None:
            level_select_menu.render()

        pygame.display.flip()

    pygame.quit()
    try:
        sound_manager.stop_music()
    except Exception:
        pass
    sys.exit()


if __name__ == "__main__":
    main()
