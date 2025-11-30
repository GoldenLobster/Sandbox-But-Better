import threading
from typing import Dict, Optional

from ursina import Entity, Vec3, color, curve, invoke, time, destroy

import server
from network import Network
from particles import Particles


class RemotePlayer(Entity):
    def __init__(self, player_id: str, position=(0, 1, 0), rotation_y=0):
        super().__init__(model=None, position=position, rotation_y=rotation_y)
        # Rendered model is a child so we can offset it down to rest on the ground.
        self.gfx = Entity(
            parent=self,
            model="Male_Casual",
            scale=1.32,  # 10% larger than default 1.2 scale
            color=color.white,
            y=-1.07,  # aligns with local player's 1.4m waist height so feet touch ground
        )
        self.gun_prop = Entity(parent=self.gfx, texture="level.png")
        self.gun_index = 0
        self._set_gun_prop(0)
        self._spawn_scale = self.gfx.scale
        self.id = player_id
        self.is_remote_player = True
        self.health = 10
        self.dead = False

        # Hitboxes for hitscan
        self.body_hitbox = Entity(
            parent=self,
            collider="box",
            scale=(3.0, 6.5, 1.5),  # doubled height to cover the full player vertically
            y=2.1,                  # keep base near feet while extending higher
            visible=False,
        )
        self.body_hitbox.owner = self
        self.body_hitbox.damage_multiplier = 1
        self.head_hitbox = Entity(
            parent=self,
            collider="box",
            scale=(1.0, 1.0, 1.0),  # simple box head hitbox
            y=3.5,
            visible=False,
        )
        self.head_hitbox.owner = self
        self.head_hitbox.damage_multiplier = 1  # no headshot bonus
        self.head_hitbox.is_headshot = False

    def _set_gun_prop(self, gun_index: int):
        """Update the remote player's visible gun based on index."""
        gun_index = int(gun_index)
        gun_models = {
            0: {"model": "rifle.obj", "scale": 0.2, "pos": (0.5, 2, 0.2), "rot": (0, 0, 0)},
            1: {"model": "shotgun.obj", "scale": 0.2, "pos": (0.5, 2, 0.2), "rot": (0, 0, 0)},
            2: {"model": "pistol.obj", "scale": 0.2, "pos": (0.5, 2, 0.2), "rot": (0, 0, 0)},
            3: {"model": "minigun.obj", "scale": 0.1, "pos": (0.5, 2, 0.2), "rot": (0, 0, 0)},
            4: {"model": "rocket-launcher.obj", "scale": 0.15, "pos": (0.5, 2, 0.2), "rot": (0, 0, 0)},
        }
        data = gun_models.get(gun_index, gun_models[0])
        self.gun_prop.model = data["model"]
        self.gun_prop.scale = data["scale"]
        self.gun_prop.position = data["pos"]
        self.gun_prop.rotation = data["rot"]
        self.gun_index = gun_index

    def die(self):
        if self.dead:
            return
        self.dead = True
        # Disable hitboxes so additional shots don't interact mid-animation
        self.body_hitbox.disable()
        self.head_hitbox.disable()
        self.gun_prop.visible = False
        # Simple collapse/fade animation, then hide the entity; keep it around to allow respawn
        self.gfx.animate_scale((0, 0, 0), duration=0.3, curve=curve.in_expo)
        self.gfx.animate_color(color.clear, duration=0.3, curve=curve.linear)
        invoke(setattr, self.gfx, "visible", False, delay=0.32)

    def respawn(self):
        """Bring the remote player back after death."""
        self.dead = False
        self.gfx.visible = True
        self.gfx.color = color.white
        self.gfx.scale = self._spawn_scale
        self.gun_prop.visible = True
        self.body_hitbox.enable()
        self.head_hitbox.enable()
        self.enable()


class RemoteProjectile(Entity):
    def __init__(self, position, rotation, kind="bullet"):
        super().__init__(
            model="bullet.obj" if kind == "bullet" else "rocket.obj",
            texture="level.png",
            scale=0.08 if kind == "bullet" else 0.2,
            position=position,
            rotation=rotation,
        )
        # Match local projectile speeds: bullets ~2000, rockets ~600 (per in-game animation)
        self.speed = 2000 if kind == "bullet" else 600
        trail_color = color.azure if kind == "bullet" else color.orange
        self.trail = Entity(model="cube", scale=(0.02, 0.02, 0.3), color=trail_color, parent=self)
        destroy(self, delay=2)

    def update(self):
        self.position += self.forward * self.speed * time.dt


