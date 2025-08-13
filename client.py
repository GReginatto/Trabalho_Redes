import socket
import json
import threading

SERVER_HOST = '' # IP DO SERVIDOR / PC
SERVER_PORT = 5000 

player_id = input("Digite seu ID de jogador: ")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_HOST, SERVER_PORT))
