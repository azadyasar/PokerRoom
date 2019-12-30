import sys
import socket
import struct
import threading
import time
import argparse
import re
#from pynput import keyboard
import select
from math import sqrt, log, ceil
from random import randrange
import pyDes
import base64
import pickle
import game_utils

SIZE = 1024
PORT = 12345
# Maximum number to check while generating a random prime number
LIMIT = 999999999
SECRET_KEY_MAX_NUMBER = 99999
# CONSTANTS
POKER_MESSAGE_TYPE_INIT = "init"
POKER_MESSAGE_TYPE_PLAY = "play"
POKER_MESSAGE_TYPE_FOLD = "fold"
POKER_MESSAGE_TYPE_UPDATE = "update"
POKER_MESSAGE_TYPE_INVALID_BET = "invalid-bet"
POKER_MESSAGE_TYPE_VALID_BET = "valid-bet"
POKER_MESSAGE_TYPE_WATCH = "watch"
POKER_MESSAGE_TYPE_SPEC = "spectator"
POKER_MESSAGE_TYPE_SIT = "spectator-sit"
POKER_MESSAGE_TYPE_TURN = "turn"
POKER_MESSAGE_TYPE_TABLE = "table"
POKER_MESSAGE_TYPE_CARDS = "cards"
POKER_MESSAGE_TYPE_CHIPS = "chips"
POKER_MESSAGE_TYPE_INIT_RESPONSE = "init-response"
# Server is announcing that it is serving a poker game
POKER_MESSAGE_TYPE_ANNOUNCE = "announce"
# A message type that the clients broadcast to find game servers available
POKER_MESSAGE_TYPE_CLIENTCAST = "clientcast"




#########




IS_WINDOWS = (len(re.findall('[Ww]in', sys.platform)) != 0)


def is_prime(num: int) -> bool:
    if num == 2:
        return True
    if num % 2 == 0 or num < 2:
        return False
    for i in range(3, ceil(sqrt(num)), 2):
        if num % i == 0:
            return False
    return True


def generate_prime(limit: int) -> int:
    while 1:
        candidate = randrange(2, limit)
        if is_prime(candidate):
            return candidate





def encrypt_message(data, key):
    """ 
    Encodes data 

    :param data: Data to be encoded 
    :type data: str 
    :returns:  string -- Encoded data 
    """
    key_handle = pyDes.triple_des(
        str(key).ljust(24),
        pyDes.CBC,
        "\0\0\0\0\0\0\0\0",
        padmode=pyDes.PAD_PKCS5)
    encrypted = key_handle.encrypt(
        data=data)
    return base64.b64encode(s=encrypted)


def decrypt_message(data, key):
    """ 
    Decodes data 

    :param data: Data to be decoded 
    :type data: str 
    :returns:  string -- Decoded data 
    """
    key_handle = pyDes.triple_des(
        str(key).ljust(24),
        pyDes.CBC,
        "\0\0\0\0\0\0\0\0",
        padmode=pyDes.PAD_PKCS5)
    decrypted = key_handle.decrypt(
        data=base64.b64decode(s=data))
    return decrypted


class PokerMessage(object):
    def __init__(self, _type, username: str = None, data=None, g: int = None, p: int = None, A: int = None, table: list = None, chips: int = None, 
            active: bool = None, order: int = None, total_bet:int=None, high_bet: int = None, key: int=None):
        self.type_ = _type
        self.username_ = username
        self.data_ = data
        self.g_ = g
        self.p_ = p
        self.A_ = A
        self.table_ = table
        #self.seat = seat
        self.chips_ = chips
        self.order_ = order
        self.total_bet_ = total_bet
        self.high_bet_ = high_bet
        self.key_ = key


    def __str__(self):
        return "Type: {}, Data: {}, username: {}, g-p-A: {}-{}-{}, table: {}, chips: {}, order: {}".format(
            self.type_, self.data_, self.username_, self.g_, self.p_, self.A_, self.table_ , self.chips_, self.order_)




