import attr
import random

@attr.s
class Action:
    id = attr.ib(default=0)
    s = attr.ib(default=0) # sigma
    r = attr.ib(default=0) # recompensa
    n = attr.ib(default=0) # qtas vezes esta ação foi selecionada
    qn = attr.ib(default=0) # valor estimado

    @property
    def reward(self)->float:
        return random.normalvariate(self.r, self.s)

    def update(self, rn:float):
        self.n += 1
        self.qn += (rn - self.qn)/self.n

class RL0:

    def __init__(self, N:int, e:float=0):
        if N < 2: raise ValueError("N deve ser maior que 1 (ao menos duas ações)")
        if e < 0 or e > 1: raise ValueError('e deve estar no intervalo [0,1]')
        self.actions = [Action(id=x, r=random.normalvariate(0,1), s=1, qn=0) for x in range(N)]
        self.e = e

    def __best_action__(self):
        e = random.random()
        if e >= self.e:
            a_greedy = max(self.actions, key=lambda a: a.qn)
            l = [a for a in self.actions if a.qn == a_greedy.qn]
        else:
            l = self.actions
        return random.choice(l)

    def is_best(self, a:Action)->bool:
        return a.r >= max(map(lambda x: x.r, self.actions))

    def learn(self, steps:int, stepsize:int=10)->dict:
        nbest = {}
        step = 0
        while step < steps:
            a = self.__best_action__()
            if self.is_best(a):
                pos = int(step/stepsize)*stepsize
                try:
                    nbest[pos] += 1
                except:
                    nbest[pos] = 1
            r = a.reward
            a.update(r)
            step += 1
        return nbest


class Testbed:

    def __init__(self, k=10, e=0):
        self.k = k
        self.e = e

    def __init_stats(self, n, stepsize):
        d = {}
        pos = 0
        while pos < n:
            d[pos] = 0
            pos += stepsize
        return d

    def __update_stats(self, stats, res):
        for k,v in res.items():
            stats[k] += v

    def run(self, runs=2000, runlen=1000, stepsize=10):
        stats = self.__init_stats(runlen, stepsize)
        for n in range(runs):
            r = RL0(self.k, self.e)
            res = r.learn(runlen, stepsize)
            self.__update_stats(stats, res)
        for k in stats:
            stats[k] /= runs
            stats[k] /= stepsize
        return stats

if __name__ == '__main__':
    K = 10
    for e in [0.01, 0.1, 0.2]:
        print('running: ', e)
        t = Testbed(K, e)
        res = t.run()
        f = open('run_%.2f.log' % e, 'w')
        for k, v in res.items():
            f.write('%d %.6f\n' % (k, v))
        f.close()
