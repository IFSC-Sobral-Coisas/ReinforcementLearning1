# Exercício 4.9
import attr
import math
import random

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
    pi = attr.ib(factory=Action)

    def add_action(self, a:Action):
        self.actions.append(a)

    def initialize(self):
        'escolhe uma ação aleatoriamente'
        self.pi = random.choice(self.actions)

class Solver:
    N = 1
    T = 100
    Theta = 1e-3
    Ph = 0.25

    def __init__(self, **args):
        '''Parâmetors:
        N:int = capital inicial
        T:int = capital a ser obtido'''
        self.N = args.get('N', Solver.N)
        self.T = args.get('T', Solver.T)
        self._ph = args.get('ph', Solver.Ph)
        self.__init_states()

    def __init_states(self):
        self.states = {}
        #Cria estados que vão de 0 até 100
        for n in range(self.T+1):
            self.states[n] = State(n)
            for m in range(min(n, self.T-n)):
                self.states[n].add_action(Action(1+m, 0))
        self.states[0].v = 0
        self.states[self.T].v = 0

    def evaluate(self, s:State, a:Action):
        'Calcula o valor do estado s se for seguida a ação a'
        # Para cada estado (n: capital, s: estado)
        total = s.n+a.n # quanto fica o capital se ganhar esta aposta
        r = total == self.T # recompensa = 1 se chegar ao total almejado
        v = self._ph * (r + self.states[total].v) + (1 - self._ph) * self.states[s.n-a.n].v
        return v

    def solve(self):
        # 1. Value evaluation
        delta = self.Theta+1
        while delta >= self.Theta:
            delta = 0
            # para cada estado (n: capital, s: estado)
            for n,s in self.states.items():
                if s.n == self.T or s.n == 0: continue
                v = s.v # valor atual do estado
                s.v = 0
                s.pi = max(s.actions, key=lambda a: self.evaluate(s, a))
                s.v = self.evaluate(s, s.pi) # calcula o valor do estado com esta ação
                delta = max(delta, abs(v-s.v)) # atualiza o delta, que é a variação de ganho no valor


if __name__ == '__main__':
    p = Solver()
    p.solve()
    for n,s in p.states.items():
        print('%s %.2f %s' % (n, s.v, s.pi.n))