from ursina import *
from ursina import curve
from keybindings import keybindings

colourH = color.rgba(0, 0, 0, 0.3)
colourN = color.rgba(0, 0, 0, 0.7)
highlighted = lambda button: button.color == colourH

class MainMenu(Entity):
    def __init__(self, player, floating_islands, deserted_sands, mountainous_valley, scaled_map, loose_sands):
        super().__init__(
            parent = camera.ui
        )

        # Player
        self.player = player

        # Maps
        self.floating_islands = floating_islands
        self.deserted_sands = deserted_sands
        self.mountainous_valley = mountainous_valley
        self.scaled_map = scaled_map
        self.loose_sands = loose_sands

        # Menus
        self.mainmenu = Entity(parent = self, enabled = False)
        self.end_screen = Entity(parent = self, enabled = False)
        self.pause_menu = Entity(parent = self, enabled = False)
        self.maps_menu = Entity(parent = self, enabled = False)
        self.settings_menu = Entity(parent = self, enabled = False)

        self.menus = [self.mainmenu, self.pause_menu, self.maps_menu, self.settings_menu]
        self.index = 0

        self.enable_end_screen = True
        self.waiting_for_key = False

        # Animate the Menus
        for menu in self.menus:
            def animate_in_menu(menu = menu):
                for i, e in enumerate(menu.children):
                    e.original_scale = e.scale
                    e.scale -= 0.01
                    e.animate_scale(e.original_scale, delay = i * 0.05, duration = 0.1, curve = curve.out_quad)

                    e.alpha = 0
                    e.animate("alpha", 0.7, delay = i * 0.05, duration = 0.1, curve = curve.out_quad)

                    if hasattr(e, "text_entity"):
                        e.text_entity.alpha = 0
                        e.text_entity.animate("alpha", 1, delay = i * 0.05, duration = 0.1)

            if menu != self.pause_menu:
                menu.on_enable = animate_in_menu

        self.mainmenu.enable()

        # Main Menu
        self.start_button = Button(text = "Start", color = colourH, highlight_color = colourH, scale_y = 0.1, scale_x = 0.3, y = 0.05, parent = self.mainmenu)
        self.maps_button = Button(text = "Maps", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = -0.07, parent = self.mainmenu)
        self.quit_button = Button(text = "Quit", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = -0.19, parent = self.mainmenu)

        invoke(setattr, self.start_button, "color", colourH, delay = 0.5)

        # Endscreen
        retry_text = Text("Retry", scale = 4, origin = (0, 0.5), x = 0, y = 0.1, z = -100, parent = self.end_screen)
        press_enter = Text("Press Enter", scale = 2, origin = (0, 0.5), x = 0, y = 0, z = -100, parent = self.end_screen)
        self.highscore_text = Text(text = str(self.player.highscore), origin = (0, 0), size = 0.05, scale = (0.8, 0.8), position = window.top - (0, 0.1), parent = self.end_screen, z = -100)
        camera.overlay.parent = self.end_screen
        camera.overlay.color = color.rgba(220, 0, 0, 100)

        # Pause Menu
        self.resume_button = Button(text = "Resume", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = 0.17, parent = self.pause_menu)
        self.retry_button = Button(text = "Retry", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = 0.05, parent = self.pause_menu)
        self.settings_button = Button(text = "Settings", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = -0.07, parent = self.pause_menu)
        self.mainmenu_button = Button(text = "Main Menu", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = -0.19, parent = self.pause_menu)
        self.pause_overlay = Entity(parent = self.pause_menu, model = "quad", scale = 99, color = color.rgba(20, 20, 20, 100), eternal = True, z = 10)

        # Maps Menu
        self.floating_islands_button = Button(text = "Floating Islands", color = colourN, highlighted_color = colourH, scale_y = 0.1, scale_x = 0.3, y = 0.05, parent = self.maps_menu)
        self.deserted_sands_button = Button(text = "Deserted Sands", color = colourN, highlighted_color = colourH, scale_y = 0.1, scale_x = 0.3, y = -0.07, parent = self.maps_menu)
        self.mountainous_valley_button = Button(text = "Mountainous Valley", color = colourN, highlighted_color = colourH, scale_y = 0.1, scale_x = 0.3, y = -0.19, parent = self.maps_menu)
        self.scaled_map_button = Button(text = "Scaled Map", color = colourN, highlighted_color = colourH, scale_y = 0.1, scale_x = 0.3, y = -0.31, parent = self.maps_menu)
        self.loose_sands_button = Button(text = "Loose Sands", color = colourN, highlighted_color = colourH, scale_y = 0.1, scale_x = 0.3, y = -0.43, parent = self.maps_menu)

        # Settings Menu
        self.settings_title = Text("Settings", parent = self.settings_menu, y = 0.4, origin = (0,0), scale = 2)
        self.keybind_buttons = {}
        
        y = 0.3
        for action, key in keybindings.keybinds.items():
            b = Button(
                parent=self.settings_menu,
                text=f"{action}: {key}",
                scale_y=0.05,
                scale_x=0.4,
                y=y,
                color = colourN, 
                highlight_color = colourN
            )
            b.on_click = Func(self.change_key, action)
            self.keybind_buttons[action] = b
            y -= 0.06

        self.back_button = Button(text = "Back", color = colourN, highlight_color = colourN, scale_y = 0.1, scale_x = 0.3, y = y, parent = self.settings_menu)
    
    def change_key(self, action):
        if self.waiting_for_key:
            return

        self.waiting_for_key = True
        self.action_to_change = action
        self.keybind_buttons[action].text = f"{action}: Press any key..."

    def update(self):
        if self.player.health <= 0:
            if self.enable_end_screen:
                self.end_screen.enable()
                self.enable_end_screen = False
                self.player.check_highscore()
                application.time_scale = 0.2
                self.player.dead = True
                self.highscore_text.text = "Highscore: " + str(self.player.highscore)

        if held_keys["enter"] and not self.enable_end_screen:
            self.player.reset()
            self.end_screen.disable()
            self.enable_end_screen = True
            
    def input(self, key):
        if self.waiting_for_key and key not in ["enter", "up arrow", "down arrow", "left mouse down", "right mouse down"]:
            keybindings.set_key(self.action_to_change, key)
            self.waiting_for_key = False
            self.refresh_settings_menu()
            return

        if self.settings_menu.enabled and not self.waiting_for_key:
            if key == "up arrow":
                self.index -= 1
                if self.index < 0:
                    self.index = len(self.settings_menu.children) - 1
            elif key == "down arrow":
                self.index += 1
                if self.index >= len(self.settings_menu.children):
                    self.index = 0
            
            for i, c in enumerate(self.settings_menu.children):
                if isinstance(c, Button):
                    if i == self.index:
                        c.color = colourH
                        c.highlight_color = colourH
                    else:
                        c.color = colourN
                        c.highlight_color = colourN
        elif not self.settings_menu.enabled:
            # Improved navigation for menus with mixed children (buttons and non-buttons)
            if key == "up arrow":
                for menu in self.menus:
                    if menu.enabled:
                        buttons_in_menu = [c for c in menu.children if isinstance(c, Button)]
                        if not buttons_in_menu:
                            continue

                        current_highlighted_index_in_buttons = -1
                        for i, btn in enumerate(buttons_in_menu):
                            if highlighted(btn):
                                current_highlighted_index_in_buttons = i
                                break

                        if current_highlighted_index_in_buttons == -1:
                            new_highlight_index_in_buttons = len(buttons_in_menu) - 1
                        else:
                            new_highlight_index_in_buttons = (current_highlighted_index_in_buttons - 1 + len(buttons_in_menu)) % len(buttons_in_menu)

                        for i, btn in enumerate(buttons_in_menu):
                            if i == new_highlight_index_in_buttons:
                                btn.color = colourH
                                btn.highlight_color = colourH
                            else:
                                btn.color = colourN
                                btn.highlight_color = colourN
                        self.index = menu.children.index(buttons_in_menu[new_highlight_index_in_buttons])
            elif key == "down arrow":
                for menu in self.menus:
                    if menu.enabled:
                        buttons_in_menu = [c for c in menu.children if isinstance(c, Button)]
                        if not buttons_in_menu:
                            continue

                        current_highlighted_index_in_buttons = -1
                        for i, btn in enumerate(buttons_in_menu):
                            if highlighted(btn):
                                current_highlighted_index_in_buttons = i
                                break

                        if current_highlighted_index_in_buttons == -1:
                            new_highlight_index_in_buttons = 0
                        else:
                            new_highlight_index_in_buttons = (current_highlighted_index_in_buttons + 1) % len(buttons_in_menu)

                        for i, btn in enumerate(buttons_in_menu):
                            if i == new_highlight_index_in_buttons:
                                btn.color = colourH
                                btn.highlight_color = colourH
                            else:
                                btn.color = colourN
                                btn.highlight_color = colourN
                        self.index = menu.children.index(buttons_in_menu[new_highlight_index_in_buttons])
        if key == "enter":
            if self.waiting_for_key:
                return
            # Main Menu
            if self.mainmenu.enabled:
                if highlighted(self.start_button):
                    self.start()
                elif highlighted(self.maps_button):
                    self.maps_menu.enable()
                    self.mainmenu.disable()
                    self.update_menu(self.maps_menu)
                elif highlighted(self.quit_button):
                    application.quit()

            # Pause Menu
            elif self.pause_menu.enabled:
                if highlighted(self.resume_button):
                    self.pause(False, False)
                elif highlighted(self.retry_button):
                    self.player.reset()
                    self.pause_menu.disable()
                elif highlighted(self.settings_button):
                    self.settings_menu.enable()
                    self.pause_menu.disable()
                    self.update_menu(self.settings_menu)
                    application.time_scale = 1
                elif highlighted(self.mainmenu_button):
                    self.player.disable()
                    self.player.reset()
                    for enemy in self.player.enemies:
                        enemy.disable()
                    self.mainmenu.enable()
                    self.pause_menu.disable()
                    self.update_menu(self.pause_menu)

            # Settings menu
            elif self.settings_menu.enabled:
                if highlighted(self.back_button):
                    self.pause_menu.enable()
                    self.settings_menu.disable()
                    self.update_menu(self.pause_menu)
                    application.time_scale = 0.1
                else:
                    for action, button in self.keybind_buttons.items():
                        if highlighted(button):
                            self.change_key(action)
                            break

            # Maps menu
            elif self.maps_menu.enabled:
                if highlighted(self.floating_islands_button):
                    for map in self.player.maps:
                        map.disable()
                    self.floating_islands.enable()
                    self.player.map = self.floating_islands
                    self.start()
                if highlighted(self.deserted_sands_button):
                    for map in self.player.maps:
                        map.disable()
                    self.deserted_sands.enable()
                    self.player.map = self.deserted_sands
                    self.start()
                if highlighted(self.mountainous_valley_button):
                    for map in self.player.maps:
                        map.disable()
                    self.mountainous_valley.enable()
                    self.player.map = self.mountainous_valley
                    self.player.position = (-5, 200, -10)
                    self.start() 
                if highlighted(self.scaled_map_button):
                    for map in self.player.maps:
                        map.disable()
                    self.scaled_map.enable()
                    self.player.map = self.scaled_map
                    self.player.position = (0, 10, 0) # Placeholder spawn position for the new map
                    self.start()
                if highlighted(self.loose_sands_button):
                    for map in self.player.maps:
                        map.disable()
                    self.loose_sands.enable()
                    self.player.map = self.loose_sands
                    self.player.position = (0, 10, 0) # Placeholder spawn position for the new map
                    self.start()

            # End Screen
            if self.player.health <= 0:
                self.end_screen.disable()
                self.enable_end_screen = True
                self.player.reset()
        if key == "escape":
            if self.maps_menu.enabled:
                self.maps_menu.disable()
                self.mainmenu.enable()
            elif self.settings_menu.enabled:
                self.settings_menu.disable()
                self.pause_menu.enable()
                application.time_scale = 0.1
            # Pause Menu
            elif self.player.enabled:
                self.pause()
                self.update_menu(self.pause_menu)

    def start(self):
        self.mainmenu.disable()
        self.maps_menu.disable()
        for enemy in self.player.enemies:
            enemy.enable()
        self.player.enable()

    def pause(self, opposite = True, pause = True):
        if opposite:
            self.pause_menu.enabled = not self.pause_menu.enabled
            if self.pause_menu.enabled:
                application.time_scale = 0.1
            else:
                application.time_scale = 1
        else:
            if pause:
                self.pause_menu.enable()
                application.time_scale = 0.1
            else:
                self.pause_menu.disable()
                application.time_scale = 1

    def update_menu(self, menu):
        for i, c in enumerate(menu.children):
            if isinstance(c, Button):
                c.color = colourN
                c.highlight_color = colourN
        
        # Find the first button to highlight
        for i, c in enumerate(menu.children):
            if isinstance(c, Button):
                c.color = colourH
                c.highlight_color = colourH
                self.index = i
                break
    
    def refresh_settings_menu(self):
        for action, button in self.keybind_buttons.items():
            button.text = f"{action}: {keybindings.get_key(action)}"
        self.update_menu(self.settings_menu)
