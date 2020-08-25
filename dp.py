import attr
import math
import random

@attr.s
class Action:
    n = attr.ib(default=0)
    q = attr.ib(default=0)
    dstate = attr.ib(default=None)

@attr.s
class State:
    v = attr.ib(default=0)
    actions = attr.ib(factory=list)
    pi = attr.ib(factory=Action)

    def add_action(self, a:Action):
        self.actions.append(a)

    def initialize(self):
        self.pi = random.choice(self.actions)

@attr.s
class Place:
    mreq = attr.ib(default=1)
    mret = attr.ib(default=1)
    states = attr.ib(factory=dict)
    lim = attr.ib(default=20)

    def _poisson(self, m, n):
        return math.exp(-m)*m**n/math.factorial(n)

    def preq(self, n):
        return self._poisson(self.mreq, n)

    def pret(self, n):
        return self._poisson(self.mret, n)

    def prob(self, n):
        return self._poisson(self.mret + self.mreq, n)

    def probability(self, n:int):
        p = 0
        for req in range(self.lim):
            ret = n + req
            print(req,ret, req+ret)
            p += self.prob(req + ret)
        return p

class Solver:
    N = 20
    p1 = Place(3,3, lim=20)
    p2 = Place(2,4, lim=20)
    r = 10
    cost = 2
    gamma = 0.9
    Theta = 0.1

    def __init__(self, **args):
        self.N = args.get('N', Solver.N)
        self.p1 = args.get('p1', Solver.p1)
        self.p2 = args.get('p2', Solver.p2)
        self.r = args.get('r', Solver.r)
        self.cost = args.get('cost', Solver.cost)
        self.gamma = args.get('gamma', Solver.gamma)
        self.__init_states()

    def comb(self,n):
        r = set()
        for n1 in range(n+1):
            for n2 in range(n+1-n1):
                p1 = (n1,n2)
                if not p1 in r:
                    r.add(p1)
                    yield p1

    def __init_states(self):
        self.states = {}
        #Cria estados que vão de (0,0) até (N1,N2)
        # Soma de carros em ambos lugares (i.e: N1+N2) deve ser N
        for n in self.comb(self.N):
            self.states[n] = State()
            self.states[n].add_action(Action(0, 1, n))
            # Ações que levam carros do lugar 1 para o 2
            for k in range(min(n[0], 5)): 
                k = 1 + k # incrementa k, pois k vai de 0 até -1+min(n[0], 5)
                a = Action(k, 0, (n[0] - k, min(self.N, n[1] + k)))
                self.states[n].add_action(a)
            # Ações que levam carros do lugar 2 para o 1
            for k in range(min(n[1],5)):
                k = 1+k
                a = Action(k, 0, (min(self.N,n[0]+k), n[1]-k))
                self.states[n].add_action(a)

        # for n in range(self.N+1):
        #     self.states[(n,self.N-n)] = State()
        # self.states[n].add_action(Action(0, 1, n))
        # # Ações que levam carros do lugar 1 para o 2
        # for k in range(min(n1, 5)):
        #     k = 1 + k
        #     a = Action(k, 0, (n1 - k, n2 + k))
        #     self.states[n].add_action(a)
        # # Cria as ações possíveis em cada estado
        # for n,s in self.states.items():
        #     n1,n2 = n
        #     # Ação que não move carros inicialmente com prob. 1
        #     self.states[n].add_action(Action(0,1,n))
        #     # Ações que levam carros do lugar 1 para o 2
        #     for k in range(min(n1,5)):
        #         k = 1+k
        #         a = Action(k, 0, (n1-k, n2+k))
        #         self.states[n].add_action(a)
        #     # Ações que levam carros do lugar 2 para o 1
        #     for k in range(min(n2,5)):
        #         k = 1+k
        #         a = Action(k, 0, (n1+k, n2-k))
        #         self.states[n].add_action(a)

    def requested(self, s, a:Action):
        r = -a.n*self.cost

    def evaluate(self, s:State, a:Action):
        n1 = a.dstate
        v = 0
        for n2, s2 in self.states.items():
            dn1 = n2[0] - n1[0]
            dn2 = n2[1] - n1[1]
            ck1 = set()
            for rq1 in range(n1[0]):
                rt1 = max(0,dn1 + rq1)
                if rt1 in ck1: continue
                ck1.add(rt1)
                ck2 = set()
                for rq2 in range(n1[1]):
                    rt2 = max(0, dn2 + rq2)
                    if rt2 in ck2: continue
                    ck2.add(rt2)
                    r = -a.n * self.cost + (rq1 + rq2) * self.r + self.gamma * v
                    v += self.p1.preq(rq1) * self.p1.pret(rt1) * self.p2.preq(rq2) * self.p2.pret(rt2) * r
        return v

    def solve(self):
        stable = False
        for n,s in self.states.items(): s.initialize()
        while not stable:
            # 2. Policy evaluation
            delta = self.Theta+1
            while delta >= self.Theta:
                delta = 0
                for n,s in self.states.items():
                    v = s.v
                    s.v = 0
                    a = s.pi
                    s.v = self.evaluate(s, a)
                    delta = max(delta, abs(v-s.v))
            # 3. policy improvement
            stable = True
            for n,s in self.states.items():
                old_a = s.pi
                s.pi = max(s.actions, key=lambda a: self.evaluate(s, a))
                if old_a != s.pi and delta > 0: stable = False


if __name__ == '__main__':
    p = Solver()
    p.solve()
    for n,s in p.states.items():
        print('%s %.2f %s' % (n, s.v, s.pi))