class Player(object):
    def __init__(self, name: str, ip: str, g: int = None, p: int = None, B: int = None, spectating: bool=None, order: int = None , chips: int = None , high_bet: int = None, folded: bool=None): #, cards: list = None):
        self.name_ = name
        self.ip_ = ip
        self.g_ = g if g is not None else generate_prime(LIMIT)
        self.p_ = p if p is not None else generate_prime(LIMIT)
        self.a_ = randrange(SECRET_KEY_MAX_NUMBER)
        self.B_ = B
        self._calculate_A()
        self.cards_ = []
        self.socket_ = None
        self.chips_ = chips
        self.order_ = order
        self.table_id = None
        self.high_bet_ = high_bet
        self.folded_ = folded
        self.spectating_ = spectating
        if self.B_ is not None:
            self.calculate_key()
            print("{} has key: {}".format(self.name_, self.key_))


    

    def _calculate_A(self):
        self.A_ = self.g_ ** self.a_ % self.p_

    def calculate_key(self):
        self.key_ = self.B_ ** self.a_ % self.p_

    def __str__(self): return "Player: uname: {}, ip: {}, key: {}".format(
        self.name_, self.ip_, self.key_)


class Spectator(object):
    def __init__(self, name: str, ip: str):
        self.name_ = name
        self.ip_ = ip


