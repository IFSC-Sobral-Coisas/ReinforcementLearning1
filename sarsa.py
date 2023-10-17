# Exercício 6.8
import attr
import random
from typing import Tuple,List
from functools import reduce

@attr.s
class Action:
    '''Uma ação: especifica uma aposta para n unidades monetárias e possui um valor q'''
    n = attr.ib(default=0)
    q = attr.ib(default=0)
    count = attr.ib(default=0) # quantas vezes foi selecionada esta ação

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

    def get_action(self, at:Action):
        r = [a for a in self.actions if a.n == at.n]
        if not r:
            return at.__class__()
        return r[0]

    @property
    def amax(self)->Action:
        amax = max(self.actions, key=lambda a: a.q)
        lmax = [a for a in self.actions if a.q == amax.q]
        # lmax = filter(lambda a: a.q == amax.q, self.actions)
        return random.choice(lmax)

    @property
    def pi(self)->Action:
        if random.random() <= self.e:
            a = random.choice(self.actions)
        else:
            # identifica ação com maior valor
            a = self.amax
        a.count += 1
        return a

    def initialize(self):
        'escolhe uma ação aleatoriamente'
        for a in self.actions:
            a.q = 0
            a.count = 0
            # if self.final: a.q = 0
            # else: a.q = random.random()

    @property
    def total(self)->int:
        return reduce(lambda x,a: x+a.count, self.actions, 0)

    @property
    def policy_dist(self)->List[Tuple[float,Action]]:
        t = self.total
        if t > 0:
            return [(a, a.count/t) for a in self.actions]
        else:
            p = 1/len(self.actions)
            return [(a, p) for a in self.actions]


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

    def next(self, s:State)->State:
        raise NotImplementedError('classe abstrata')

    def episode(self, s:State)->State:
        while not s.final:
            yield s
            s = self.next(s)
        #raise StopIteration('no more states')

class Sarsa:

    Alfa = 0.1
    Gamma = 1 # sem desconto

    def __init__(self, model:Model, **args):
        self.model = model
        self.alfa = args.get('alfa', Sarsa.Alfa)
        self.gamma = args.get('gamma', Sarsa.Gamma)
        self.model.initialize()

    def next_value(self, s: State)->float:
        return s.pi.q

    def evaluate(self, s:State):
        at = s.pi
        r, stt = self.model.evaluate(s, at)
        at.q += self.alfa * (r + self.gamma * self.next_value(stt) - at.q)
        # print(s.n, at.n, at.q, r, stt.n, att.n, att.q)
        s = stt
        at = s.pi
        return s,at

    def estimate(self, s:State)->int:
        # at = s.pi
        steps = 0
        while not s.final:
            s,a = self.evaluate(s)
            # r,stt = self.model.evaluate(s, at)
            # at.q += self.alfa*(r + self.gamma*self.next_value(stt) - at.q)
            # # print(s.n, at.n, at.q, r, stt.n, att.n, att.q)
            # s = stt
            # at = s.pi
            steps += 1
        return steps

class QLearn(Sarsa):

    def next_value(self, s: State)->float:
        return s.amax.q

class ExpSarsa(Sarsa):

    def next_value(self, s: State)->float:
        # valor esperado do valor da próxima ação
        soma = s.total
        if soma > 0:
            return reduce(lambda x,a: x+a.q*a.count, s.actions, 0)/soma
        return s.amax.q

@attr.s
class DoubleAction:
    '''Uma ação: especifica uma aposta para n unidades monetárias e possui um valor q'''
    n = attr.ib(default=0)
    q1 = attr.ib(default=0)
    q2 = attr.ib(default=0)
    count = attr.ib(default=0) # quantas vezes foi selecionada esta ação

    @property
    def q(self):
        return self.q1 + self.q2

    @q.setter
    def q(self, n):
        self.q1 = n
        self.q2 = n

class DoubleSarsa(Sarsa):

    def next_value(self, s:State, q:str):
        return getattr(s.pi,q)

    def evaluate(self, s:State):
        at = s.pi
        r, stt = self.model.evaluate(s, at)
        if random.random() > 0.5:
            at.q1 += self.alfa * (r + self.gamma * self.next_value(stt, 'q2') - at.q1)
        else:
            at.q2 += self.alfa * (r + self.gamma * self.next_value(stt, 'q1') - at.q2)
        att = s.pi
        # print(s.n, r, at.q, at, stt.n, att.n, att.q)
        s = stt
        # at = s.pi
        return s,att

class DoubleQLearn(DoubleSarsa):

    def __getmax(self, s:State, q:str):
        qq = q == 'q1' and 'q2' or 'q1'
        amax = max(s.actions, key=lambda a: getattr(a, qq))
        lmax = [a for a in s.actions if a.q == amax.q]
        return random.choice(lmax)

    def next_value(self, s:State, q:str):
        # lmax = filter(lambda a: a.q == amax.q, self.actions)
        amax = self.__getmax(s, q)
        # print(f'{amax}, {s}, {q}')
        return getattr(amax,q)

class DoubleExpSarsa(DoubleSarsa):

    def next_value(self, s: State, q:str)->float:
        # valor esperado do valor da próxima ação
        soma = s.total
        if soma > 0:
            return reduce(lambda x,a: x+getattr(a,q)*a.count, s.actions, 0)/soma
        return getattr(s.amax,q)
