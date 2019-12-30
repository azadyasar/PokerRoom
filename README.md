A poker server that is capable of handling multiple games to multiple clients on a LAN at once. Launch the server by issuing the following command:
```
python3 poker_server.py -s <your-ip> -p <port> -tp <target-port>
```

IP and port is self-explanatory. Target port is the port that will be used among client while initiating a connection from server to client.

To launch a client, issue:
```
python3 client.py -ip <your-ip> -p <port> -u <uname>
```

Once launched, clients will find the server automatically and ask the user if they want to play or spectate. If there are more than 2 players at a table the server will instantly start a game.

- Drawn cards for the clients are encrypted and sent with TCP to the clients individually.
- Table updates are multicasted to clients.
- Spectators are able to see every update on the table.
- There can be multiple users with the same IP, assuming they use different usernames.
- A client/IP cannot be a spectator and a player at the same time.
