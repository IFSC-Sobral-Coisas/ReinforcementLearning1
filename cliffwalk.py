from gridworld import GridWorld,Direction
from sarsa import State,Action,Sarsa,QLearn,ExpSarsa
from typing import Tuple

class CliffWalk(GridWorld):

    Rows = 4
    Columns = 12
    Start = (0,3)
    Goal = (11,3)
    Cliff = 3 # Linha do abismo

    def __init__(self, **args):
        args['start'] = args.get('start', CliffWalk.Start)
        args['goal'] = args.get('goal', CliffWalk.Goal)
        GridWorld.__init__(self, CliffWalk.Columns, CliffWalk.Rows, **args)

    def __in_cliff__(self, s:State)->bool:
        col,row = s.n
        return row == CliffWalk.Cliff and s != self.start and s != self.goal

    def evaluate(self, s:State, a:Action) ->Tuple[float,State]:
        r, s = GridWorld.evaluate(self, s, a)
        if self.__in_cliff__(s):
            r = -100
            s = self.start
        return r,s

if __name__ == '__main__':
    model = CliffWalk()
    p = ExpSarsa(model, alfa=0.5)
    episode = 0
    total = 0
    while episode < 1000:
        steps = p.estimate(model.start)
        total += steps
        episode += 1
        # print(episode, steps, total)

    s = model.start
    for s in model.episode(s):
        m = s.pi.n
        print('%s %s' % (s.n, m.name))

    for s in model.states.values():
        print(s.n, end=' ')
        for a,p in s.policy_dist:
            print('%s %.2f %.2f' % (a.n.name, a.q, p), end=', ')
        print('')
    # for n,s in model.states.items():
    #     print('%s %s' % (n, s.pi.n))

