from random import shuffle, randrange
from itertools import combinations 

suits = ['S', 'H', 'C', 'D']
cards = [str(i) for i in range(2, 10)]
cards.extend(['T', 'J', 'Q', 'K', 'A'])


def get_deck(shuffle_deck=True):
    deck = []
    for suit in suits:
        for card in cards:
            deck.append([card, suit])
    if shuffle_deck:
        shuffle(deck)
    return deck


def draw_cards(deck, nbr_of_cards):
    if len(deck) < nbr_of_cards:
        raise Exception(
            "Requested number of cards cannot exceed the size of the deck")
    card_idx = set()
    while len(card_idx) < nbr_of_cards:
        card_idx.add(randrange(len(deck)))
    drawn_cards = []
    for idx in card_idx:
        drawn_cards.append(deck[idx])
    return drawn_cards


def draw_cards_from_deck(deck: list, nbr_of_cards: int):
    if len(deck) < nbr_of_cards:
        raise Exception(
            "Requested number of cards cannot exceed the size of the deck")
    card_idx = set()
    while len(card_idx) < nbr_of_cards:
        card_idx.add(randrange(len(deck)))
    drawn_cards = []
    for idx in card_idx:
        drawn_cards.append(deck[idx])
    for drawn_card in drawn_cards:
        deck.remove(drawn_card)

    return deck, drawn_cards


# Test function that checks the ranking of hands


def compare_players(nbr_of_players, cards):
    deck = get_deck(True)
    #drawn_cards = draw_cards(deck, 5 * nbr_of_players)
    
    table = []
    winner = []
    for x in range(5):
        table.append(cards.pop(nbr_of_players*2))
    for i in range(nbr_of_players):
        current_cards = []
        results = []
        #current_cards = drawn_cards[i * 5: (i+1) * 5]
        current_cards.append(cards.pop(0))
        current_cards.append(cards.pop(0))
        for x in range(5):
            current_cards.append(table[x])
        comb = combinations(current_cards, 5)
        for y in list(comb):
            rank = check_hand_rank(y)
            results.append(rank)
        #results.append(check_hand_rank(drawn_cards[i * 5 : (i+1) * 5]))
        #for res in results:
        #    print(res)
        
        winner.append(results[0])
        for j in range(1, len(results)-1):
            if results[j]["rank"] > winner[i]["rank"]:
                winner[i] = results[j]
            elif results[j]["rank"] == winner[i]["rank"]:
                if results[j]["score"] > winner[i]["score"]:
                    winner[i] = results[j]
        #print(winner[i])
    win_final = winner[0]
    win_player = 0
    for i in range(1, nbr_of_players):
        if winner[i]["rank"] > win_final["rank"]:
            win_final = winner[i]
            win_player = i
    return win_player#winner


def get_hand_rank(hand):
    return ['--23456789TJQKA'.index(n) for n, h in hand]


def get_card_rank(card):
    return '--23456789TJQKA'.index(card)


def royal_straight_flush(hand):
    def royal_straight(hand):
        n = [n for n, h in hand]
        for c in n:
            if c not in ['A', 'K', 'Q', 'J', 'T'] or len(set(n)) != 5:
                return False
        return True
    return royal_straight(hand) and flush(hand)["result"]


def high_card(hand):
    card_rank = ['--23456789TJQKA'.index(n) for n, h in hand]
    card_rank.sort()
    card_rank.reverse()
    return max(card_rank)


def one_pair(hand):
    card_rank = get_hand_rank(hand)
    pair_rank = -1
    for i in range(len(card_rank)):
        if card_rank.count(card_rank[i]) == 2:
            pair_rank = card_rank[i]
            break
    return {"result": len(set(card_rank)) == 4, "rank": pair_rank}


