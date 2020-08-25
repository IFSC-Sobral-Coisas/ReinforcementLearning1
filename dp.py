import attr
import math
import random

@attr.s
class Action:
    '''Uma ação: especifica uma quantidade de carros movidos, possui um valor q, e a quantidade
    de carros nos lugares (dstate) se aplicada'''
    n = attr.ib(default=0)
    q = attr.ib(default=0)
    dstate = attr.ib(default=None)

@attr.s
class State:
    'Um estado: tem um valor, um conjunto de ações, e uma ação dada pela policy'
    v = attr.ib(default=0)
    actions = attr.ib(factory=list)
    pi = attr.ib(factory=Action)

    def add_action(self, a:Action):
        self.actions.append(a)

    def initialize(self):
        'escolhe uma ação aleatoriamente'
        self.pi = random.choice(self.actions)

@attr.s
class Place:
    'Um lugar onde tem uma loja com carros para alugar'
    mreq = attr.ib(default=1)
    mret = attr.ib(default=1)
    states = attr.ib(factory=dict)
    lim = attr.ib(default=20)

    def _poisson(self, m, n):
        return math.exp(-m)*m**n/math.factorial(n)

    def preq(self, n):
        'Probabilidade de n carros alugados'
        return self._poisson(self.mreq, n)

    def pret(self, n):
        'Probabilidade de n carros devolvidos'
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
        '''Parâmetors:
        N:int = quantidade de carros total
        p1:Place = lugar 1 com suas probabilidades de carros alugados e devolvidos
        p2:Place = lugar 2 com suas probabilidades de carros alugados e devolvidos
        r:float = recompensa para cada carro alugado
        cost:float = custo para mover carro
        gamma:float = fator de decaimento da recompensa'''
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

    def requested(self, s, a:Action):
        r = -a.n*self.cost

    def evaluate(self, s:State, a:Action):
        'Calcula o valor do estado s se for seguida a ação a'
        n1 = a.dstate # estado destino da ação
        v = 0 # valor a calcular
        # Para cada estado (n2: tupla (np1,np2), s2: estado)
        for n2, s2 in self.states.items():
            dn1 = n2[0] - n1[0] # diferença de carros no lugar 1, entre estado atual n1 e destino n2
            dn2 = n2[1] - n1[1] # diferença de carros no lugar 2, entre estado atual n1 e destino n2
            ck1 = set()
            # rq1: carros alugados, e rt1: carros retornados
            for rq1 in range(n1[0]):
                # carros retornados: calculado pela variação de carros observada,
                # e a quantidade de carros alugados. Ex:
                # a) se a variação foi 1, e carros alugados foi 1, então retornados
                # deve ser 2.
                # b) Se variação foi -1 e carros alugados foi 1, retornados deve ser 0.
                rt1 = max(0,dn1 + rq1)
                if rt1 in ck1: continue # se já calculou este valor, ignora
                ck1.add(rt1)
                ck2 = set()
                # faz o mesmo procedimento para a variação de carros no lugar 2
                for rq2 in range(n1[1]):
                    rt2 = max(0, dn2 + rq2)
                    if rt2 in ck2: continue
                    ck2.add(rt2)
                    # recompensa: quanto se ganha com esse balanço de carros movidos e alugados
                    r = -a.n * self.cost + (rq1 + rq2) * self.r + self.gamma * v
                    # valor: pondera a recompensa pela probabilidade de que ocorra
                    # produto das probabilidades de ocorrerem estas quantidades de carros alugados
                    # e devolvidos nos lugares 1 e 2
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
                # para cada estado (n: tupla (n1, n2), s: estado)
                for n,s in self.states.items():
                    v = s.v # valor atual do estado
                    s.v = 0
                    a = s.pi # a ação escolhida pela policy
                    s.v = self.evaluate(s, a) # calcula o valor do estado com esta ação
                    delta = max(delta, abs(v-s.v)) # atualiza o delta, que é a variação de ganho no valor
            # 3. policy improvement
            stable = True
            # para cada estado (n: tupla (n1, n2), s: estado)
            for n,s in self.states.items():
                old_a = s.pi # ação da policy atual para estado "s"
                # avalia cada uma das ações do estado "s", e seleciona
                # aquela que retornou o maior valor. Ela será a nova policy
                s.pi = max(s.actions, key=lambda a: self.evaluate(s, a))
                # Se ação for diferente da atual, mas delta > 0 (no passo 2 houve atualização de valores)
                # então ainda é possível melhorar ...
                if old_a != s.pi and delta > 0: stable = False


if __name__ == '__main__':
    p = Solver()
    p.solve()
    for n,s in p.states.items():
        print('%s %.2f %s' % (n, s.v, s.pi))



