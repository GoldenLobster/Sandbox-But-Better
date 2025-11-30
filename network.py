import json
import socket
from typing import Optional


class Network:
    """
    Minimal client for exchanging player state with the server.
    """

    def __init__(self, server_addr: str, server_port: int, username: str):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = server_addr
        self.port = server_port
        self.username = username
        self.recv_size = 2048
        self.id: Optional[str] = None
        self._recv_buffer = ""

    def settimeout(self, value: float) -> None:
        self.client.settimeout(value)

    def connect(self) -> None:
        """Connect to the server and get a unique identifier."""
        self.client.connect((self.addr, self.port))
        self.id = self.client.recv(self.recv_size).decode("utf8")
        self.client.send(self.username.encode("utf8"))

    def receive_info(self):
        """Non-blocking receive. Returns a parsed JSON dict, list of dicts, or None."""
        try:
            msg = self.client.recv(self.recv_size)
        except (socket.timeout, BlockingIOError):
            return None
        except socket.error as e:
            print("network receive error:", e)
            return None

        if not msg:
            return None

        self._recv_buffer += msg.decode("utf8")
        messages = []

        while True:
            try:
                start = self._recv_buffer.index("{")
                end = self._recv_buffer.index("}", start) + 1
            except ValueError:
                break

            chunk = self._recv_buffer[start:end]
            self._recv_buffer = self._recv_buffer[end:]
            try:
                messages.append(json.loads(chunk))
            except Exception as e:
                print("network json error:", e)
                continue

        if not messages:
            return None
        if len(messages) == 1:
            return messages[0]
        return messages

    def send_player(self, player):
        """Send the local player's transform/health."""
        if self.id is None:
            return
        player_info = {
            "object": "player",
            "id": self.id,
            "position": (player.world_x, player.world_y, player.world_z),
            "rotation": player.rotation_y,
            "health": getattr(player, "health", 0),
            "gun": getattr(player, "current_gun", 0),
            "joined": False,
            "left": False,
        }
        self._send_payload(player_info)

    def send_damage(self, target_id: str, amount: float, headshot: bool = False) -> None:
        """Tell the server a player took damage."""
        if self.id is None:
            return
        payload = {
            "object": "damage",
            "id": self.id,
            "target": target_id,
            "amount": amount,
            "headshot": False,
        }
        self._send_payload(payload)

    def send_projectile(self, position, rotation, kind: str = "bullet", direction=None) -> None:
        """Broadcast a projectile so other clients can render a tracer."""
        if self.id is None:
            return
        payload = {
            "object": "projectile",
            "id": self.id,
            "position": position,
            "rotation": rotation,
            "kind": kind,
        }
        if direction is not None:
            payload["direction"] = direction
        self._send_payload(payload)

    def send_particles(self, position, direction=(0, 0, 0), spray_amount: float = 30, model: str = "particles", texture: str | None = None) -> None:
        """Broadcast a particle effect so other clients can see it."""
        if self.id is None:
            return
        payload = {
            "object": "particle",
            "id": self.id,
            "position": position,
            "direction": direction,
            "spray": spray_amount,
            "model": model,
            "texture": texture,
        }
        self._send_payload(payload)

    def _send_payload(self, payload: dict) -> None:
        try:
            self.client.send(json.dumps(payload).encode("utf8"))
        except socket.error as e:
            print("network send error:", e)
