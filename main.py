from ursina import *

from player import Player

from mainmenu import MainMenu

from maps import FloatingIslands, DesertedSands, MountainousValley, ScaledMap, LooseSands

from scene_lighting import SceneLighting
from multiplayer import MultiplayerManager
import tkinter as tk
from keybindings import keybindings

import os
from pathlib import Path
base_dir = os.path.dirname(__file__)
# Use the font filename only; Ursina searches the `assets/` folder for assets by name.
Text.default_font = "Roboto.ttf"
Text.default_resolution = Text.size * 1080

def get_multiplayer_choice():
    """Show a small Tkinter window to choose host/join/solo."""
    choice = {"mode": "solo", "username": "Player", "addr": "127.0.0.1"}
    try:
        root = tk.Tk()
        root.title("Multiplayer")
        root.geometry("320x200")
        tk.Label(root, text="Name").pack()
        name_var = tk.StringVar(value="Player")
        tk.Entry(root, textvariable=name_var).pack()

        mode_var = tk.StringVar(value="solo")
        tk.Radiobutton(root, text="Solo", variable=mode_var, value="solo").pack(anchor="w")
        tk.Radiobutton(root, text="Host", variable=mode_var, value="host").pack(anchor="w")
        tk.Radiobutton(root, text="Join", variable=mode_var, value="join").pack(anchor="w")

        tk.Label(root, text="Server IP").pack()
        ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(root, textvariable=ip_var).pack()

        done = tk.BooleanVar(value=False)

        def submit():
            choice["mode"] = mode_var.get()
            choice["username"] = name_var.get() or "Player"
            choice["addr"] = ip_var.get() or "127.0.0.1"
            done.set(True)

        tk.Button(root, text="Start", command=submit).pack(pady=8)
        root.wait_variable(done)
        root.destroy()
    except Exception as e:
        print("Tkinter prompt failed, defaulting to solo:", e)
    return choice

mp_choice = get_multiplayer_choice()

app = Ursina()
window.fullscreen = True
window.borderless = False
window.cog_button.disable()
window.collider_counter.disable()
window.entity_counter.disable()
window.fps_counter.disable()
window.exit_button.disable()

scene.fog_density = 0.001

# Ensure OBJ files are triangulated to avoid ursina importer issues
import os
from shutil import copy2

def triangulate_obj_file(src_path, dst_path):
    """Read an OBJ file and write a triangulated version to dst_path.
    Faces with more than 3 vertices are split using a fan triangulation.
    """
    with open(src_path, 'r', encoding='utf-8') as f_in, open(dst_path, 'w', encoding='utf-8') as f_out:
        for line in f_in:
            if line.startswith('f '):
                parts = line.strip().split()
                verts = parts[1:]
                if len(verts) <= 3:
                    f_out.write(line)
                else:
                    # fan triangulation: v0, vi, vi+1
                    v0 = verts[0]
                    for i in range(1, len(verts)-1):
                        f_out.write('f ' + v0 + ' ' + verts[i] + ' ' + verts[i+1] + '\n')
            else:
                f_out.write(line)

def triangulate_all_objs(asset_root='assets'):
    # Walk asset folder and triangulate .obj files, backing up originals
    for root, dirs, files in os.walk(asset_root):
        for fname in files:
            if fname.lower().endswith('.obj'):
                full = os.path.join(root, fname)
                bak = full + '.bak'
                tri = full  # overwrite original after backing up

                try:
                    if not os.path.exists(bak):
                        copy2(full, bak)
                        print(f'Backed up OBJ: {full} -> {bak}')

                    # write to a temp file then replace
                    tmp = full + '.tmp'
                    triangulate_obj_file(bak, tmp)
                    os.replace(tmp, tri)
                    print(f'Triangulated OBJ: {full}')
                except Exception as e:
                    print(f'Failed triangulating {full}:', e)

# Run triangulation once at startup
triangulate_all_objs(asset_root=os.path.join(base_dir, 'assets'))

def load_assets():
    models_to_load = [
        "floatingislands", "desertedsands", "mountainous_valley", "jumppad", "particle", "particles", "enemy", "bigenemy", "pistol",
        "shotgun", "rifle", "minigun", "minigun-barrel", "rocket-launcher", "rocket", "bullet", "Male_Casual",
        "map-scaled",
        "loose-sands", # Add the new map model
    ]

    textures_to_load = [
        "level", "particle", "destroyed", "jetpack", "sky", "rope", "hit"
    ]

    sounds_to_load = [
        "fall", "rope", "dash", "pistol", "destroyed", "shotgun", "rifle", "minigun", "rocket_launcher"
    ]

    for i, m in enumerate(models_to_load):
        load_model(m)

    for i, t in enumerate(textures_to_load):
        load_texture(t)

    for i, s in enumerate(sounds_to_load):
        # Pre-load sounds by creating Audio objects
        Audio(s, autoplay=False)

# Load all assets on the main thread; Panda3D's loader isn't thread-safe
load_assets()

player = Player((-60, 50, -16)) # Flat: (-47, 50, -94) # Rope: (-61, 100, 0)
player.disable()

floating_islands = FloatingIslands(player, enabled = True)
deserted_sands = DesertedSands(player, enabled = False)
mountainous_valley = MountainousValley(player, enabled = False)
scaled_map = ScaledMap(player, enabled = False)
loose_sands = LooseSands(player, enabled = False)

player.map = floating_islands
player.maps = [floating_islands, deserted_sands, mountainous_valley, scaled_map, loose_sands]

multiplayer = MultiplayerManager(player)

if mp_choice["mode"] == "host":
    multiplayer.host_game(mp_choice["username"])
elif mp_choice["mode"] == "join":
    multiplayer.connect(mp_choice["addr"], mp_choice["username"])
 
mainmenu = MainMenu(player, floating_islands, deserted_sands, mountainous_valley, scaled_map, loose_sands)

# Lighting + Shadows
scene_lighting = SceneLighting(ursina = app, player = player, sun_direction = (-0.7, -0.9, 0.5), shadow_resolution = 4096, sky_texture = "sky")

def input(key):
    if key == keybindings.get_key("reset"):
        player.reset()

def update():
    multiplayer.update()

app.run()
