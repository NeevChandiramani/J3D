import socket
import threading
import json

SERVER_HOST = "dyn.ychandir.com"
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

    def send_position(self, x, y, z, ry):
        """Envoie position ET rotation Y au serveur."""
        if not self.connected: return
        try:
            data = {
                "x": round(x, 2), 
                "y": round(y, 2), 
                "z": round(z, 2), 
                "ry": round(ry, 2)
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

    def disconnect(self):
        self.connected = False
        if self.sock: self.sock.close()