def two_pair(hand):
    s = [n for n, h in hand]
    
    if not (not three_of_a_kind(hand)["result"] != True and len(set(s)) == 3):
    #if (three_of_a_kind(hand) == True and len(set(s)) == 3):
        return {"result": False, "rank": -1}
    card_rank = get_hand_rank(hand)
    card_rank.sort(reverse=True)
    
    rank = 0
    pair_set = set()
    for c in card_rank:
        if card_rank.count(c) == 2 and c not in pair_set:
            rank += c
            pair_set.add(c)
    return {"result": True, "rank": rank}


def three_of_a_kind(hand):
    s = [n for n, h in hand]
    s.sort()
    rank = -1
    status = False
    for i in range(len(s)):
        if s.count(s[i]) >= 3:
            status = True
            rank = get_card_rank(s[i])
            break
    return {"result": status, "rank": rank}


def full_house(hand):
    hand_rank = get_hand_rank(hand)
    #print(hand_rank)
    hand_rank_set = set(hand_rank)
    rank = 0
    threeofakind_result = three_of_a_kind(hand)
    if threeofakind_result["result"] and len(hand_rank_set) == 2:
        for c in hand_rank_set:
            rank += c
        return {"result": True, "rank": rank}
    return {"result": False, "rank": -1}


def flush(hand):
    hand_rank = get_hand_rank(hand)
    s = [h for n, h in hand]
    if len(set(s)) != 1:
        return {"result": False, "rank": -1}
    return {"result": True, "rank": max(hand_rank)}


def straight(hand):
    tocheck_straight = ['--23456789TJQKA'.index(n) for n, h in hand]
    tocheck_straight.sort()
    tocheck_straight.reverse()
    if tocheck_straight == [14, 5, 4, 3, 2]:
        tocheck_straight = [5, 4, 3, 2, 1]
    if (max(tocheck_straight) - min(tocheck_straight) == 4) and (len(set(tocheck_straight)) == 5):
        return {"result": True, "rank": max(tocheck_straight)}
    else:
        return {"result": False, "rank": -1}


def four_of_a_kind(hand):
    hand_rank = get_hand_rank(hand)
    for i in range(len(hand_rank)):
        if hand_rank.count(hand_rank[i]) == 4:
            return {"result": True, "rank": hand_rank[i]}
    return {"result": False, "rank": -1}


def straight_flush(hand):
    straight_result = straight(hand)
    flush_result = flush(hand)
    if straight_result['result'] and flush_result['result']:
        return {"result": True, "rank": straight_result["rank"]}
    else:
        return {"result": False, "rank": -1}


def check_hand_rank(hand):
    if royal_straight_flush(hand):
        return {"rank": 9, "score": -1, "description": "Royal Straight Flush"}
    is_straight_flush = straight_flush(hand)
    if is_straight_flush["result"]:
        return {"rank": 8, "score": is_straight_flush["rank"], "description": "Straight Flush"}
    is_four_of_a_kind = four_of_a_kind(hand)
    if is_four_of_a_kind["result"]:
        return {"rank": 7, "score": is_four_of_a_kind["rank"], "description": "Four of a Kind"}
    is_full_house = full_house(hand)
    if is_full_house["result"]:
        return {"rank": 6, "score": is_full_house["rank"], "description": "Full House"}
    is_flush = flush(hand)
    if is_flush["result"]:
        return {"rank": 5, "score": is_flush["rank"], "description": "Flush"}
    is_straight = straight(hand)
    if is_straight["result"]:
        return {"rank": 4, "score": is_straight["rank"], "description": "Straight"}
    is_three_ofa_kind = three_of_a_kind(hand)
    if is_three_ofa_kind["result"]:
        return {"rank": 3, "score": is_three_ofa_kind["rank"], "description": "Three of a Kind"}
    is_two_pair = two_pair(hand)
    if is_two_pair["result"]:
        return {"rank": 2, "score": is_two_pair["rank"], "description": "Two Pair"}
    is_one_pair = one_pair(hand)
    if is_one_pair["result"]:
        return {"rank": 1, "score": is_one_pair["rank"], "description": "One Pair"}
    return {"rank": 0, "score": high_card(hand), "description": "High Card"}
