import socket
import threading
import json
import random

HOST = '' # Ip do computador
PORT = 5000 # Porta do servidor

clients = []
players = {}
turn = 0
games = {}
game_started = False

ELEMENTS = ["fire", "water", "plant", "electric", "earth"]

ADVANTAGES = {
    "fire": "plant",
    "water": "fire",
    "plant": "earth",
    "electric": "water",
    "earth": "electric"
}
DISADVANTAGES = {v: k for k, v in ADVANTAGES.items()}

ABILITIES = {
    1: {"name": "Ataque Forte", "dmg": (25, 35), "accuracy": 0.6, "mana_cost": 15, "special": False},
    2: {"name": "Ataque Rápido", "dmg": (10, 20), "accuracy": 0.9, "mana_cost": 7, "special": False},
    3: {"name": "Ataque Especial", "dmg": (30, 50), "accuracy": 0.7, "mana_cost": 20, "special": True}
}

MAX_HP = 100
MAX_MANA = 50

lock = threading.Lock()

def send_json(conn, data):
    try:
        json_data = json.dumps(data).encode('utf-8')
        conn.sendall(json_data + b'\n')
    except:
        pass 

def broadcast_game(game_id, data):
    with lock:
        for pid in games[game_id]['players']:
           player = players[pid]
           send_json(player['conn'], data)

def calculate_damage(attacker_element, defender_element, base_dmg):
    if attacker_element == defender_element:
        return base_dmg // 2  
    elif ADVANTAGES[attacker_element] == defender_element:
        return base_dmg * 2  
    elif DISADVANTAGES[attacker_element] == defender_element:
        return base_dmg // 4  
    else:
        return base_dmg 

def start_game():
    with lock:
        waiting_players = [pid for pid, p in players.items() if p["game_id"] is None]
        while len(waiting_players) >= 2:
            p1 = waiting_players.pop(0)
            p2 = waiting_players.pop(0)
            game_id = f"Game{len(games) + 1}"
            games[game_id] = {
                'players': [p1, p2],
                'turn': 0,
                'started': "playing"
            }
            players[p1]["game_id"] = game_id
            players[p2]["game_id"] = game_id
            players[p1]["hp"] = MAX_HP
            players[p2]["hp"] = MAX_HP
            players[p1]["mana"] = MAX_MANA
            players[p2]["mana"] = MAX_MANA

            start_msg = {
                "type": "GAME_START",
                "game_id": game_id,
                "payload": {
                    "players": {
                        p1: { "hp":MAX_HP, "mana": MAX_MANA },
                        p2: { "hp": MAX_HP, "mana": MAX_MANA }
                    },
                    },
                    "msg": "Jogo iniciado!",
             }
            broadcast_game(game_id, start_msg)

            send_json(players[p1]['conn'], {
                "type": "YOUR_TURN",
                "game_id": game_id,
                "payload": {
                    "msg": "Sua vez de jogar!",
                }
            })


def handle_client(conn, addr):
    global clients, players, games
    print(f"Conexão estabelecida com {addr}")

    send_json(conn, {"type": "LOGIN_REQUEST", "payload": {"msg": "Envie JOIN_GAME para entrar na partida"}})
    try:
        data = conn.recv(1024).decode('utf-8').strip()
        login_msg = json.loads(data)
        if login_msg["type"] != "JOIN_GAME":
            send_json(conn, {"type": "LOGIN_FAIL", "payload": {"msg": "Comando inválido. Use JOIN_GAME para entrar na partida."}})
            conn.close()
            return
        player_id = login_msg.get("player_id")
        if not player_id:
            send_json(conn, {"type": "LOGIN_FAIL", "payload": {"msg": "player_id é obrigatório."}})
            conn.cl ose()
            return
    except:
        conn.close()
        return

    with lock:
        clients[conn] = player_id
        players[player_id] = {
            "conn": conn,
            "hp": MAX_HP,
            "mana": MAX_MANA,
            "game_id": None,
            "last_element": None,
            "last_ability": None
        }

    send_json(conn, {"type": "LOGIN_SUCCESS", "payload": {"msg": f"Bem-vindo, {player_id}!"}})  
