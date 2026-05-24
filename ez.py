import socket
import threading
import json
import uuid

HOST = "0.0.0.0"
PORT = 5555

players = {}
players_lock = threading.Lock()

connections = {}
connections_lock = threading.Lock()


def broadcast_state():
    with players_lock:
        state = json.dumps(players) + "\n"

    dead = []
    with connections_lock:
        for pid, conn in connections.items():
            try:
                conn.sendall(state.encode())
            except Exception:
                dead.append(pid)

    for pid in dead:
        remove_player(pid)


def broadcast_message(msg):
    """Envoie un message arbitraire à tous les joueurs connectés."""
    dead = []
    with connections_lock:
        for pid, conn in connections.items():
            try:
                conn.sendall((json.dumps(msg) + "\n").encode())
            except Exception:
                dead.append(pid)
    for pid in dead:
        remove_player(pid)


def send_to_player(player_id, msg):
    """Envoie un message à un joueur spécifique."""
    with connections_lock:
        conn = connections.get(player_id)
    if conn:
        try:
            conn.sendall((json.dumps(msg) + "\n").encode())
            print(f"[SERVER] Dégâts relayés vers {player_id}")
        except Exception as e:
            print(f"[SERVER] Erreur envoi dégâts à {player_id} : {e}")
    else:
        print(f"[SERVER] Cible {player_id} introuvable")


def remove_player(player_id):
    with players_lock:
        players.pop(player_id, None)
    with connections_lock:
        conn = connections.pop(player_id, None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    print(f"[SERVER] Joueur déconnecté : {player_id}")
    print(f"[SERVER] Joueurs connectés : {list(players.keys())}")


def handle_client(conn, addr, player_id):
    print(f"[SERVER] Nouveau joueur : {player_id} depuis {addr}")
    buffer = ""

    try:
        while True:
            data = conn.recv(1024).decode("utf-8", errors="ignore")
            if not data:
                break

            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)

                    if isinstance(msg, dict) and msg.get("type") == "damage":
                        target_id = msg.get("target_id")
                        print(f"[SERVER] Dégâts de {player_id} vers {target_id} ({msg.get('amount')} dmg)")
                        send_to_player(target_id, msg)

                    elif isinstance(msg, dict) and msg.get("type") == "survivant_fini":
                        print(f"[SERVER] Joueur {player_id} a fini ses tâches, on broadcast à tous")
                        broadcast_message(msg)

                    elif isinstance(msg, dict) and msg.get("type") == "liberer_joueur":
                        target_id = msg.get("target_id")
                        print(f"[SERVER] Libération de {target_id} par {player_id}")
                        send_to_player(target_id, msg)
                    
                    elif isinstance(msg, dict) and msg.get("type") == "survivant_emprisonne":
                        print(f"[SERVER] Survivant emprisonné : {player_id}")
                        broadcast_message(msg)

                    else:
                        with players_lock:
                            players[player_id] = msg
                        broadcast_state()

                except json.JSONDecodeError:
                    pass

    except Exception as e:
        print(f"[SERVER] Erreur avec {player_id} : {e}")
    finally:
        remove_player(player_id)


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER] En écoute sur {HOST}:{PORT}")

    while True:
        try:
            conn, addr = server.accept()
            player_id = str(uuid.uuid4())[:8]

            # On envoie l'ID AVANT d'enregistrer le joueur : si le client a déjà
            # coupé (scan, réseau qui lâche), on abandonne sans laisser de fantôme.
            try:
                conn.sendall((json.dumps({"my_id": player_id}) + "\n").encode())
            except Exception:
                conn.close()
                continue

            with players_lock:
                players[player_id] = {"x": 0, "y": 0, "z": 0}
            with connections_lock:
                connections[player_id] = conn

            t = threading.Thread(target=handle_client, args=(conn, addr, player_id), daemon=True)
            t.start()

        except Exception as e:
            # Quoi qu'il arrive sur une connexion, le serveur ne tombe jamais.
            print(f"[SERVER] Erreur sur accept() : {e}")


if __name__ == "__main__":
    start_server()