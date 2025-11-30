import json
import os

class Keybindings:
    def __init__(self, path="keybinds.json"):
        self.path = path
        self.keybinds = {}
        self.default_keybinds = {
            "forward": "w",
            "left": "a",
            "right": "d",
            "back": "s",
            "jump": "space",
            "slide": "left shift",
            "gun_1": "1",
            "gun_2": "2",
            "gun_3": "3",
            "gun_4": "4",
            "gun_5": "5",
            "next_gun": "scroll up",
            "prev_gun": "scroll down",
            "reset": "g"
        }
        self.load_keybinds()

    def load_keybinds(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.keybinds = json.load(f)
        else:
            self.keybinds = self.default_keybinds
            self.save_keybinds()

    def save_keybinds(self):
        with open(self.path, "w") as f:
            json.dump(self.keybinds, f, indent=4)

    def get_key(self, action):
        return self.keybinds.get(action, self.default_keybinds.get(action))

    def set_key(self, action, key):
        self.keybinds[action] = key
        self.save_keybinds()

keybindings = Keybindings()
