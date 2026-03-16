import socket
import threading
import json

SERVER_HOST = "86.242.238.8"
SERVER_PORT = 5555


class NetworkClient:
    def __init__(self):
        self.sock = None
        self.my_id = None
        self.other_players = {}
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
            print(f"[CLIENT] Impossible de se connecter : {e}")
            self.connected = False
            return False

    def _receive_loop(self):
        while self.connected:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                self._buffer += data

                while "\n" in self._buffer:
                    line, self._buffer = self._buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)

                        if "my_id" in msg:
                            self.my_id = msg["my_id"]
                            print(f"[CLIENT] Mon ID joueur : {self.my_id}")

                        else:
                            nouveaux_joueurs = {}
                            for pid, pos in msg.items():
                                if pid != self.my_id:
                                    nouveaux_joueurs[pid] = pos

                            with self._lock:
                                self.other_players = nouveaux_joueurs

                    except json.JSONDecodeError:
                        pass

            except Exception as e:
                print(f"[CLIENT] Erreur réception : {e}")
                break

        self.connected = False
        print("[CLIENT] Déconnecté du serveur.")

    def send_position(self, x, y, z):
        if not self.connected:
            return
        try:
            pos = json.dumps({"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)}) + "\n"
            self.sock.sendall(pos.encode())
        except Exception as e:
            print(f"[CLIENT] Erreur envoi : {e}")
            self.connected = False

    def get_other_players(self):
        with self._lock:
            return dict(self.other_players)

    def disconnect(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
