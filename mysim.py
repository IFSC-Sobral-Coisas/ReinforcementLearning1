import bisect

class Event:
  
  def __init__(self, eng, dt, kind=0):
    self.dt = dt
    self.t = eng.now+dt
    self.kind = kind
    self.callbacks = []

  def set_start(self, t):
    self.t = t + self.dt

  def __lt__(self, o):
    return self.t < o.t

  def __gt__(self, o):
    return self.t > o.t

  def __le__(self, o):
    return self.t <= o.t

  def __ge__(self, o):
    return self.t >= o.t

  def __eq__(self, o):
    return self.t == o.t

  def __ne__(self, o):
    return self.t != o.t

  def add_callback(self, cb, *args):
    self.callbacks.append((cb, args))

  def execute(self):
    res = []
    for cb,args in self.callbacks:
      r = cb(self, args)
      if not r: continue
      if type(r) != type([]): r = [r]
      res += r
    return res

  def __repr__(self):
    return 'Event %d: dt=%.2f, t=%.2f' % (self.kind, self.dt, self.t)

class Engine:

  def __init__(self):
    self.lef = []
    self.now = 0

  def add_event(self, ev):
    ev.set_start(self.now)
    bisect.insort_right(self.lef, ev)

  def cancel_event(self, ev):
    try:
      self.lef.remove(ev)
    except:
      pass

  def next(self):
    if not self.lef: raise RuntimeError('no more events')
    ev = self.lef[0]
    self.now = ev.t
    del self.lef[0]
    return ev

  def run(self, until):
    while self.now < until:
      ev = self.next()
      res = ev.execute()
      for e in res:
        self.add_event(e)
    #print('now: %.2f, until=%.2f'%(self.now, until))

def demo(ev, args):
  print(ev.now, ev.kind, args)
  ev.t += 1
  return ev

if __name__ == '__main__':
  eng = Engine()
  ev = Event(1)
  ev.add_callback(demo)
  eng.add_event(ev)
  eng.run(10)

