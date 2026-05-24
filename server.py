import socket
import threading
import json
import uuid
import random

HOST = "0.0.0.0"
PORT = 5555

# Positions des joueurs (broadcasté à tous à chaque mise à jour)
players = {}
players_lock = threading.Lock()

# Connexions TCP par player_id
connections = {}
connections_lock = threading.Lock()

# État du lobby : {pid: {"ready": bool}}
lobby = {}
lobby_lock = threading.Lock()

# Une fois les rôles tirés, ils sont figés pour la partie
assigned_roles = None         # {pid: "Infected"/"Survivor"} ou None
roles_lock = threading.Lock()

# Pourcentage d'Infectés en multijoueur (≥ 2 joueurs)
INFECTED_RATIO = 0.35


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
            print(f"[SERVER] Message relayé vers {player_id} : {msg.get('type')}")
        except Exception as e:
            print(f"[SERVER] Erreur envoi à {player_id} : {e}")
    else:
        print(f"[SERVER] Cible {player_id} introuvable")


def broadcast_lobby_state():
    with lobby_lock:
        snapshot = {pid: dict(info) for pid, info in lobby.items()}
    broadcast_message({"type": "lobby_state", "players": snapshot})


def maybe_assign_roles(force=False):
    """Tire les rôles et les broadcast. Idempotent : ne fait rien si déjà attribués.
    En mode normal, attend que tous les joueurs présents soient prêts.
    Avec force=True, démarre immédiatement avec les joueurs connectés."""
    global assigned_roles

    with roles_lock:
        if assigned_roles is not None:
            return  # déjà fait

        with lobby_lock:
            pids = list(lobby.keys())
            all_ready = len(pids) >= 2 and all(lobby[p].get("ready") for p in pids)

        if not force and not all_ready:
            return

        if not pids:
            return

        if len(pids) <= 1:
            # Solo : 70/30 comme avant
            role = random.choices(["Survivor", "Infected"], weights=[70, 30])[0]
            roles = {pids[0]: role}
        else:
            nb_infectes = max(1, min(len(pids) - 1, round(len(pids) * INFECTED_RATIO)))
            infectes = set(random.sample(pids, nb_infectes))
            roles = {p: ("Infected" if p in infectes else "Survivor") for p in pids}

        assigned_roles = roles

    print(f"[SERVER] Rôles attribués ({'force' if force else 'all-ready'}) : {roles}")
    broadcast_message({"type": "roles", "roles": roles})


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
    with lobby_lock:
        lobby.pop(player_id, None)
    # Si tout le monde est parti, on autorise une nouvelle partie : reset des rôles.
    with connections_lock:
        remaining = len(connections)
    if remaining == 0:
        global assigned_roles
        with roles_lock:
            assigned_roles = None
        print("[SERVER] Plus aucun joueur connecté, reset des rôles")

    print(f"[SERVER] Joueur déconnecté : {player_id}")
    print(f"[SERVER] Joueurs connectés : {list(players.keys())}")
    # Rebroadcast du lobby pour que les autres voient la liste à jour
    broadcast_lobby_state()


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

                    elif isinstance(msg, dict) and msg.get("type") == "screamer":
                        print(f"[SERVER] Screamer de {player_id} -> broadcast")
                        broadcast_message(msg)

                    elif isinstance(msg, dict) and msg.get("type") == "survivant_fini":
                        print(f"[SERVER] Joueur {player_id} a fini ses tâches, on broadcast à tous")
                        broadcast_message(msg)

                    elif isinstance(msg, dict) and msg.get("type") == "liberer_joueur":
                        target_id = msg.get("target_id")
                        print(f"[SERVER] Libération de {target_id} par {player_id}")
                        send_to_player(target_id, msg)

                    elif isinstance(msg, dict) and msg.get("type") == "ready":
                        is_ready = bool(msg.get("ready", False))
                        with lobby_lock:
                            if player_id in lobby:
                                lobby[player_id]["ready"] = is_ready
                        print(f"[SERVER] {player_id} ready={is_ready}")
                        broadcast_lobby_state()
                        maybe_assign_roles()

                    elif isinstance(msg, dict) and msg.get("type") == "force_start":
                        print(f"[SERVER] {player_id} force_start")
                        maybe_assign_roles(force=True)

                    else:
                        # Position / état d'animation : on stocke et on broadcast l'état complet
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
            with lobby_lock:
                lobby[player_id] = {"ready": False}

            # Si la partie est déjà en cours (rôles déjà tirés), on assigne
            # Survivor par défaut au retardataire et on rebroadcast à tous
            # pour que chacun ait la liste complète des rôles à jour.
            with roles_lock:
                if assigned_roles is not None:
                    assigned_roles[player_id] = "Survivor"
                    current_roles = dict(assigned_roles)
                else:
                    current_roles = None

            # Notifier tout le monde du nouvel arrivé dans le lobby
            broadcast_lobby_state()

            if current_roles is not None:
                broadcast_message({"type": "roles", "roles": current_roles})

            t = threading.Thread(target=handle_client, args=(conn, addr, player_id), daemon=True)
            t.start()

        except Exception as e:
            # Quoi qu'il arrive sur une connexion, le serveur ne tombe jamais.
            print(f"[SERVER] Erreur sur accept() : {e}")


if __name__ == "__main__":
    start_server()
