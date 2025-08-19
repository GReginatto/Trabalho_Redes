import socket
import json
import threading

#HOST = '' # IP do servidor
HOST = 'localhost'
PORT = 5000


ELEMENTS = ["fire", "water", "plant", "electric", "earth"]
ABILITIES = {
    "1": {"name": "Ataque Forte", "mana_cost": 20},
    "2": {"name": "Ataque Rápido", "mana_cost": 10},
    "3": {"name": "Ataque Especial", "mana_cost": 30}
}

client_socket = None
player_id = None
game_id = None
is_my_turn = False
lock = threading.Lock()

def send_json(data):
    if client_socket:
        try:
            client_socket.sendall(json.dumps(data).encode('utf-8') + b'\n')
        except Exception as e:
            print(f"[ERRO] Falha ao enviar dados: {e}")

def display_game_state(players_data):
    print("\n--- ESTADO ATUAL DA PARTIDA ---")
    for pid, stats in players_data.items():
        id_display = f"{pid} (Você)" if pid == player_id else pid
        element_display = f"Elemento: {stats['element'].capitalize()}" if pid == player_id else "Elemento: ????"
        mana_display = f"Mana: {stats['mana']}" if pid == player_id  else "Mana: ????"
        print(f"  {id_display:<20} HP: {stats['hp']:<4} | {element_display:<22} | {mana_display:<20}")
    print("--------------------------------\n")

def receive_messages():
    global game_id, is_my_turn
    buffer = ""
    while True:
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data: break
            buffer += data
            while '\n' in buffer:
                message_str, buffer = buffer.split('\n', 1)
                response = json.loads(message_str)
                msg_type = response.get("type")
                payload = response.get("payload", {})
                
                server_message = ""
                if 'log' in payload:
                    server_message = payload['log']
                elif 'winner' in payload:
                    server_message = f"O Vencedor é: {payload['winner']}!"
                elif 'msg' in payload:
                    server_message = payload['msg']

                if server_message:
                    print(f"\n[SERVIDOR] {server_message}")

                if msg_type == "GAME_START":
                    with lock: game_id = response.get("game_id")
                    if "players" in payload: display_game_state(payload["players"])
                
                elif msg_type == "GAME_UPDATE":
                    if "players" in payload: display_game_state(payload["players"])

                elif msg_type == "YOUR_TURN":
                    with lock: is_my_turn = True
                
                elif msg_type == "GAME_END":
                    with lock:
                        is_my_turn = False
                        game_id = None
                    print("O jogo acabou. Obrigado por jogar!")

        except (ConnectionResetError, json.JSONDecodeError):
            break
    print("Conexão com o servidor perdida.")
    client_socket.close()

def prompt_for_action():
    global is_my_turn
    print("\n--- SUA VEZ DE JOGAR ---")
    print("Escolha um elemento:")
    for i, element in enumerate(ELEMENTS): print(f"  {i+1}. {element.capitalize()}")
    
    element_choice = 0
    while element_choice not in range(1, len(ELEMENTS) + 1):
        try: element_choice = int(input(">> Digite o número do elemento: "))
        except: pass

    print("\nEscolha uma habilidade:")
    for key, ability in ABILITIES.items(): print(f"  {key}. {ability['name']} (Mana: {ability['mana_cost']})")
    print("  pass. Passar a vez")

    ability_choice = ""
    while ability_choice not in list(ABILITIES.keys()) + ["pass"]:
        ability_choice = input(">> Digite o número da habilidade ou 'pass': ").lower()

    move_payload = {
        "element": ELEMENTS[element_choice - 1],
        "ability_id": int(ability_choice) if ability_choice != "pass" else "pass"
    }
    send_json({"type": "PLAY_MOVE", "game_id": game_id, "payload": move_payload})
    with lock: is_my_turn = False

def main():
    global client_socket, player_id
    player_id = input("Digite seu nome de jogador: ").strip()
    if not player_id: return

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
    except Exception as e:
        print(f"Não foi possível conectar: {e}"); return

    threading.Thread(target=receive_messages, daemon=True).start()
    send_json({"type": "JOIN_GAME", "player_id": player_id})

    while True:
        with lock:
            my_turn_now = is_my_turn
        if my_turn_now:
            prompt_for_action()
        else:
            pass

if __name__ == "__main__":
    main()
