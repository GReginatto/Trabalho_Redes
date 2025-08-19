import socket
import threading
import json
import random
import queue

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
    1: {"name": "Ataque Forte", "dmg": (20, 25), "accuracy": 0.6, "mana_cost": 20, "special": False},
    2: {"name": "Ataque Rápido", "dmg": (5, 15), "accuracy": 0.9, "mana_cost": 10, "special": False},
    3: {"name": "Ataque Especial", "dmg": (40, 60), "accuracy": 1, "mana_cost": 30, "special": True}
}

MAX_HP = 150
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
                        "payload": {"players": game["players"]}})

    while True:
        current_player = players[turn % 2]
        opponent = players[(turn + 1) % 2]

        send_json(clients[current_player], {
            "type": "YOUR_TURN",
            "game_id": game_id,
            "payload": game["players"][current_player]
        })

        # aguarda jogada
        move = game["queue"].get()
        if move["player_id"] != current_player:
            continue  # ignora fora de turno

        action = move["payload"]
        ability_id = action["ability_id"]

        # ação escolhida
        if ability_id == "pass":
            game["players"][current_player]["mana"] = min(
                MAX_MANA, game["players"][current_player]["mana"] + 15)
            result = f"{current_player} recuperou mana!"
        else:
            element = action["element"]
            ability = ABILITIES[action["ability_id"]]
            player_state = game["players"][current_player]
            opp_state = game["players"][opponent]

            if ability.get("special") and player_state["special_attack_used"]:
                result = f"{current_player} tentou usar {ability['name']}, mas já foi utilizado!"

            elif player_state["mana"] < ability["mana_cost"]:
                result = f"{current_player} tentou usar {ability['name']} mas não tinha mana!"
            else:
                player_state["mana"] -= ability["mana_cost"]

                if ability.get("special"):
                    player_state["special_attack_used"] = True

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
                "players": game["players"],
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

                if msg["type"] == "JOIN_GAME":
                    player_id = msg["player_id"]
                    clients[player_id] = conn
                    print(f"Player '{player_id}' entrou no jogo")
                
                    game_id = "game1"
                    if game_id not in games:
                        games[game_id] = {
                            "players": {},
                            "queue": queue.Queue()
                        }
                    games[game_id]["players"][player_id] = {
                        "hp": MAX_HP,
                        "mana": MAX_MANA,
                        "element": random.choice(ELEMENTS),
                        "special_attack_used": False
                    }
                    if len(games[game_id]["players"]) == 2:
                        print(f"Jogadores encontrados. Iniciando jogo '{game_id}'.") # Optional
                        threading.Thread(target=handle_game, args=(game_id,), daemon=True).start()

                elif msg["type"] == "PLAY_MOVE":
                    game_id = msg["game_id"]
                    msg["player_id"] = player_id
                    games[game_id]["queue"].put(msg)

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
