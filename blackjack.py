import sys
import attr,random
from enum import Enum
import statistics
from functools import reduce

class Card(Enum):
    Ace = 11
    Um = 1
    Dois = 2
    Tres = 3
    Quatro = 4
    Cinco= 5
    Seis = 6
    Sete = 7
    Oito = 8
    Nove = 9
    Dez = 10
    Valete = 12
    Dama = 13
    Rei = 14

    @staticmethod
    def get_random():
        return Card(random.randint(1,11))

class Baralho:

    def __init__(self):
        self.cards = self.genseq()*4

    def genseq(self):
        return [Card(x+1) for x in range(11)] + [Card.Valete, Card.Dama, Card.Rei]

@attr.s
class State:

    usable_ace = attr.ib(True)
    player_sum = attr.ib(12)
    dealer_visible = attr.ib(Card.Ace)
    val = attr.ib(factory=list)


    def key(self):
        return (self.usable_ace, self.player_sum, self.dealer_visible)

    def value(self):
        return statistics.mean(self.val)

    def add_value(self, val):
        self.val.append(val)

    def as_tuple(self):
        return (self.usable_ace, self.player_sum, self.dealer_visible)

@attr.s
class Player:
    cards = attr.ib(factory=list)

    def add(self, card: Card = None):
        if card == None:
            card = Card.get_random()
        self.cards.append(card)

    def __basic_sum(self):
        others = filter(lambda c: c != Card.Ace, self.cards)
        return reduce(lambda x, y: x + y.value, others, 0)

    def sum(self):
        aces = filter(lambda c: c == Card.Ace, self.cards)
        s = self.__basic_sum()
        for c in aces:
            if 21 - s > 10:
                s += 11
            else:
                s += 1
        return s

    def has_usable_ace(self):
        return Card.Ace in self.cards and self.__basic_sum() < 11

    def last(self):
        return self.cards[-1]


    @staticmethod
    def create():
        p = Player()
        p.add(Card.get_random())
        p.add(Card.get_random())
        return p

class Action(Enum):
    Hit = 1
    Stick = 2

Gamma = 1
b = Baralho()
states = {}
for card in b.genseq():
    if card.value > 11: break
    for usable in (True, False):
        for soma in range(12,22):
            s = State(usable, soma, card)
            states[s.key()] = s


for n in range(500000):
    jogador = Player.create()
    banca = Player.create()

    # sequencia inicial, enquanto jogador tem soma < 12:
    while jogador.sum() < 12:
        jogador.add()
        if banca.sum() < 17: banca.add()

    # gera um episodio
    ep = []
    fim = False
    while not fim:
        curr = State(jogador.has_usable_ace(), jogador.sum(), banca.last())
        if jogador.sum() < 20:
            jogador.add()
            a = Action.Hit
        else:
            a = Action.Stick
        if banca.sum() < 17:
            banca.add()
        s1 = jogador.sum()
        s2 = banca.sum()
        fim = True
        if s1 == 21:
            if s2 == 21: R = 0
            else: R = 1
        elif s1 > 21: R = -1
        elif s2 > 21: R = 1
        else:
            fim = jogador.sum() > 19 and banca.sum() > 16
            R = 0
        ep.append((curr, a, R))

    # calcula os valores dos estados deste episodio
    #print(ep)
    G = 0
    while ep:
        s,a,R = ep.pop()
        G = Gamma*G + R
        if not s in [x[0] for x in ep]:
            states[s.key()].add_value(G)

for s in states.values():
    print(s.as_tuple(), s.value())





