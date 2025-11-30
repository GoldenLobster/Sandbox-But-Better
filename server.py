"""
Server script for hosting games.
"""

import json
import random
import socket
import threading
import time

ADDR = "0.0.0.0"
PORT = 8000
MAX_PLAYERS = 10
MSG_SIZE = 2048

# Setup server socket (initialized in main)
s: socket.socket | None = None
players = {}


def generate_id(player_list: dict, max_players: int):
    """Generate a unique identifier."""
    while True:
        unique_id = str(random.randint(1, max_players))
        if unique_id not in player_list:
            return unique_id


def handle_messages(identifier: str):
    client_info = players[identifier]
    conn: socket.socket = client_info["socket"]
    username = client_info["username"]
    recv_buffer = ""

    while True:
        try:
            msg = conn.recv(MSG_SIZE)
        except ConnectionResetError:
            break

        if not msg:
            break

        recv_buffer += msg.decode("utf8")

        while True:
            try:
                start = recv_buffer.index("{")
                end = recv_buffer.index("}", start) + 1
            except ValueError:
                break

            chunk = recv_buffer[start:end]
            recv_buffer = recv_buffer[end:]

            try:
                msg_json = json.loads(chunk)
            except Exception as e:
                print(e)
                continue

            if msg_json.get("object") == "damage":
                for player_id, player_info in list(players.items()):
                    player_conn: socket.socket = player_info["socket"]
                    try:
                        player_conn.send(json.dumps(msg_json).encode("utf8"))
                    except OSError:
                        pass
                continue
            if msg_json.get("object") == "projectile":
                for player_id, player_info in list(players.items()):
                    player_conn: socket.socket = player_info["socket"]
                    try:
                        player_conn.send(json.dumps(msg_json).encode("utf8"))
                    except OSError:
                        pass
                continue
            if msg_json.get("object") == "particle":
                for player_id, player_info in list(players.items()):
                    player_conn: socket.socket = player_info["socket"]
                    try:
                        player_conn.send(json.dumps(msg_json).encode("utf8"))
                    except OSError:
                        pass
                continue

            if msg_json.get("object") == "player":
                players[identifier]["position"] = msg_json.get("position")
                players[identifier]["rotation"] = msg_json.get("rotation")
                players[identifier]["health"] = msg_json.get("health")
                players[identifier]["gun"] = msg_json.get("gun", players[identifier].get("gun", 0))

            # Tell other players about player moving
            for player_id in list(players.keys()):
                if player_id != identifier:
                    player_info = players[player_id]
                    player_conn: socket.socket = player_info["socket"]
                    try:
                        player_conn.sendall(chunk.encode("utf8"))
                    except OSError:
                        pass

    # Tell other players about player leaving
    for player_id in list(players.keys()):
        if player_id != identifier:
            player_info = players[player_id]
            player_conn: socket.socket = player_info["socket"]
            try:
                player_conn.send(
                    json.dumps(
                        {
                            "id": identifier,
                            "object": "player",
                            "joined": False,
                            "left": True,
                        }
                    ).encode("utf8")
                )
            except OSError:
                pass

    print(f"Player {username} with ID {identifier} has left the game...")
    del players[identifier]
    conn.close()


def main():
    global s
    if s is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((ADDR, PORT))
        s.listen(MAX_PLAYERS)

    print("Server started, listening for new connections...")

    while True:
        # Accept new connection and assign unique ID
        conn, addr = s.accept()
        new_id = generate_id(players, MAX_PLAYERS)
        conn.send(new_id.encode("utf8"))
        username = conn.recv(MSG_SIZE).decode("utf8")
        new_player_info = {
            "socket": conn,
            "username": username,
            "position": (0, 1, 0),
            "rotation": 0,
            "health": 100,
            "gun": 0,
        }

        # Tell existing players about new player
        for player_id in list(players.keys()):
            if player_id != new_id:
                player_info = players[player_id]
                player_conn: socket.socket = player_info["socket"]
                try:
                    player_conn.send(
                        json.dumps(
                            {
                                "id": new_id,
                                "object": "player",
                                "username": new_player_info["username"],
                                "position": new_player_info["position"],
                                "health": new_player_info["health"],
                                "gun": new_player_info["gun"],
                                "joined": True,
                                "left": False,
                            }
                        ).encode("utf8")
                    )
                except OSError:
                    pass

        # Tell new player about existing players
        for player_id in list(players.keys()):
            if player_id != new_id:
                player_info = players[player_id]
                try:
                    conn.send(
                        json.dumps(
                            {
                                "id": player_id,
                                "object": "player",
                                "username": player_info["username"],
                                "position": player_info["position"],
                                "health": player_info["health"],
                                "gun": player_info.get("gun", 0),
                                "joined": True,
                                "left": False,
                            }
                        ).encode("utf8")
                    )
                    time.sleep(0.1)
                except OSError:
                    pass

        # Add new player to players list
        players[new_id] = new_player_info

        # Start thread to receive messages from client
        msg_thread = threading.Thread(target=handle_messages, args=(new_id,), daemon=True)
        msg_thread.start()

        print(f"New connection from {addr}, assigned ID: {new_id}...")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if s:
            s.close()
