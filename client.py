import socket
import struct
import time
import argparse
from random import randint
from random import randrange
import pyDes
from math import ceil, sqrt
import base64
import pickle
import threading
import sys
import time

LIMIT = 999999999
SECRET_KEY_MAX_NUMBER = 99999
# CONSTANTS
POKER_MESSAGE_TYPE_INIT = "init"
POKER_MESSAGE_TYPE_PLAY = "play"
POKER_MESSAGE_TYPE_FOLD = "fold"
POKER_MESSAGE_TYPE_WATCH = "watch"
POKER_MESSAGE_TYPE_UPDATE = "update"
POKER_MESSAGE_TYPE_INVALID_BET = "invalid-bet"
POKER_MESSAGE_TYPE_SPEC = "spectator"
POKER_MESSAGE_TYPE_SIT = "spectator-sit"
POKER_MESSAGE_TYPE_VALID_BET = "valid-bet"
POKER_MESSAGE_TYPE_TABLE = "table"
POKER_MESSAGE_TYPE_TURN = "turn"
POKER_MESSAGE_TYPE_CARDS = "cards"
POKER_MESSAGE_TYPE_CHIPS = "chips"
POKER_MESSAGE_TYPE_INIT_RESPONSE = "init-response"
# Server is announcing that it is serving a poker game
POKER_MESSAGE_TYPE_ANNOUNCE = "announce"
# A message type that the clients broadcast to find game servers available
POKER_MESSAGE_TYPE_CLIENTCAST = "clientcast"

GAME_STARTED = False


class PokerMessage(object):
    def __init__(self, _type, username: str = None, data=None, g: int = None, p: int = None, A: int = None, table: list = None, chips: int = None, 
            order: int = None, total_bet: int=None, high_bet: int=None, spectating:bool=None):
        self.type_ = _type
        self.username_ = username
        self.data_ = data
        self.g_ = g
        self.p_ = p
        self.A_ = A
        self.table_ = table
        self.chips_ = chips
        self.order_ = order
        self.total_bet_ = total_bet
        self.high_bet_ = high_bet
        self.spectating_ = spectating

    def __str__(self):
        return "Type: {}, Data: {}, username: {}, g-p-A: {}-{}-{}, table: {},chips:{}, order: {}".format(
            self.type_, self.data_, self.username_, self.g_, self.p_, self.A_, self.table_, self.chips_, self.order_)


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


class Player(object):
    def __init__(self, name: str, ip: str, g: int = None, p: int = None, B: int = None, order: int = None , chips: int = None, high_bet:int=None, folded: bool=None, spectating: bool=None ): #, cards: list = None):
        self.name_ = name
        self.ip_ = ip
        self.g_ = g if g is not None else generate_prime(LIMIT)
        self.p_ = p if p is not None else generate_prime(LIMIT)
        self.a_ = randrange(SECRET_KEY_MAX_NUMBER)
        self.B_ = B
        self._calculate_A()
        self.cards_ = []
        self.socket_ = None
        self.chips = chips
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


class ClientListener(object):
    def __init__(self, host, port, uname):
        print("Constructing client listener ({}, {})".format(host, port))
        self.host_, self.port_ = host, port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host_addr = None
        self.running_ = True
        self.thr = threading.Thread(target=self.listen)
        self.thr.start()
        binded = False 
        while not binded:
            try:
                self.sock.bind((self.host_, self.port_))
                binded = True
            except OSError as osErr:
                binded = False
                print("Can't bind {}".format(osErr))
                if osErr.errno == 99:
                    print(
                        "[ERROR]: Cannot assign requested address. Make sure that the provided address is correct.")
                    # sys.exit(1)
                time.sleep(1)
        self.sock.settimeout(.3)

    def listen(self):
        print("[INFO]: GameServer listener is started.")
        self.sock.listen(5)
        while self.running_:
            try:
                sock, address = self.sock.accept()
            except socket.timeout:
                continue
            except Exception as ex:
                print("exception while accepting ", ex)
            print("Connected to ", address)
            while True:
                data = sock.recv(1024)
                if not data:
                    print("no data")
                    break 
                server_msg = pickle.loads(data)
                print("Server message: {}".format(server_msg))
                self.host_addr = address[0]

    def close(self):
        self.running_ = False
        self.sock.close()