class MultiplayerManager:
    def __init__(self, player):
        self.player = player
        self.player.multiplayer = self
        self.network: Optional[Network] = None
        self.remote_players: Dict[str, RemotePlayer] = {}
        self.server_thread: Optional[threading.Thread] = None
        self.connected = False
        self.port = 8000

    # Server hosting -----------------------------------------------------
    def host_game(self, username: str):
        if self.server_thread is None or not self.server_thread.is_alive():
            self.server_thread = threading.Thread(target=server.main, daemon=True)
            self.server_thread.start()
            print("Started local server on port 8000")
        self.connect("127.0.0.1", username)

    # Client -------------------------------------------------------------
    def connect(self, addr: str, username: str):
        try:
            net = Network(addr, self.port, username)
            net.settimeout(0.001)
            net.connect()
            self.network = net
            self.connected = True
            print(f"Connected to server as id {self.network.id}")
        except Exception as e:
            print("Failed to connect:", e)
            self.network = None
            self.connected = False

    def update(self):
        if not self.connected or not self.network:
            return

        # Send local state
        self.network.send_player(self.player)

        # Drain incoming messages
        while True:
            msg = self.network.receive_info()
            if not msg:
                break
            if isinstance(msg, list):
                for m in msg:
                    self._handle_message(m)
            else:
                self._handle_message(msg)

    # Message handling ---------------------------------------------------
    def _handle_message(self, msg: dict):
        if msg.get("object") == "damage":
            self._apply_damage_message(msg)
            return
        if msg.get("object") == "projectile":
            # Don't render our own projectiles; local client already sees them
            if self.network and str(msg.get("id")) == str(self.network.id):
                return
            self._spawn_remote_projectile(msg)
            return
        if msg.get("object") == "particle":
            if self.network and str(msg.get("id")) == str(self.network.id):
                return
            self._spawn_remote_particles(msg)
            return

        if msg.get("object") != "player":
            return

        player_id = str(msg.get("id"))
        if self.network and player_id == str(self.network.id):
            return

        if msg.get("left"):
            self._remove_remote_player(player_id)
            return

        if msg.get("joined"):
            if player_id not in self.remote_players:
                self._spawn_remote_player(player_id, msg)
            return

        # Regular position update
        rp = self.remote_players.get(player_id)
        if rp:
            pos = msg.get("position", (rp.x, rp.y, rp.z))
            rp.position = Vec3(*pos)
            rp.rotation_y = msg.get("rotation", rp.rotation_y)
            rp.health = msg.get("health", getattr(rp, "health", 100))
            rp._set_gun_prop(msg.get("gun", rp.gun_index))
            if rp.health <= 0 and not rp.dead:
                rp.die()
            elif rp.dead and rp.health > 0:
                rp.respawn()

    def _spawn_remote_player(self, player_id: str, msg: dict):
        pos = msg.get("position", (0, 1, 0))
        rot = msg.get("rotation", 0)
        rp = RemotePlayer(player_id, position=Vec3(*pos), rotation_y=rot)
        rp._set_gun_prop(msg.get("gun", 0))
        self.remote_players[player_id] = rp
        print(f"Spawned remote player {player_id}")

    def _spawn_remote_projectile(self, msg: dict):
        pos = msg.get("position", (0, 1, 0))
        rot = msg.get("rotation", (0, 0, 0))
        kind = msg.get("kind", "bullet")
        direction = msg.get("direction")
        owner_id = str(msg.get("id"))
        spawn_pos = Vec3(*pos)

        proj = RemoteProjectile(position=spawn_pos, rotation=rot, kind=kind)
        if direction:
            dir_vec = Vec3(*direction)
            if dir_vec.length() > 0:
                proj.look_at(proj.position + dir_vec)

    def _remove_remote_player(self, player_id: str):
        rp = self.remote_players.pop(player_id, None)
        if rp:
            rp.disable()
            rp.remove_node()
            print(f"Removed remote player {player_id}")

    def send_damage(self, target_id: str, amount: float, headshot: bool = False):
        if self.network and self.connected:
            self.network.send_damage(target_id, amount, headshot=headshot)

    def send_projectile(self, position, rotation, kind="bullet", direction=None):
        """Relay a fired projectile to other clients."""
        if self.network and self.connected:
            self.network.send_projectile(position, rotation, kind=kind, direction=direction)

    def send_particles(self, position, direction=(0, 0, 0), spray_amount: float = 30, model: str = "particles", texture: str | None = None):
        """Broadcast a particle effect so other clients can render it."""
        if self.network and self.connected:
            self.network.send_particles(position, direction, spray_amount, model=model, texture=texture)

    def _apply_damage_message(self, msg: dict):
        target_id = str(msg.get("target"))
        amount = float(msg.get("amount", 0))
        is_headshot = bool(msg.get("headshot"))

        # Local player hit
        if self.network and target_id == str(self.network.id):
            self.player.health -= amount
            self.player.healthbar.value = self.player.health
            if self.player.health <= 0:
                self.player.dead = True
            return

        # Remote representation hit (to show damage locally)
        rp = self.remote_players.get(target_id)
        if rp:
            rp.health = max(0, getattr(rp, "health", 10) - amount)
            if rp.health <= 0:
                rp.die()
            elif rp.dead and rp.health > 0:
                rp.respawn()
            return

    def _spawn_remote_particles(self, msg: dict):
        pos = msg.get("position", (0, 0, 0))
        direction = msg.get("direction", (0, 0, 0))
        spray = msg.get("spray", 30)
        model = msg.get("model", "particles")
        texture = msg.get("texture", None)
        Particles(position=Vec3(*pos), direction=Vec3(*direction), spray_amount=spray, model=model, texture=texture)
