import socket, json

s = socket.socket()
s.settimeout(5)
s.connect(("127.0.0.1", 9876))
s.sendall((json.dumps({"command": "ping", "params": {}}) + "\n").encode())
print(s.recv(4096).decode())
s.close()
