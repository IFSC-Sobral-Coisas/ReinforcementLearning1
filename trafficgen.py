import random
from mysim import Event,Engine
from ptmputil import Frame,App

class TrafficGen:
  '''Gerador de tráfego básico:
  - gera quadros com tamanhos uniformemente
  - intervalos entre quqadros também são uniformemente distribuidos'''

  def __init__(self, minperiod:int, minsize:int, **args):
    '''
    Construtor
    :param minperiod: menor intervalo entre dois quadros
    :param maxperiod: maior intervalo entre dois quadros
    :param minsize: menor tamanho de quadro
    :param maxsize: maior tamanho de quadro
    :param start: instante para iniciar a geração de quadros (default: 0)
    '''
    self.minT = minperiod
    self.maxT = args.get('maxperiod', minperiod)
    self.minL = minsize
    self.maxL = args.get('maxsize', minsize)
    self.maxL = max(self.maxL, self.minL)
    self.startTime = args.get('start', 0)
    self.app = None
    self.pkts = 0
    if self.startTime < 0:
      self.startTime = random.randint(0, maxperiod)

  def start(self, env:Engine, sta):
    '''
    Inicia a geração de quadros: gera o primeiro quadro'
    :param env: objeto Engine do simulador
    :param sta: a estação que vai transmitir o quadro
    :return: None
    '''
    self.env = env
    self.sta = sta
    # self.size = random.randint(self.minL, self.maxL)
    self.__add_timeout__(self.startTime, self.run)

  def __get_size__(self)->int:
    return random.randint(self.minL, self.maxL)

  def __gen_frame__(self)->Event:
    '''
    Cria um quadro e o enfileira na estação
    :return: Event
    '''
    size = self.__get_size__()
    ev = Frame(Frame.DATA, self.sta.__airtime__(size), None, self.sta)
    ev.app = self.app
    ev.t0 = self.env.now
    ev.size = size
    self.pkts += 1
    self.sta.handle_frame(ev)
    return ev

  def run(self, e:Event, args):
    '''
    Gera um quadro e o enfileira na estação.
    Agenda a próxima geração de quadro
    (callback para o simulador)
    :param e: o evento passado pelo suimulador
    :param args: argumentos passados pelo simulador (neste caso, não há argumentos)
    :return: None
    '''
    self.__gen_frame__()

    T = random.randint(self.minT, self.maxT)
    # self.size = random.randint(self.minL, self.maxL)
    self.__add_timeout__(T, self.run)

  def __add_timeout__(self, dt, cb):
    '''
    Agenda um evento para o gerador de tráfego: corresponde ao instante em que deve ser gerado novo quadro
    :param dt: delta de tempo para o evento, em relação ao tempo atual
    :param cb: a callback a ser chamada para tratar o evento
    :return:
    '''
    ev = Event(self.env, dt, Frame.Timeout)
    ev.add_callback(cb)
    self.env.add_event(ev)
    return ev

  def max_size(self):
    return self.maxL

  def min_size(self):
    return self.minL

class RateTrafficGen(TrafficGen):

  '''
  Gerador de tráfego a taxa constante
  '''

  def __init__(self, rate:int, minsize:int, **args):
    '''
    Construtor
    :param rate: a taxa de dados do fluxo de quadros, dada em kBps
    :param minsize: menor tamanho de quadro
    :param maxsize: maior tamanho de quadro
    :param start: inicio da geração de quadros
    '''
    TrafficGen.__init__(self, 0, minsize, **args)
    self.rate = rate*1000
    self._octets = 0

  @property
  def curr_rate(self)->int:
    'Taxa de dados atual'
    dt = 1e-6*(self.env.now - self.startTime)
    if dt > 0:
      return int(self._octets/dt)
    else:
      return 0

  def run(self, e:Event, args):
    e = self.__gen_frame__()

    self._octets += e.size
    T = max(1e6*e.size/self.rate, 1e6*self._octets/self.rate + self.startTime - self.env.now)
    self.__add_timeout__(T, self.run)

class ConstantTrafficGen(TrafficGen):

  'Gera quadros a intervalos constantes. Os quadros podem ter tamanhos variáveis'

  def __init__(self, interval:int, minsize:int, **args):
    '''
    Construtor
    :param interval: intervalo entre quadros
    :param minsize: menor tamanho de quadro
    :param maxsize: maior tamanho de quadro
    :param start: inicio da geração
    '''
    TrafficGen.__init__(self, interval, minsize, **args)

class PingGen(ConstantTrafficGen):

  'Gera quadros periódicos do tipo "ping"'

  def __init__(self, interval:int=1000, size:int=80, **args):
    '''
    Construtor
    :param interval: intervalo entre PINGs, em ms (default: 1000 ms)
    :param size: tananho do PING (default: 80 octetos)
    :param start: primeira geração de ping
    '''
    ConstantTrafficGen.__init__(self, interval*1000, size, **args)
    self.app = App.PingReq

class BurstTrafficGen(RateTrafficGen):

  '''Gerador de tráfego em rajada: gera quadros em grupos
  Gera quadros com taxa básica, e ocasionalmente gera quadros com taxa de pico'''

  Burst = 1
  Idle = 0
  IFS = 2 # 2 us

  def __init__(self, baserate:int, duration:int, minsize:int, **args):
    '''
    Construtor
    :param baserate: taxa de dados do fluxo normal, em Bps
    :param duration: duração do fluxo normal, em ms
    :param minsize: menor tamanho de quadro
    :param args: argumentos opcionais:
        * *peakrate* (``int``) --
          taxa de pico
        * *peakduration* (``int``) --
          duração da rajada
        * *start* (``int``) --
          início da geração de quadros
    '''
    maxsize = args.get('maxsize', minsize)
    start = args.get('start', 0)
    RateTrafficGen.__init__(self, baserate, minsize, **args)
    self._peakrate = args.get('peakrate', baserate)*1000
    self._basedt = duration*1000
    self._baserate = self.rate
    self._peakdt = args.get('peakduration', duration)*1000
    self.state = self.Idle
    self.n = 0
    self.N = 0
    self.pkts = 0

  def start(self, env:Engine, sta):
    TrafficGen.start(self, env, sta)
    self._finish = self.env.now + random.expovariate(1 / self._basedt)

  def run(self, e, args):
    RateTrafficGen.run(self, e, args)
    self.__fsm__(e)
    
  def __fsm__(self, e):
    'FSM para a geração de quadros: estados Idle (normal) e Burst (rajada)'
    # print(self.env.now/1000, self.state, self._finish/1000, self.curr_rate/1000, self._octets, self.env.now-self.startTime)
    if self.state == self.Idle:
      if self.env.now >= self._finish:
        self.state = self.Burst
        self._octets = 0
        self.startTime = self.env.now
        self.rate = self._peakrate
        self._finish = self.env.now + random.expovariate(1/self._peakdt)
    elif self.state == self.Burst:
      if self.env.now >= self._finish:
        self.state = self.Idle
        self._octets = 0
        self.startTime = self.env.now
        self.rate = self._baserate
        self._finish = self.env.now + random.expovariate(1/self._basedt)

