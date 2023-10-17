# Ex. 6.5 - windy gridworld
import sarsa
from gridworld import GridWorld,Direction
from sarsa import State,Action,Sarsa
from typing import Tuple
import random

class Windy(GridWorld):

    Rows = 7
    Columns = 10
    Start = (0, 3)
    Goal = (7, 3)
    Wind = (0,0,0,1,1,1,2,2,1,0)

    def __init__(self, **args):
        start = args.get('start', Windy.Start)
        goal = args.get('goal', Windy.Goal)
        GridWorld.__init__(self, Windy.Columns, Windy.Rows, start=start, goal=goal, actionclass=sarsa.DoubleAction)
        self.wind = args.get('wind', Windy.Wind)

    def __wind__(self, col):
        return self.wind[col]

    def __move__(self, s:State, a:Action)->Tuple[int,int]:
        col,row = GridWorld.__move__(self,s,a)
        row = min(self.rows-1, max(0, row - self.__wind__(col)))
        return col,row

class Windy2(Windy):
    'Exercicio 6.9'

    def __init__(self, **args):
        args['diagonal']=True
        Windy.__init__(self, **args)

class Windy3(Windy2):
    'Exercicio 6.9 2a parte'

    def __init__(self, **args):
        args['nomove']=True
        Windy2.__init__(self, **args)

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
    p = sarsa.DoubleQLearn(model, alfa=0.5)
    episode = 0
    total = 0
    while episode < 1000:
        steps = p.estimate(model.start)
        total += steps
        episode += 1
        # print(episode, steps, total)

    s = model.start
    passos = 0
    for s in model.episode(s):
        m = s.pi.n
        print('%s %s' % (s.n, m.name))
        passos+= 1

    for n,s in model.states.items():
        print('%s %s' % (n, s.pi.n))

    print(f'{passos} passos')