def Main(uname, host):

    global GAME_STARTED

    #host = '127.0.0.1'
    #host = '192.168.1.42'
    port = 12345
    g = generate_prime(LIMIT)
    p = generate_prime(LIMIT)
    a = randrange(SECRET_KEY_MAX_NUMBER)
    A = g ** a % p
    cards = []

    print("g: {}, p: {}, A: {}".format(g, p, A))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print("Do you want to play or spectate?")
    print("Type \"p\" to play, \"s\" to spectate")
    ask_type = input()
    if ask_type == "p":
        try:
            msg = PokerMessage(POKER_MESSAGE_TYPE_INIT, username=uname, g=g, p=p, A=A)
            s.connect((host, port))
            data = pickle.dumps(msg)
            s.send(data)
            data = s.recv(1024)
            #print(data)
            if not data or len(data) == 0:
                print("Empty message")
                return
            #print("received: ", data)
            c_msg = pickle.loads(data)
            #print("constructed: ", c_msg)
            key = c_msg.A_ ** a % p
            print("Key is {}".format(key))
            priv_data = "encrypt me"
            encrypted_data = encrypt_message(priv_data, key)
            msg = PokerMessage(POKER_MESSAGE_TYPE_PLAY,
                               username=uname, data=encrypted_data)
            s.send(pickle.dumps(msg))
            # get cards for hand
            data = s.recv(1024)
            #print("Received: ", data)
            print('data: ', data)
            decrypted = decrypt_message(data, key)
            print('ddata: ', decrypted)
            c_msg = pickle.loads(decrypted)
            print("des: ", c_msg)
            #print("constructed: ", c_msg)
            
            if c_msg.key_ == key:
                cards = c_msg.table_
                chips = c_msg.chips_
                order = c_msg.order_
                print("Your Cards are : " + str(cards))
                print("Your current chips: " + str(chips))
                #player : Player
                print("Your seat order: " + str(order))
            #get cards on table for opening round
            data = s.recv(1024)
            #print("Received: ", data)
            c_msg = pickle.loads(data)
            #print("constructed: ", c_msg)
            cards_on_table = c_msg.table_
            print("Cards on table are : " + str(cards_on_table))

            GAME_STARTED = True
            last_bet = 0

            # round 1
            while(GAME_STARTED):
                data = s.recv(1024)
                if data:
                    try:
                        c_msg = pickle.loads(data)
                    except:
                        decrypted = decrypt_message(data, key)
                        print('ddata: ', decrypted)
                        c_msg = pickle.loads(decrypted)

                    #print("constructed: ", c_msg)
                    if c_msg.type_ == POKER_MESSAGE_TYPE_TURN:
                        print("Place your bet. Type \"fold\" to fold.")

                        user_input = input()
                        if user_input == "fold":
                            msg = PokerMessage(POKER_MESSAGE_TYPE_FOLD,
                                       username=uname, data=encrypted_data, order=order)
                            s.send(pickle.dumps(msg))
                        elif int(user_input) > chips:
                            msg = PokerMessage(POKER_MESSAGE_TYPE_INVALID_BET,
                                       username=uname, data=encrypted_data, order=order)
                            s.send(pickle.dumps(msg))
                            print("You do not have enough chips for that bet. Your max bet can be " + str(chips) + ".")
                        else:
                            check_if_int = True
                            while check_if_int:
                                try:
                                    bet = int(user_input)
                                    msg = PokerMessage(POKER_MESSAGE_TYPE_TURN,
                                       username=uname, data=encrypted_data, chips=bet, order = order)
                                    s.send(pickle.dumps(msg))

                                    check_if_int = False
                                    print("yolladı")
                                except:
                                    print("Please enter an integer number to bet")
                                    check_if_int = False
                    elif c_msg.type_ == POKER_MESSAGE_TYPE_UPDATE:
                        print("Player " + c_msg.username_  + " has placed bet: " + str(c_msg.chips_) + ". Total bet on table is: " + str(c_msg.total_bet_) + ".")
                    elif c_msg.type_ == POKER_MESSAGE_TYPE_INVALID_BET:
                        print("Your bet is invalid, please bet at least \"" + str(c_msg.high_bet_ - c_msg.chips_) + "\" more to match the high bet, or fold.")
                    elif c_msg.type_ == POKER_MESSAGE_TYPE_VALID_BET:
                        chips = chips - c_msg.chips_
                    elif c_msg.type_ == POKER_MESSAGE_TYPE_FOLD:
                        folded_name = c_msg.username_
                        print("Player \"" + folded_name + "\" has fold.")
                    elif c_msg.type_ == POKER_MESSAGE_TYPE_TABLE:
                        cards_on_table.append(c_msg.table_)
                        print("Cards on table are : " + str(cards_on_table))
                        print("Your current chips : " + str(chips))
                    elif c_msg.type_ == POKER_MESSAGE_TYPE_CARDS:
                        cards_on_table.clear()
                        cards = c_msg.table_
                        chips = c_msg.chips_
                        order = c_msg.order_
                        print("Your Cards are : " + str(cards))
                        print("Your current chips: " + str(chips))
                        #player : Player

                        print("Your seat order: " + str(order))
        except ConnectionRefusedError:
            print("Connection refused!")
            return
        except ConnectionResetError:
            print("Connection reset!")
            return
    elif ask_type == "s":
        msg = PokerMessage(POKER_MESSAGE_TYPE_SPEC, username=uname, g=g, p=p, A=A, spectating=True)
        s.connect((host, port))
        data = pickle.dumps(msg)
        s.send(data)
      
        data = s.recv(1024)
        #print(data)
        if not data or len(data) == 0:
            print("Empty message")
            return
            #print("received: ", data)
        c_msg = pickle.loads(data)
            #print("constructed: ", c_msg)
        key = c_msg.A_ ** a % p
        print("Key is {}".format(key))
        priv_data = "encrypt me"
        encrypted_data = encrypt_message(priv_data, key)
        msg = PokerMessage(POKER_MESSAGE_TYPE_SIT,
                               username=uname, data=encrypted_data, spectating = True)
        s.send(pickle.dumps(msg))
        cards_on_table = []

        while True:

            data = s.recv(1024)
            c_msg = pickle.loads(data)

            if c_msg.type_ == POKER_MESSAGE_TYPE_CARDS:
                pname = c_msg.username_
                cards = c_msg.table_
                print("Player \"" + pname +"\" has cards: " + str(cards))

            elif c_msg.type_ == POKER_MESSAGE_TYPE_TABLE:
                cards_on_table.append(c_msg.table_)
                print("Cards on table are : " + str(cards_on_table))

            elif c_msg.type_ == POKER_MESSAGE_TYPE_UPDATE:
                print("Player " + c_msg.username_  + " has placed bet: " + str(c_msg.chips_) + ". Total bet on table is: " + str(c_msg.total_bet_) + ".")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--uname", type=str)
    parser.add_argument("-s", "--host", type=str)
    parser.add_argument("-ip", "--ip", type=str)
    parser.add_argument("-p", "--port", type=str)
    args = vars(parser.parse_args())
    host, c_ip, uname, port = args['host'], args['ip'], args['uname'], int(args['port'])

    if host == '' or host is None:
        listener = ClientListener(c_ip, port, uname)
        import time 
        while listener.host_addr is None:
            print("Host is not specified. Checking for available game servers..")
            msg = PokerMessage(POKER_MESSAGE_TYPE_CLIENTCAST, username=uname)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            c_msg = pickle.dumps(msg)
            sock.sendto(c_msg, ('<broadcast>', 12345))
            time.sleep(2)
        listener.close()
        host = listener.host_addr

    print("Host ip: ", host)
    #udp_listen = threading.Thread(target=UDPListen)
    #udp_listen.start()
    Main(uname, host)

  