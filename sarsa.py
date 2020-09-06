# Exercício 6.8
import attr
import random
from typing import Tuple

@attr.s
class Action:
    '''Uma ação: especifica uma aposta para n unidades monetárias e possui um valor q'''
    n = attr.ib(default=0)
    q = attr.ib(default=0)

@attr.s
class State:
    'Um estado: tem um valor, um conjunto de ações, e uma ação dada pela policy'
    n = attr.ib(default=0)
    v = attr.ib(default=0)
    actions = attr.ib(factory=list)
    e = attr.ib(default=0.1)
    final = attr.ib(default=False)

    def add_action(self, a:Action):
        self.actions.append(a)

    @property
    def pi(self)->Action:
        amax = max(self.actions, key=lambda a: a.q)
        lmax = filter(lambda a: a.q == amax.q, self.actions)
        return random.choice(list(lmax))

    @property
    def best(self)->Action:
        if random.random() <= self.e:
            return random.choice(self.actions)
        # identifica ação com maior valor
        return self.pi

    def initialize(self):
        'escolhe uma ação aleatoriamente'
        for a in self.actions:
            a.q = 0
            # if self.final: a.q = 0
            # else: a.q = random.random()

class Model:
    Epsilon = 0.1

    def __init__(self, **args):
        self.states = {}
        epsilon = args.get('e', Model.Epsilon)
        self.__initialize__()
        for s in self.states.values(): s.e = epsilon

    def __initialize__(self):
        raise NotImplementedError('classe abstrata')

    def evaluate(self, s:State, a:Action)->Tuple[float,State]:
        raise NotImplementedError('classe abstrata')

    def initialize(self):
        for s in self.states.values():
            s.initialize()


class Sarsa:

    Alfa = 0.1
    Gamma = 1 # sem desconto

    def __init__(self, model:Model, **args):
        self.model = model
        self.alfa = args.get('alfa', Sarsa.Alfa)
        self.gamma = args.get('gamma', Sarsa.Gamma)
        self.model.initialize()

    def estimate(self, s:State)->int:
        at = s.best
        steps = 0
        while not s.final:
            r,stt = self.model.evaluate(s, at)
            att = stt.best
            at.q += self.alfa*(r + self.gamma*att.q - at.q)
            # print(s.n, at.n, at.q, r, stt.n, att.n, att.q)
            s = stt
            at = att
            steps += 1
        return steps