class Game(object):

   
    
    def StartGameThread(self):
        while True:
            #print("--")
            if self.CAN_START_GAME:
                # print("Type \"start\" to start the game.")
                # user_input = input()
                # if user_input == "start":
                self.begin_game = threading.Thread(target=self.start_game)
                self.begin_game.start()
                self.CAN_START_GAME = False
            # else:
            #   import time
            #   time.sleep(3)
    

    def __init__(self, table_id, nbr_of_players: int = 0): #, CAN_START_GAME: bool = None, PLAYER_COUNT: int = None, TOTAL_PLAYERS: int = None):
        self.deck_ = game_utils.get_deck(shuffle_deck=True)
        self.player_dict_ = {}
        self.spect_dict_ = {}
        self.player_order_list_ = []
        self.table_ = []
        self.is_started_ = False
        self.waiting_list_ = []
        self.CAN_START_GAME = False
        self.PLAYER_COUNT = 0
        self.TOTAL_PLAYERS = 0
        self.LOCK_WAIT = False
        self.multicast_addresses = []


    def seat_available(self):
        return len(self.player_order_list_) + len(self.waiting_list_) <= 4

    def parse_raw_msg(self, payload: bytes) -> PokerMessage:
        return pickle.loads(payload)

    def add_player(self, player: Player):
        if self.PLAYER_COUNT == 0:
            StartGame = threading.Thread(target=self.StartGameThread)
            StartGame.start()
        print("Adding player {}".format(player.name_))
        print(player.socket_.getsockname())
        #self.multicast_addresses.append(player.socket_.getsockname()[0])
        self.multicast_addresses.append(player.socket_.getsockname())

        #PLAYER_COUNT = 0
        if self.is_started_:
            self.waiting_list_.append(player)
        elif player.spectating_ == False:
            self.deck_, player.cards_ = game_utils.draw_cards_from_deck(
            self.deck_, 2)
            player.chips_ = 10000
            player.order_ = self.PLAYER_COUNT
            self.PLAYER_COUNT = self.PLAYER_COUNT + 1
            print("Drawn cards for {} => {}".format(player.name_, player.cards_))

            self.player_dict_[player.name_] = player
            self.player_order_list_.append(player.name_)
            if len(self.player_order_list_) >= 2 and not self.is_started_:
                print("Game has more than 2 players. You can start the game.")
                self.TOTAL_PLAYERS = len(self.player_order_list_)
                #print(PLAYER_COUNT)
                self.CAN_START_GAME = True
        else:
            self.spect_dict_[player.name_] = player

            
            #self.start_game()

    def table_update(self):
        table_msg = PokerMessage(POKER_MESSAGE_TYPE_TABLE, table=self.table_)
        print("[INFO]: sending table update: ", self.table_)
        table_msg_bin = pickle.dumps(table_msg)
        #print("yo: "+ str(table_msg_bin))
        for uname in self.player_dict_:
            player = self.player_dict_[uname]
            player.socket_.send(table_msg_bin)
        for sname in self.spect_dict_:
            spectator = self.spect_dict_[sname]
            spectator.socket_.send(table_msg_bin)

    def bring_new_players(self):
        for player in self.waiting_list_:
            self.add_player(player)
        self.waiting_list_.clear()

    def start_game(self):

        players_in_game = []
        TABLE_BET = 0
        HIGH_BET = 0
        PLAYER_BET = 0
        player_bets = []
        PLAYER_FOLDED = False

        self.PLAYER_COUNT = 0

        self.is_started_ = True

        bets_on_table = 0
        #round zero, distribute cards to players
        for uname in self.player_dict_:
            #PLAYER_COUNT = PLAYER_COUNT + 1
            print(self.player_dict_[uname].cards_)
            print(self.player_dict_[uname].chips_)
            player = self.player_dict_[uname]
            
            cards_msg = PokerMessage(POKER_MESSAGE_TYPE_CARDS, table=self.player_dict_[uname].cards_, 
                chips=self.player_dict_[uname].chips_, order=self.PLAYER_COUNT, key = player.key_)
            players_in_game.append(1)
            self.PLAYER_COUNT = self.PLAYER_COUNT + 1
            cards_msg_bin = pickle.dumps(cards_msg)
            
            player.folded_ = False
            encrypted_msg = encrypt_message(cards_msg_bin, key = player.key_)
            player.socket_.send(encrypted_msg)

            for sname in self.spect_dict_:
                cards_msg = PokerMessage(POKER_MESSAGE_TYPE_CARDS, username = uname, table=self.player_dict_[uname].cards_)
                cards_msg_bin = pickle.dumps(cards_msg)
                spectator = self.spect_dict_[sname]
                spectator.socket_.send(cards_msg_bin)
        cards_on_table = []
        for round in range(3):
        # rounds
            HIGH_BET = 0
            # first round, 3 cards on table
            if round == 0:
                self.deck_, self.table_ = game_utils.draw_cards_from_deck(
                    self.deck_, 3)
                for x in range(3):
                    cards_on_table.append(self.table_[x])
            # second & third round, 1 card on table
            else:
                self.deck_, self.table_ = game_utils.draw_cards_from_deck(
                    self.deck_, 1)
                cards_on_table.append(self.table_[0])

            print((self.PLAYER_COUNT))
            self.table_update()
            
            # ask each player their bet
            for uname in self.player_dict_:
                name = uname
                player = self.player_dict_[uname]
                print(player.folded_)
                if player.folded_ == False:
                    name = uname
                    win = True
                    for other_name in self.player_dict_:
                        if other_name != name:
                            other_player = self.player_dict_[other_name]
                            if(other_player.folded_ == False):
                                win = False
                    if win:
                        print("player " + name + " has won!")
                        break
                    cards_msg = PokerMessage(POKER_MESSAGE_TYPE_TURN, username = uname)
                    #player_bets.append(0)
                    cards_msg_bin = pickle.dumps(cards_msg)
                    player.socket_.send(cards_msg_bin)
                    self.LOCK_WAIT = True
                    bets_on_table = TABLE_BET
                    print("Waiting for player " + uname)
                    player_bets.append(0)
                    while(self.LOCK_WAIT):
                        data = player.socket_.recv(1024)
                        client_msg = self.parse_raw_msg(data)
                        if client_msg.type_ == POKER_MESSAGE_TYPE_TURN:
                            #print("NEREDE 22")
                            order = client_msg.order_
                            name = client_msg.username_
                            print("!---!")
                            #print(client_msg.chips_ )
                            #print( player_bets[order])
                            #print("---")
                            print(order)
                            print(client_msg.chips_ )
                            print( player_bets[order])
                            print("!---!")
                            if client_msg.chips_ + player_bets[order] > HIGH_BET:
                                HIGH_BET = client_msg.chips_ + player_bets[order]
                                PLAYER_BET = client_msg.chips_
                                TABLE_BET = TABLE_BET + client_msg.chips_
                                player.chips_ = player.chips_ - (client_msg.chips_ + player_bets[order])
                                cards_msg = PokerMessage(POKER_MESSAGE_TYPE_VALID_BET, username = uname, chips=(client_msg.chips_))
                                cards_msg_bin = pickle.dumps(cards_msg)
                                player.socket_.send(cards_msg_bin)
                                self.LOCK_WAIT = False
                            elif client_msg.chips_ + player_bets[order] == HIGH_BET:
                                TABLE_BET = TABLE_BET + client_msg.chips_
                                PLAYER_BET = client_msg.chips_ + player_bets[order]
                                player.chips_ = player.chips_ - (client_msg.chips_ + player_bets[order])
                                cards_msg = PokerMessage(POKER_MESSAGE_TYPE_VALID_BET, username = uname, chips=(client_msg.chips_ ))
                                cards_msg_bin = pickle.dumps(cards_msg)
                                player.socket_.send(cards_msg_bin)
                                self.LOCK_WAIT = False
                            else:
                                msg = PokerMessage(POKER_MESSAGE_TYPE_INVALID_BET, high_bet=HIGH_BET, chips=player_bets[order])
                                msg_bin = pickle.dumps(msg)
                                player.socket_.send(msg_bin)
                                msg = PokerMessage(POKER_MESSAGE_TYPE_TURN, username = name)
                                msg_bin = pickle.dumps(msg)
                                player.socket_.send(msg_bin)
                        elif client_msg.type_ == POKER_MESSAGE_TYPE_FOLD:
                            order = client_msg.order_
                            name = client_msg.username_
                            print("folded client: " + str(order))
                            print(client_msg)
                            for uname in self.player_dict_:
                                if name == uname:
                                    print("heh")
                            players_in_game[order] = 0
                            self.LOCK_WAIT = False
                            PLAYER_FOLDED = True
                        elif client_msg.type_ == POKER_MESSAGE_TYPE_INVALID_BET:
                                cards_msg = PokerMessage(POKER_MESSAGE_TYPE_TURN, username = uname)
                                cards_msg_bin = pickle.dumps(cards_msg)
                                player.socket_.send(cards_msg_bin)
                                print("YENIDEN")
                                self.LOCK_WAIT = True
                    if PLAYER_FOLDED == True:
                            player.folded_ = True
                            PLAYER_FOLDED = False
                            player.folded_ = True
                            PLAYER_FOLDED = False
                            fold_msg = PokerMessage(POKER_MESSAGE_TYPE_FOLD, username = name)
                            print(fold_msg)
                            fold_msg_bin = pickle.dumps(fold_msg)
                            for oname in self.player_dict_:
                                other_player = self.player_dict_[oname]
                                other_player.socket_.send(fold_msg_bin)
                            for sname in self.spect_dict_:
                                spectator = self.spect_dict_[sname]
                                spectator.socket_.send(fold_msg_bin)
                    player_bets.pop()
                    player_bets.append(PLAYER_BET)
                    #while
                    player.high_bet_ = PLAYER_BET
                    #if players_in_game[order-1] == 0:
                        #print()
                    msg = PokerMessage(POKER_MESSAGE_TYPE_UPDATE, username = name, chips = (TABLE_BET-bets_on_table), total_bet = TABLE_BET)
                    msg_bin = pickle.dumps(msg)
                    print("GECTI")
                    for uname in self.player_dict_:
                        player = self.player_dict_[uname]
                        player.socket_.send(msg_bin)

                    for sname in self.spect_dict_:
                        spectator = self.spect_dict_[sname]
                        spectator.socket_.send(msg_bin)

            check_high_bets = True
            i = 0 

            # ask for bets again to match the highest bid
            while check_high_bets:
                for uname in self.player_dict_:
                    player = self.player_dict_[uname]
                    print(player.high_bet_)
                    if player.high_bet_ < HIGH_BET and player.folded_ == False:
                        name = uname
                        cards_msg = PokerMessage(POKER_MESSAGE_TYPE_TURN, username = uname, high_bet=(HIGH_BET-player.high_bet_))
                        cards_msg_bin = pickle.dumps(cards_msg)
                        player.socket_.send(cards_msg_bin)
                        self.LOCK_WAIT = True
                        bets_on_table = TABLE_BET
                        print("Waiting for player " + uname + str(player_bets[player.order_]))
                        while(self.LOCK_WAIT):
                            data = player.socket_.recv(1024)
                            client_msg = self.parse_raw_msg(data)
                            if client_msg.type_ == POKER_MESSAGE_TYPE_TURN:
                                #print("NEREDE 22")
                                order = client_msg.order_
                                name = client_msg.username_
                                print("!---!")
                                #print(client_msg.chips_ )
                                #print( player_bets[order])
                                #print("---")
                                print(order)
                                print(client_msg.chips_ )
                                print( player_bets[order])
                                print("!---!")
                                if client_msg.chips_ + player_bets[order] > HIGH_BET:
                                    HIGH_BET = client_msg.chips_ + player_bets[order]
                                    PLAYER_BET = client_msg.chips_
                                    TABLE_BET = TABLE_BET + client_msg.chips_
                                    player.chips_ = player.chips_ - (client_msg.chips_ + player_bets[order])
                                    cards_msg = PokerMessage(POKER_MESSAGE_TYPE_VALID_BET, username = uname, chips=(client_msg.chips_))
                                    cards_msg_bin = pickle.dumps(cards_msg)
                                    player.socket_.send(cards_msg_bin)
                                    self.LOCK_WAIT = False
                                elif client_msg.chips_ + player_bets[order] == HIGH_BET:
                                    TABLE_BET = TABLE_BET + client_msg.chips_
                                    PLAYER_BET = client_msg.chips_ + player_bets[order]
                                    player.chips_ = player.chips_ - (client_msg.chips_ + player_bets[order])
                                    cards_msg = PokerMessage(POKER_MESSAGE_TYPE_VALID_BET, username = uname, chips=(client_msg.chips_))
                                    cards_msg_bin = pickle.dumps(cards_msg)
                                    player.socket_.send(cards_msg_bin)
                                    self.LOCK_WAIT = False
                                else:
                                    msg = PokerMessage(POKER_MESSAGE_TYPE_INVALID_BET, high_bet=HIGH_BET,chips =player_bets[order])
                                    msg_bin = pickle.dumps(msg)
                                    player.socket_.send(msg_bin)

                                    msg = PokerMessage(POKER_MESSAGE_TYPE_TURN, username = name)
                                    msg_bin = pickle.dumps(msg)
                                    player.socket_.send(msg_bin)
                            elif client_msg.type_ == POKER_MESSAGE_TYPE_FOLD:
                                order = client_msg.order_
                                name = client_msg.username_
                                print("folded client: " + str(order))
                                print(client_msg)
                                for uname in self.player_dict_:
                                    if name == uname:
                                        print("heh")
                                players_in_game[order] = 0
                                self.LOCK_WAIT = False
                                PLAYER_FOLDED = True
                            elif client_msg.type_ == POKER_MESSAGE_TYPE_INVALID_BET:
                                cards_msg = PokerMessage(POKER_MESSAGE_TYPE_TURN, username = uname)
                                cards_msg_bin = pickle.dumps(cards_msg)
                                player.socket_.send(cards_msg_bin)
                                print("YENIDEN")
                                self.LOCK_WAIT = True
                        if PLAYER_FOLDED == True:
                            player.folded_ = True
                            PLAYER_FOLDED = False

                        if PLAYER_FOLDED == True:
                            player.folded_ = True
                            PLAYER_FOLDED = False
                            player.folded_ = True
                            PLAYER_FOLDED = False
                            fold_msg = PokerMessage(POKER_MESSAGE_TYPE_FOLD, username = name)
                            print(fold_msg)
                            fold_msg_bin = pickle.dumps(fold_msg)
                            for oname in self.player_dict_:
                                other_player = self.player_dict_[oname]
                                other_player.socket_.send(fold_msg_bin)
                            for sname in self.spect_dict_:
                                spectator = self.spect_dict_[sname]
                                spectator.socket_.send(fold_msg_bin)
                        player_bets[player.order_] = player_bets[player.order_] + PLAYER_BET
                        #while
                        player.high_bet_ = player_bets[player.order_]
                        #if players_in_game[order-1] == 0:
                            #print()

                        print("GECTI")
                        for uname in self.player_dict_:
                            msg = PokerMessage(POKER_MESSAGE_TYPE_UPDATE, username = name, chips = (TABLE_BET-bets_on_table), total_bet = TABLE_BET)
                            msg_bin = pickle.dumps(msg)
                            player = self.player_dict_[uname]
                            player.socket_.send(msg_bin)
                    else:
                        i = i + 1
                if i > self.PLAYER_COUNT-1 : 
                    check_high_bets = False
                i = 0
            player_bets.clear()

        fold_winner = ""
        won = True
        for uname in self.player_dict_:
            won = True
            player = self.player_dict_[uname]
                
            for other_player_name in self.player_dict_:
                other_player = self.player_dict_[other_player_name]
                if uname != other_player_name:
                    if other_player.folded_ == False:
                        won = False
            if won :
                fold_winner = player.name_
        if fold_winner != "":
            print("Player \"" + fold_winner + "\" has won")
        # check hands
        else:
          cards = []
          for uname in self.player_dict_:
                  player = self.player_dict_[uname]
                  cards.append(player.cards_[0])
                  cards.append(player.cards_[1])

          for x in range(5):
              cards.append(cards_on_table[x])
          winner = game_utils.compare_players(self.TOTAL_PLAYERS, cards)

          for uname in self.player_dict_:
              player = self.player_dict_[uname]
              if winner == player.order_:
                  print("Player \"" + uname + "\" has won! The prize is "+ str(TABLE_BET) +"!")
                  player.chips_ = player.chips_+TABLE_BET

          print("winner:" + str(winner))
          self.TOTAL_PLAYERS = 0

        
        # playing


        cards_on_table.clear()
        self.deck_ = game_utils.get_deck(shuffle_deck=True)
        self.CAN_START_GAME = True
        self.is_started_ = False
        self.bring_new_players()
        print("Game has more than 2 players. You can start the game.")



        self.TOTAL_PLAYERS = len(self.player_order_list_)
                #print(PLAYER_COUNT)
        #self.start_game()


