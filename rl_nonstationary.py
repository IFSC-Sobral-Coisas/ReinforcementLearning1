import attr
import random

@attr.s
class Action:
    id = attr.ib(default=0)
    s = attr.ib(default=0) # sigma
    r = attr.ib(default=0) # recompensa
    n = attr.ib(default=0) # qtas vezes esta ação foi selecionada
    qn = attr.ib(default=0) # valor estimado
    alfa = attr.ib(default=0)
    
    @property
    def reward(self)->float:
        return random.normalvariate(self.r, self.s)

    def update(self, rn:float):
        self.n += 1        
        if self.alfa: alfa = self.alfa
        else: alfa = 1/self.n
        self.qn += (rn - self.qn)*alfa
        
    def next(self):
      self.r += random.normalvariate(0, .01)

# LearnStats: acumula as estatísticas de escolha de melhor ação ao longo da execução,
# com intervalos dados por stepsize
@attr.s
class LearnStats:
  stats = attr.ib(factory=dict)
  stepsize = attr.ib(default=10)
  
  @staticmethod
  def create(n, stepsize):
    d = {}
    pos = 0
    while pos < n:
        d[pos] = 0
        pos += stepsize
    return LearnStats(d, stepsize)
    
  # acumula os resultados contidos em outra instancia de LearnStats
  def update(self, other):
    for k,v in other.stats.items():
      self.stats[k] += v

  # incrementa o contador de melhor ação selecionada, com respeito ao passo dado por "step"
  def incr(self, step):
    pos = int(step/self.stepsize)*self.stepsize
    try:
      self.stats[pos] += 1
    except:
      self.stats[pos] = 1
      
  # normaliza os resultados por um fator dado por 1/n
  def norm(self, n):
    for k in self.stats:
      self.stats[k] /= n
    
class RL0:

    def __init__(self, N:int, e:float=0, decay:float=0, alfa=-1):
        if N < 2: raise ValueError("N deve ser maior que 1 (ao menos duas ações)")
        if e < 0 or e > 1: raise ValueError('e deve estar no intervalo [0,1]')
        self.actions = [Action(id=x, r=random.normalvariate(0,1), s=1, qn=5, alfa=alfa) for x in range(N)]
        self.e = e
        self.decay = decay

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

    # executa o aprendizado: conta quantas vezes foi escolhida a melhor ação
    # a cada intervalo de largura stepsize
    def learn(self, steps:int, stepsize:int=10)->dict:
        nbest = LearnStats.create(steps, stepsize)
        for step in range(steps):
            a = self.__best_action__()
            if self.is_best(a):
                nbest.incr(step)
            # obtém a recompensa e atualiza o valor da ação
            r = a.reward
            a.update(r)
            # atualiza epsilon
            self.e *= 1-self.decay
            # perturba os valores das ações
            for a in self.actions:
              a.next()
        return nbest


class Testbed:

    # K-armed bandit: cria um bandit com k ações e epsilon dado por e
    def __init__(self, k=10, e=0, decay=0):
        self.k = k
        self.e = e
        self.decay = decay

    def run(self, runs=2000, runlen=1000, stepsize=10, alfa=0.1):
        stats = LearnStats.create(runlen, stepsize)
        for n in range(runs):
            r = RL0(self.k, self.e, self.decay, alfa)
            res = r.learn(runlen, stepsize)
            stats.update(res)
        # normaliza os resultados, em função da quantidade de execuções E largura de intervalo de 
        # contabilização
        stats.norm(runs*stepsize)
        return stats

if __name__ == '__main__':
    K = 10
    Decay = 0
    Steps = 1000
    for e in [0]:
        print('running: ', e)
        t = Testbed(K, e, Decay)
        res = t.run()
        f = open('run_%.2f.log' % e, 'w')
        for k, v in res.stats.items():
            f.write('%d %.6f\n' % (k, v))
        f.close()
