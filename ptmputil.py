#import simpy
#from simpy.events import AnyOf,Event
import sys,random
from enum import Enum

class Timer:

    def __init__(self, env, delay, callback=None):
        self.env      = env 
        self.delay    = delay
        self.action   = None
        self.callback = callback
        self.running  = False
        self.canceled = False

    def wait(self):
        """
        Calls a callback after time has elapsed. 
        """
        try:
            yield self.env.timeout(self.delay)
            if self.callback: self.callback()
            self.running  = False
        except simpy.Interrupt as i:
            #print("Interrupted!")
            self.canceled = True
            self.running  = False

    def start(self):
        """
        Starts the timer 
        """
        if not self.running:
            self.running = True
            self.action  = self.env.process(self.wait())
            return True
        return False

    def stop(self):
        """
        Stops the timer 
        """
        if self.running:
            self.action.interrupt()
            self.action = None
            return True
        return False

    def reset(self):
        """
        Interrupts the current timer and restarts. 
        """
        self.stop()
        self.start()

class Waiter:

    ID = 1

    def __init__(self, env):
        self.env      = env 
        self.action   = None
        self.running  = False
        self.canceled = False
        self.lev = []
        self.id = Waiter.ID
        Waiter.ID += 1

    def __get_events__(self, ev):
       l = ev.value.todict().keys()
       return list(l)


    def run(self):
      while True:
        #print ('wait:', self.env.now, len(self.lev))
        try:
            #print(self.id, self.lev)
            ev = AnyOf(self.env, self.lev)
            self.running  = True
            yield ev
            self.running  = False
            ev = self.__get_events__(ev)
            if ev:
              #print('anyof:', self.id, ev)
              ev = ev[0]
              if ev in self.lev: self.lev.remove(ev)
        except simpy.Interrupt as i:
            #print("Interrupted!")
            self.running  = False
            self.canceled = True
        except Exception as e:
            pass
            print(e, self.id, ev, self.lev)

    def add(self, ev):
      #print('add:', self.running, self.lev)
      self.lev.append(ev)
      if self.running: self.reset()

    def cancel(self, ev):
      #print('cancel:', self.id, ev)
      try:
        self.lev.remove(ev)
        if self.running: self.reset()
      except ValueError as e:
        print('cancel: %s não estava agendado' % ev)

    def start(self):
        #print ('start:', self.env.now, self, self.running, self.lev)
        if not self.running:
            self.running = True
            self.action  = self.env.process(self.run())

    def stop(self):
        #print ('stop:', self, self.running)
        if self.running:
            self.action.interrupt()
            self.action = None
        self.running = False

    def reset(self):
        self.stop()
        self.start()

class Latencia:

    def __init__(self):
        self.reset()

    def reset(self):
        self.avg = 0
        self.minima = 1e10
        self.maxima = 0
        self.n = 0
        self.lost = 0

    @property
    def media(self):
        return self.avg / self.n

    def update(self, dt:int):
        self.avg += dt
        self.minima = min(self.minima, dt)
        self.maxima = max(self.maxima, dt)
        self.n += 1

    @property
    def valores(self):
        if self.n:
            return (self.media, self.minima, self.maxima)
        else:
            return (0,0,0)
            # raise ValueError('empty')

class App(Enum):

    PingReq = 1
    PingResp = 2

class Frame:

  DATA = 0
  RTS = 1
  CTS = 2
  ACK = 3
  Timeout = 4
  POLL = 5
  PollTimeout = 6
  IFS = 7
  PollAll = 8
  BA = 9
  MGT = 10

  Tipos = ['DATA', 'RTS', 'CTS', 'ACK', 'Timeout', 'POLL', 'PollTimeout', 'IFS', 'PollAll','BA', 'MGT']


  def __init__(self, kind, duration=0, dest=None, orig=None):
    self.dt = duration
    self.dest = dest
    self.kind = kind
    self.sta = orig
    self.app = None
    self.t0 = 0

  def __str__(self):
    if self.app:
        return '%s (%s): %s -> %s, %d' % (self.Tipos[self.kind], self.app, self.sta, self.dest, self.dt)
    return '%s: %s -> %s, %d' % (self.Tipos[self.kind], self.sta, self.dest, self.dt)