class GameServer(object):
    def __init__(self, host, port, uname, targetport):
        ip  = socket.gethostbyname(socket.gethostname())
        HOST = ip
        #host = "127.0.0.1"
        print("host: " + HOST)
        self.host_ = host
        self.port_ = port
        self.targetport_ = targetport
        self.uname_ = uname
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.sock.bind((self.host_, self.port_))
            print(host)
        except OSError as osErr:
            if osErr.errno == 99:
                print(
                    "[ERROR]: Cannot assign requested address. Make sure that the provided address is correct.")
                sys.exit(1)
        self.sock.settimeout(.3)
        self.broadcast_listener_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.broadcast_listener_sock.bind(('', self.port_))
        except OSError as osErr:
            if osErr.errno == 99:
                print(
                    "[ERROR]: Cannot assign requested address. Make sure that the provided address is correct.")
                sys.exit(1)

        self.running_ = False
        self.main_thread_ = None
        self.bcast_listener_thread_ = None
        self.game_dict_ = {}
        self.user_dict_ = {}
        self.player_dict_ = {}
        self.spectator_dict_ = {}
        self.broadcast_period_ = 60

    def start(self):
        self.stop()
        print("[INFO]: Launching gameserver listener...")
        self.running_ = True
        self.bcast_listener_thread_ = threading.Thread(
            target=self.bcast_listener)
        self.bcast_listener_thread_.start()
        self.main_thread_ = threading.Thread(target=self.listen)
        self.main_thread_.start()
        self.broadcast()

    def stop(self):
        if (self.running_ and self.main_thread_ is not None and self.main_thread_.is_alive()):
            print("[INFO]: Halting gameserver and broadcast listener...")
            self.running_ = False
            self.main_thread_.join()
            self.main_thread_ = None
            self.bcast_listener_thread_.join()
            self.bcast_listener_thread_ = None



    ###################################################################
    # Change to zeroconf broadcast
    def broadcast(self):
        print("[INFO]: Broadcasting...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        announce_message = self.construct_message(POKER_MESSAGE_TYPE_ANNOUNCE)

        # for i in range(3):
        sock.sendto(announce_message, ('<broadcast>', self.port_))
        sock.sendto(announce_message, ('127.0.0.1', self.port_))
        # time.sleep(1)
        thr = threading.Timer(self.broadcast_period_, self.broadcast)
        thr.setDaemon(True)
        thr.start()

    def bcast_listener(self):
        print("[INFO]: Broadcast listener is started.")
        self.broadcast_listener_sock.setblocking(0)
        while self.running_:
            try:
                result = select.select(
                    [self.broadcast_listener_sock], [], [], 1)
                if result[0]:
                    (msg, address) = self.broadcast_listener_sock.recvfrom(SIZE)
                    peer_ip = address[0]
                    peer_port = address[1]
                else:
                    #print("AMK1")
                    continue
            except:
                #print("AMK2")
                pass
            #print("[INFO]: Received broadcast UDP message: ", msg)
            poker_message = self.parse_raw_msg(msg)
            #print("[INFO]: Constructed: ", poker_message)
            if poker_message is False:
                continue
            if peer_ip == self.host_:
                print("Own broadcast, skipping...")
                # continue
            peer_uname = poker_message.username_
            if poker_message.type_ == POKER_MESSAGE_TYPE_CLIENTCAST:
                # self.add_friend(peer_uname, peer_ip, None, None, None)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    try:
                        response = self.construct_message(
                            POKER_MESSAGE_TYPE_ANNOUNCE)
                        s.connect((peer_ip, self.targetport_))
                        print("[INFO]: Sending response to ", peer_uname)
                        s.send(response)
                        print("[INFO]: Message sent!")
                    except ConnectionRefusedError:
                        print("[ERROR]: An error occured while sending the response to [{0}]!".format(
                            peer_uname))
                        print("Connection refused!")
                        pass
                    except ConnectionResetError:
                        print("[ERROR]: An error occured while sending the response to [{0}]!".format(
                            peer_uname))
                        print("Connection reset!")
                        pass
                    except OSError:
                        print("[ERROR]: An error occured while sending the response to [{0}]!".format(
                            peer_uname))

        print("[INFO]: Broadcast listener is halted!")

    def listen(self):
        print("[INFO]: GameServer listener is started.")
        self.sock.listen(5)
        while self.running_:
            try:
                sock, address = self.sock.accept()
            except socket.timeout:
                continue
            print("Connected to ", address)
            sock.settimeout(None)
            threading.Thread(target=self.listen_to_client,
                             args=(sock, address)).start()
        print("[INFO]: GameServer listener is halted!")

    def listen_to_client(self, sock, address):
        print("Started talking to the client @{0}".format(address))
        got_conn = True

        while got_conn:
            # try:
            #print("WAITING" + str(address))
            data = sock.recv(SIZE)
            #print("RECEIVED" + str(address))
            #print("BEKLENEN ADRES @{0}".format(address))
            #print(data)
            if not data:
                #print("ADRES KAPANDI @{0}".format(address))
                print("NEDEN")
                return
            #print("received {} from {}".format(data, address))
            client_msg = self.parse_raw_msg(data)
            #print("Constructed poker message: {}".format(client_msg))
            # x1, x2, and x3 are g, p, and B respectively if the msg_type is init
            # x1, x2, and x3 are B, msg, and None respectivley if the msg_type is message
            if client_msg.type_ == POKER_MESSAGE_TYPE_INIT:
                player = self.add_user(client_msg, address[0])
                if player is False:
                    sock.close()
                    return
                # player.socket_ = sock
                response_message = self.construct_message(
                    POKER_MESSAGE_TYPE_INIT_RESPONSE, player.A_)
                sock.sendall(response_message)
            elif client_msg.type_ == POKER_MESSAGE_TYPE_PLAY:
                player = self.add_player(client_msg, address[0])
                # player was already added so fetch it
                if player is False:
                    print("Player {} not found.".format(player))
                    sock.close()
                    return
                player.socket_ = sock
                game = self.get_available_game()
                game.add_player(player)
                got_conn = False

            elif client_msg.type_ == POKER_MESSAGE_TYPE_SPEC:
                player = self.add_user(client_msg, address[0])
                if player is False:
                    sock.close()
                    return
                # player.socket_ = sock
                response_message = self.construct_message(
                    POKER_MESSAGE_TYPE_INIT_RESPONSE, player.A_)
                sock.sendall(response_message)

            elif client_msg.type_ == POKER_MESSAGE_TYPE_SIT:
                player = self.add_player(client_msg, address[0])
                player.spectating_ = True
                # player was already added so fetch it
                if player is False:
                    print("Player {} not found.".format(player))
                    sock.close()
                    
                    return
                player.socket_ = sock
                game = self.get_available_game()
                game.add_player(player)
                got_conn = False

        print("INIT COMPLETE")

    def add_user(self, client_message: PokerMessage, ip) -> Player or bool:
        if client_message.username_ in [None, ""]:
            return False
        key = str(ip + "-" + client_message.username_)
        if key in self.user_dict_:
            return self.user_dict_[key]
        if client_message.spectating_ :
            user = Player(client_message.username_, ip,
                      client_message.g_, client_message.p_, client_message.A_, client_message.spectating_)

        else:
            user = Player(client_message.username_, ip,
                      client_message.g_, client_message.p_, client_message.A_, False)
        self.user_dict_[key] = user
        return user

    def add_player(self, client_message: PokerMessage, ip) -> Player or bool:
        if client_message.username_ in [None, ""]:
            return False
        key = str(ip + "-" + client_message.username_)
        if key in self.player_dict_:
            print("[WARNING]: {}-{} is in player list already.".format(ip,
                                                                       client_message.username_))
            return False
        if key in self.spectator_dict_:
            print("[WARNING]: {}-{} is in spectator list already. Cannot play.".format(ip,
                                                                                       client_message.username_))
            return False

        if key in self.user_dict_ and client_message.spectating_:
            print("hspecteeee")
            self.spectator_dict_[key] = self.user_dict_[key]
            return self.spectator_dict_[key]

        elif key in self.user_dict_:
            print("hey")
            self.player_dict_[key] = self.user_dict_[key]
            return self.player_dict_[key]
        # player = Player(client_message.username_, ip,
        #                 client_message.g_, client_message.p_, client_message.A_)
        # self.player_dict_[str(ip + "-" + client_message.username_)] = player
        # return player
        return False

    def construct_message(self, message_type: str, data=None) -> bytes:
        # TODO Construct a status message of the table
        if message_type == POKER_MESSAGE_TYPE_INIT_RESPONSE:
            message = PokerMessage(
                message_type, None, None, None, None, data)  # data is A
        else:
            message = PokerMessage(message_type, data=data)
        return pickle.dumps(message)
        # ELIMINATE THE FOLLOWING
        # payload = "[POKERSERVER,"
        # payload = "[" + self.uname_ + ", " + self.host_ + ", " + message_type
        # if message_type == MESSAGE_TYPE_MESSAGE:
        #     payload += ", " + str(encrypt_message(message, friend.key))
        #     payload += ", " + str(friend.A)
        # elif message_type == MESSAGE_TYPE_INIT:
        #     payload += ", " + str(friend.g)
        #     payload += ", " + str(friend.p)
        #     payload += ", " + str(friend.A)
        # payload += "]"
        # return payload.encode('ascii')

    def parse_raw_msg(self, payload: bytes) -> PokerMessage:
        return pickle.loads(payload)

    def get_available_game(self):
        for table_id in self.game_dict_:
            if self.game_dict_[table_id].seat_available():
                return self.game_dict_[table_id]
        game = Game(len(self.game_dict_))
        self.game_dict_[len(self.game_dict_)] = game
        return game

    def print_friends(self):
        print("\n[INFO] Connected Friends: ")
        # for friend in self.friend_list_:
        #     print("[{0}]".format(friend))
        print()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--host", type=str, default='')
    parser.add_argument("-p", "--port", type=int, default=PORT)
    parser.add_argument("-u", "--uname", type=str, default='azad')
    parser.add_argument("-tp", "--targetport", type=str, default='12346')
    args = vars(parser.parse_args())

    host, port, uname, tport = args['host'], args['port'], args['uname'], int(args['targetport'])

    
    
    gameserver = GameServer(host, port, uname, tport)
    gameserver.start()
   
