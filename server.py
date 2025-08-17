import socket
import threading
import json
import random

HOST = ''  # IP do servidor ('' aceita conexões de qualquer interface)
PORT = 5000

clients = {}
games = {}
lock = threading.Lock()

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


def send_json(conn, data):
    json_data = json.dumps(data).encode('utf-8')
    conn.sendall(json_data + b'\n')


def broadcast(game_id, data):
    for player_id in games[game_id]["players"]:
        conn = clients[player_id]
        send_json(conn, data)


def calculate_damage(attacker_element, defender_element, ability):
    dmg = random.randint(*ability["dmg"])
    # checa vantagem/desvantagem
    if attacker_element == defender_element:
        dmg //= 2
    elif ADVANTAGES[attacker_element] == defender_element:
        dmg *= 2
    elif DISADVANTAGES[attacker_element] == defender_element:
        dmg //= 2
    return dmg


def handle_game(game_id):
    game = games[game_id]
    players = list(game["players"].keys())
    turn = 0

    broadcast(game_id, {"type": "GAME_START", "game_id": game_id,
                        "payload": {"players": players}})

    while True:
        current_player = players[turn % 2]
        opponent = players[(turn + 1) % 2]

        send_json(clients[current_player], {
            "type": "YOUR_TURN",
            "game_id": game_id,
            "payload": game["players"][current_player]
        })

        # aguarda jogada
        move = game["queue"].pop(0)
        if move["player_id"] != current_player:
            continue  # ignora fora de turno

        action = move["payload"]

        # ação escolhida
        if action["move"] == "GAIN_MANA":
            game["players"][current_player]["mana"] = min(
                MAX_MANA, game["players"][current_player]["mana"] + 10)
            result = f"{current_player} recuperou mana!"
        else:
            element = action["element"]
            ability = ABILITIES[action["ability"]]

            player_state = game["players"][current_player]
            opp_state = game["players"][opponent]

            if player_state["mana"] < ability["mana_cost"]:
                result = f"{current_player} tentou usar {ability['name']} mas não tinha mana!"
            else:
                player_state["mana"] -= ability["mana_cost"]

                if random.random() <= ability["accuracy"]:
                    dmg = calculate_damage(element, opp_state["element"], ability)
                    opp_state["hp"] = max(0, opp_state["hp"] - dmg)
                    result = f"{current_player} atacou com {element} usando {ability['name']} causando {dmg} de dano!"
                else:
                    result = f"{current_player} errou o ataque!"

        # envia atualização
        broadcast(game_id, {
            "type": "GAME_UPDATE",
            "game_id": game_id,
            "payload": {
                "state": game["players"],
                "log": result
            }
        })

        # checa fim de jogo
        if game["players"][opponent]["hp"] <= 0:
            broadcast(game_id, {
                "type": "GAME_END",
                "game_id": game_id,
                "payload": {"winner": current_player}
            })
            break

        turn += 1


def handle_client(conn, addr):
    try:
        player_id = None
        while True:
            data = conn.recv(1024)
            if not data:
                break

            for line in data.splitlines():
                msg = json.loads(line.decode('utf-8'))

                if msg["type"] == "LOGIN":
                    player_id = msg["player_id"]
                    clients[player_id] = conn
                    send_json(conn, {"type": "STATUS", "status": "OK"})
                elif msg["type"] == "JOIN_GAME":
                    game_id = "game1"  # simplificação: só 1 partida
                    if game_id not in games:
                        games[game_id] = {
                            "players": {},
                            "queue": []
                        }
                    games[game_id]["players"][player_id] = {
                        "hp": MAX_HP,
                        "mana": MAX_MANA,
                        "element": random.choice(ELEMENTS)
                    }
                    if len(games[game_id]["players"]) == 2:
                        threading.Thread(target=handle_game, args=(game_id,), daemon=True).start()

                elif msg["type"] == "PLAY_MOVE":
                    game_id = msg["game_id"]
                    with lock:
                        games[game_id]["queue"].append(msg)

    finally:
        if player_id in clients:
            del clients[player_id]
        conn.close()


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor rodando em {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    start_server()
