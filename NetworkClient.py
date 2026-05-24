import socket
import threading
import json

SERVER_HOST = "89.168.46.126"
SERVER_PORT = 5555

class NetworkClient:
    def __init__(self):
        self.sock = None
        self.my_id = None
        self.other_players = {}
        self.damage_queue = []  # Liste des dégâts reçus du serveur
        self.connected = False
        self._lock = threading.Lock()
        self._buffer = ""
        self.game_event_queue = []
        self.lobby_state = {}        # {pid: {"ready": bool}}
        self.assigned_roles = None   # None tant qu'on n'a pas reçu de "roles" du serveur

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            self.sock.settimeout(None)
            self.connected = True
            print(f"[CLIENT] Connecté au serveur {SERVER_HOST}:{SERVER_PORT}")

            t = threading.Thread(target=self._receive_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            print(f"[CLIENT] Erreur connexion : {e}")
            self.connected = False
            return False

    def _receive_loop(self):
        while self.connected:
            try:
                data = self.sock.recv(4096).decode()
                if not data: break
                self._buffer += data

                while "\n" in self._buffer:
                    line, self._buffer = self._buffer.split("\n", 1)
                    line = line.strip()
                    if not line: continue

                    try:
                        msg = json.loads(line)

                        # Cas 1 : Le serveur nous donne notre ID au début
                        if "my_id" in msg:
                            self.my_id = str(msg["my_id"])
                            print(f"[CLIENT] Mon ID : {self.my_id}")

                        # Cas 2 : C'est un message d'attaque / dégâts
                        elif isinstance(msg, dict) and msg.get("type") == "damage":
                            with self._lock:
                                self.damage_queue.append(msg)

                        # Cas 3 : C'est un screamer à afficher
                        elif isinstance(msg, dict) and msg.get("type") == "screamer":
                            with self._lock:
                                self.damage_queue.append(msg)

                        elif isinstance(msg, dict) and msg.get("type") == "survivant_fini":
                            with self._lock:
                                self.game_event_queue.append(msg)

                        elif isinstance(msg, dict) and msg.get("type") == "liberer_joueur":
                            with self._lock:
                                self.game_event_queue.append(msg)

                        # Cas lobby : état des joueurs (prêt / pas prêt)
                        elif isinstance(msg, dict) and msg.get("type") == "lobby_state":
                            with self._lock:
                                self.lobby_state = dict(msg.get("players", {}))
                            try:
                                print(f"[CLIENT] lobby_state reçu : {self.lobby_state}")
                            except Exception:
                                pass

                        # Cas roles : attribution des rôles par le serveur
                        elif isinstance(msg, dict) and msg.get("type") == "roles":
                            with self._lock:
                                self.assigned_roles = dict(msg.get("roles", {}))
                            try:
                                print(f"[CLIENT] Rôles reçus : {self.assigned_roles}")
                            except Exception:
                                pass
                        
                        elif isinstance(msg, dict) and msg.get("type") == "survivant_emprisonne":
                            with self._lock:
                                self.game_event_queue.append(msg)

                        # Cas 4 : C'est la liste des positions/rotations des joueurs
                        else:
                            nouveaux_joueurs = {}
                            for pid, pos in msg.items():
                                if str(pid) != str(self.my_id):
                                    nouveaux_joueurs[str(pid)] = pos
                            with self._lock:
                                self.other_players = nouveaux_joueurs

                    except json.JSONDecodeError:
                        pass
            except Exception:
                break
        self.connected = False

    def send_position(self, x, y, z, ry, mv=0, sp=0, atk=0, at=0.0):
        """Envoie position, rotation Y et état d'animation au serveur.
        mv = is_moving, sp = is_sprinting, atk = is_attack_anim, at = _anim_timer.
        """
        if not self.connected: return
        try:
            data = {
                "x": round(x, 2),
                "y": round(y, 2),
                "z": round(z, 2),
                "ry": round(ry, 2),
                "mv": int(mv),
                "sp": int(sp),
                "atk": int(atk),
                "at": round(float(at), 2),
            }
            self.sock.sendall((json.dumps(data) + "\n").encode())
        except Exception:
            self.connected = False

    def send_damage(self, target_id, amount):
        """Envoie une attaque au serveur pour qu'il la relaie."""
        if not self.connected: return
        try:
            msg = {
                "type": "damage",
                "target_id": str(target_id),
                "amount": amount,
                "attacker_id": self.my_id
            }
            self.sock.sendall((json.dumps(msg) + "\n").encode())
            print(f"[COMBAT] Attaque envoyée vers {target_id}")
        except Exception as e:
            print(f"Erreur envoi dégâts : {e}")

    def get_damage_events(self):
        """Récupère les dégâts subis et vide la liste."""
        with self._lock:
            events = list(self.damage_queue)
            self.damage_queue.clear()
            return events

    def get_other_players(self):
        with self._lock:
            return dict(self.other_players)

    def send_screamer(self, screamer_name):
        """Envoie un screamer à tous les autres joueurs."""
        if not self.connected: return
        try:
            msg = {
                "type": "screamer",
                "screamer": screamer_name,
                "sender_id": self.my_id
            }
            self.sock.sendall((json.dumps(msg) + "\n").encode())
            print(f"[SCREAMER] Envoyé : {screamer_name}")
        except Exception as e:
            print(f"Erreur envoi screamer : {e}")

    def send_ready(self, is_ready):
        """Indique au serveur si ce joueur est prêt à démarrer la partie."""
        if not self.connected: return
        try:
            msg = {"type": "ready", "ready": bool(is_ready)}
            self.sock.sendall((json.dumps(msg) + "\n").encode())
            print(f"[LOBBY] Ready={is_ready} envoyé")
        except Exception as e:
            print(f"Erreur envoi ready : {e}")

    def send_force_start(self):
        """Demande au serveur de démarrer la partie sans attendre que tous soient prêts."""
        if not self.connected: return
        try:
            msg = {"type": "force_start"}
            self.sock.sendall((json.dumps(msg) + "\n").encode())
            print("[LOBBY] Force start envoyé")
        except Exception as e:
            print(f"Erreur envoi force_start : {e}")

    def get_lobby_state(self):
        """Retourne l'état du lobby : {pid: {"ready": bool}}."""
        with self._lock:
            return dict(self.lobby_state)

    def get_assigned_roles(self):
        """Retourne le dict des rôles si le serveur les a déjà attribués, sinon None."""
        with self._lock:
            return dict(self.assigned_roles) if self.assigned_roles is not None else None

    def disconnect(self):
        self.connected = False
        if self.sock: self.sock.close()

    def get_game_events(self):
        with self._lock:
            events = list(self.game_event_queue)
            self.game_event_queue.clear()
            return events
