# Exercício 6.8
import attr
import math
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
        return max(self.actions, key=lambda a: a.q)

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

# Ex. 6.5 - windy gridworld
class Windy(Model):

    Rows = 7
    Columns = 10
    Start = (0, 3)
    Goal = (7, 3)
    Wind = (0,0,0,1,1,1,2,2,1,0)
    Up = 0
    Down = 1
    Left = 2
    Right = 3

    Dirs = {Up: (0,-1), Down: (0,1), Right: (1,0), Left:(-1,0)}

    def __init__(self, **args):
        self._start = args.get('start', Windy.Start)
        self._goal = args.get('goal', Windy.Goal)
        self.wind = args.get('wind', Windy.Wind)
        Model.__init__(self, **args)

    def __initialize__(self):
        for col in range(Windy.Columns):
            for row in range(Windy.Rows):
                pos = (col, row)
                s = State(pos)
                if col > 0:
                    s.add_action(Action(Windy.Left))
                if col < Windy.Columns-1:
                    s.add_action(Action(Windy.Right))
                if row > 0:
                    s.add_action(Action(Windy.Up))
                if row < Windy.Rows-1:
                    s.add_action(Action(Windy.Down))
                self.states[pos] = s

        self.goal.final = True

    def __wind__(self, col):
        return self.wind[col]

    def __move__(self, s:State, a:Action)->Tuple[int,int]:
        col, row = s.n
        dc, dr = self.Dirs[a.n]
        col += dc
        row += dr
        row = min(Windy.Rows-1, max(0, row - self.__wind__(col)))
        return col,row

    def evaluate(self, s:State, a:Action)->Tuple[float,State]:
        col, row = self.__move__(s, a)
        stt = self.states[(col,row)]
        if stt.final: r = 0
        else: r = -1

        return r,stt

    @property
    def start(self):
        return self.states[self._start]

    @property
    def goal(self):
        return self.states[self._goal]

    def next(self, s: State=Start) -> State:
        a = s.pi
        col,row = self.__move__(s, a)
        return self.states[(col,row)]

class Windy2(Windy):
    'Exercicio 6.9'

    UpRight = 4
    UpLeft = 5
    DownRight = 6
    DownLeft = 7
    Dirs = {UpRight:(1,-1), UpLeft:(-1,-1), DownRight:(1,1), DownLeft:(-1,1)}
    Dirs.update(Windy.Dirs)

    def __init__(self, **args):
        Windy.__init__(self, **args)

    def __initialize__(self):
        Windy.__initialize__(self)
        for s in self.states.values():
            col,row = s.n
            if col > 0:
                if row > 0:
                    s.add_action(Action(Windy2.UpLeft))
                if row < Windy.Rows-1:
                    s.add_action(Action(Windy2.DownLeft))
            if col < Windy.Columns-1:
                if row > 0:
                    s.add_action(Action(Windy2.UpRight))
                if row < Windy.Rows-1:
                    s.add_action(Action(Windy2.DownRight))

class Windy3(Windy2):
    'Exercicio 6.9 2a parte'

    Nope = 8
    Dirs = {Nope:(0,0)}
    Dirs.update(Windy2.Dirs)

    def __initialize__(self):
        Windy2.__initialize__(self)
        for s in self.states.values():
            col,row = s.n
            s.add_action(Action(Windy3.Nope))

class Windy4(Windy):
    'Exercicio 6.9 2a parte'

    def __wind__(self, col: int):
        w = Windy.__wind__(self, col)
        p = random.choice((0,1,2))
        if p == 1: # uma casa acima
            w += 1
        elif p == 2: # uma casa abaixo
            w -= 1
        return w

if __name__ == '__main__':
    model = Windy()
    p = Sarsa(model, alfa=0.5)
    episode = 0
    total = 0
    while episode < 1000:
        steps = p.estimate(model.start)
        total += steps
        episode += 1
        # print(episode, steps, total)

    s = model.start
    while not s.final:
        m = s.pi.n
        if m == model.Up: m = 'up'
        elif m == model.Down: m = 'down'
        elif m == model.Left: m = 'left'
        elif m == model.Right: m = 'right'
        print('%s %s' % (s.n, m))
        s = model.next(s)

    # for n,s in model.states.items():
    #     print('%s %s' % (n, s.pi.n))