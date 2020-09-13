import random
from mysim import Event
from ptmputil import Frame,App

class TrafficGen:

  def __init__(self, minperiod, maxperiod, minsize, maxsize, start=0):
    self.minT = minperiod
    self.maxT = maxperiod
    self.minL = minsize
    self.maxL = maxsize
    self.app = None
    if start:
      self.startTime = start
    else:
      self.startTime = random.randint(0, maxperiod)

  def start(self, env, sta):
    self.env = env
    self.sta = sta
    # self.size = random.randint(self.minL, self.maxL)
    self.__add_timeout__(self.startTime, self.run)

  def run(self, e, args):
    size = random.randint(self.minL, self.maxL)
    ev = Frame(Frame.DATA, self.sta.__airtime__(size), None, self.sta)
    ev.app = self.app
    ev.t0 = self.env.now
    ev.size = size
    self.sta.handle_frame(ev)
    T = random.randint(self.minT, self.maxT)
    # self.size = random.randint(self.minL, self.maxL)
    self.__add_timeout__(T, self.run)

  def __add_timeout__(self, dt, cb):
    ev = Event(self.env, dt, Frame.Timeout)
    ev.add_callback(cb)
    self.env.add_event(ev)
    return ev

  def max_size(self):
    return self.maxL

  def min_size(self):
    return self.minL

class ConstantTrafficGen(TrafficGen):

  def __init__(self, interval, minsize, maxsize=0, start=0):
    TrafficGen.__init__(self, interval, interval, minsize, max(minsize, maxsize), start)

class PingGen(TrafficGen):

  def __init__(self, interval, size, start=0):
    TrafficGen.__init__(self, interval, interval, size, size, start)
    self.app = App.PingReq

class BurstTrafficGen(TrafficGen):

  Burst = 1
  Idle = 0
  IFS = 2 # 2 us

  def __init__(self, mininterval, maxinterval, duration, minsize, maxsize, start=0):
    TrafficGen.__init__(self, mininterval, maxinterval, minsize, maxsize, start)
    self.dt = duration
    self.state = self.Idle
    self.n = 0
    self.N = 0
    self.pkts = 0

  def run(self, e, args):
    self.fsm(e)
    
  def __gen_frame__(self):
    size = random.randint(self.minL, self.maxL)
    ev = Frame(Frame.DATA, self.sta.__airtime__(size), self.sta, self.sta)
    ev.t0 = self.env.now
    ev.size = size
    self.sta.handle_frame(ev)
    self.pkts += 1

  def fsm(self, e, *args):
    if self.state == self.Idle:
      self.N = random.randint(1, self.dt)
      self.n = 1
      self.__gen_frame__()
      if self.n < self.N:
        self.state = self.Burst
        self.__add_timeout__(self.IFS, self.fsm)
      else:
        T = random.randint(self.minT, self.maxT)
        self.__add_timeout__(T, self.fsm)
    elif self.state == self.Burst:
      self.n += 1
      self.__gen_frame__()
      if self.n < self.N: self.__add_timeout__(self.IFS, self.fsm)
      else:
        T = random.randint(self.minT, self.maxT)
        self.__add_timeout__(T, self.fsm)
        self.state = self.Idle

