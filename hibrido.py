#!/usr/bin/python3

from mysim import *
#from simpy.events import AnyOf,Event
import sys,random,time,copy
from collections import deque
import argparse

from ptmputil import *
from trafficgen import *

class Estado(Enum):
    Idle = 0
    Wait = 1
    Boff = 2
    Rx = 3
    BoffOk = 4
    RxErr = 5
    Colision = 6
    BA_Wait = 7
    RxEnd = 8
    NAV = 9
    NAVOK = 10
    IFS_Wait = 11

    DATA_rx = 12
    RTS_tx = 13
    POLLED = 15
    POLL_END = 16
    POLL_RX = 18
    DATA_tx = 17
    POLLALL = 20
    DATA_wait = 50

class Modo(Enum):
    TDMA = 1
    CSMA = 2

class Timeout(Enum):
    Ack = 1
    Backoff = 2
    Frame = 3
    Poll = 4

class STA:

     Size = 32768
     Overhead = 32 # PLCP e PHY header: 32 us
     ID = 1

     # Intervalos minimo e maximo entre transmissoes (us)
     MinT = 10000
     MaxT = 20000

     # IFS: 34us
     IFS = 34 # 100
     SIFS = 13 # 45
     SlotTime = 9 #32
     cwmin = 15
     cwmax = 1023
     ACK_size = 14
     MaxCollisions = 7

     BA_SIZE = 64

     RTS_size = 20
     CTS_size = 14

     # porcentagem minima do tempo de posse do poll
     MinPeriod = .2 # 20%

     # processamento no envio do poll
     PollOverhead = 20
     TxOverhead = (4,40)

     def __init__(self, env, rate, gen):
         self.env = env
         self.gen = gen
         self.id = STA.ID
         STA.ID += 1
         # Start the run process everytime an instance is created.
         self.rate = rate
         self.base = None
         self.range = 0
         self.state = Estado.Idle
         self.tout_ev = None # usado para timeout de espera de quadro
         self.boff_ev = None # usado para backoff
         self.action = None
         self.u = 0
         self.ru = 0
         self.octets = 0
         self.N = 0
         self.n = 0
         self.ifs = STA.IFS
         self.queue = deque()
         self.lat = Latencia()
         self.ping_lat = Latencia()
         self.cw = self.cwmin
         self.boff_cnt = 0
         self.cols = 0
         self.timeouts = {}
         self.seqno = 0
         self.rx_sta = {}
         self._mode = Modo.CSMA
         self.fsm = self.fsm_csma
         self.handle_frame = self.handle_frame_csma
         self.last_tx_int = 0
         self._last_tx = None
         self._retransmissions = 0
         self._frames = 0
         self._frames0 = 0
         self._t0 = self.env.now
         self._last_lat = Latencia()

     @property
     def num_clients(self)->int:
         return len(self._stas)

     @property
     def currlatency(self)->float:
         a,m,M = self._last_lat.valores
         self._last_lat.reset()
         return a

     @property
     def frames(self)->int:
         return self._frames

     @property
     def currpps(self)->int:
         try:
             dt = (self.env.now - self._t0)/1e6
             rate = (self._frames - self._frames0)/dt
         except:
             rate = 0
         return int(rate)

     @property
     def pps(self)->int:
         rate = self.currpps
         self._frames0 = self._frames
         self._t0 = self.env.now
         return rate

     @property
     def curr_rate(self)->int:
         return 8*self.octets/self.env.now

     def __last_tx_interval__(self):
         if self.last_tx_int:
            dt = self.env.now - self.last_tx_int
         else:
            dt = 0
         self.last_tx_int = self.env.now
         return dt

     def __hash__(self):
       return hash(self.id)

     def __str__(self):
       return '%s %d (%s)' % (self.__class__.__name__, self.id, self.gen.__class__.__name__)

     def data_rate(self, t):
       return self.ru*self.rate/t

     def __switch_csma__(self):
         # print(self, '---> CSMA')
         self._mode = Modo.CSMA
         self.fsm = self.fsm_csma
         self.handle_frame = self.handle_frame_csma
         self.state = Estado.Idle

     def __switch_tdma__(self):
         # print(self.env.now, self, '---> TDMA')
         self._mode = Modo.TDMA
         self.fsm = self.fsm_tdma
         self.handle_frame = self.handle_frame_tdma
         self.state = Estado.Idle

     @property
     def backoff(self):
         n = random.randint(0, self.cw)
         if self.cw < self.cwmax: self.cw = (self.cw<<1)+1
         return n

     def add_base(self, base, dist):
         self.base = base # a base PTMP
         self.range = dist/3e2 # atraso de propagacao, em us
         self.__ack_tout = 2*(self.SIFS + self.range + self.__airtime__(self.ACK_size))

     def __send_ba__(self, ev)->int:
       dt = self.__airtime__(self.BA_SIZE)
       fr = Frame(Frame.BA, dt, ev.sta, self)
       fr.range = ev.range
       fr.t0 = self.env.now
       self.__send_frame__(fr, self.SIFS)
       return dt + self.SIFS + self.IFS

     def get_ack_tout(self, dest):
         return self.__ack_tout

     def start(self):
         if not self.base: raise RuntimeError('falta definir a base')
         self.gen.start(self.env, self)

     def add_frame(self, data, dt=0):
       if Debug: print('add_frame: %s %s %s %d %.2f' % (self, self.state, data, data.range, self.env.now))
       # if data.kind == Frame.DATA: print('add_frame:', self, data.dest, data.t0)
       ev = Event(self.env, data.range+dt, Frame.Timeout)
       ev.add_callback(self.frame_rx)
       ev.value = data
       # print('add_frame:', data.t0)
       self.env.add_event(ev)

     def frame_rx(self, e, args):
       #print('frame_rx: %d %s %s' % (self.env.now, self, e.value))
       self.fsm(e.value)

     def handle_frame_tdma(self, fr, *args):
       if isinstance(fr, Event):
           fr = fr.value
       fr.range = self.range
       fr.seq = self.seqno
       self.seqno += 1
       fr.dest = self.base
       self.queue.append(fr)

     def handle_frame_csma(self, fr, *args):
       # if isinstance(fr, Event):
       #     fr = fr.value
       # if not fr.dest:
       #     fr.dest = self.__get_dest__()
       # fr.range = self.get_range(fr.dest)
       # fr.seq = self.seqno
       # self.seqno += 1
       # # print('handle_frame', self, fr)
       # if fr.app == App.PingResp or fr.app == App.PingReq:
       #     self.queue.appendleft(fr)
       # else:
       #     self.queue.append(fr)
       STA.handle_frame_tdma(self, fr)
       if self.state == Estado.Idle:
           self.__dequeue__()
       #      # ev = Event(self.env, self.env.now)
       #      # ev.value = fr
       #      self.u += 1
       #      self.n += 1
       #      self.fsm(fr)
       # else:
       #     if fr.app == App.PingResp or fr.app == App.PingReq:
       #         self.queue.appendleft(fr)
       #     else:
       #         self.queue.append(fr)

     def __sched_frame__(self, fr:Frame, dt:int):
         ev = Event(self.env, dt)
         ev.value = fr
         ev.add_callback(self.handle_frame)
         self.env.add_event(ev)
         # print('sched_frame:', self.env.now, ev.t, dt, fr.t0)

     def start_backoff(self, cnt=None):
         if cnt != None:
             print('colisao:', self.env.now, self, self._mode, self.cols)
             self.boff_cnt = cnt
             delay = self.IFS
             self.cols += 1
         else:
             delay = self.SlotTime
         self.__add_timeout__(Timeout.Backoff, delay, self.backoff_dec)

     def backoff_dec(self, e, args):
         if self.boff_cnt == 0:
             e = Frame(Frame.Timeout)
             self.fsm(e)
         else:
             self.boff_cnt -= 1
             self.start_backoff()

     def timeout(self, e, args):
       ev = Frame(Frame.Timeout)
       self.fsm(ev)

     def poll_timeout(self, e=None, args=None):
       ev = Frame(Frame.PollTimeout)
       self.fsm(ev)

     def __add_timeout__(self, nome:Timeout, dt:int, cb):
        self.__cancel_timeout__(nome) # preventivo
        ev = Event(self.env, dt, Frame.Timeout)
        ev.add_callback(cb)
        self.env.add_event(ev)
        self.timeouts[nome] = ev

     def __cancel_timeout__(self, nome:Timeout):
        try:
           self.env.cancel_event(self.timeouts[nome])
           del self.timeouts[nome]
        except KeyError:
            pass

     def __airtime__(self, bytes):
       return bytes*8/self.rate+self.Overhead

     def send_frame(self, q, state=Estado.Wait):
         # if q.app == App.PingReq:
         #     q.seq = self._last_ping
         # self.__send_frame__(q, self.ifs)
         if q == None:
             self.state = Estado.Idle
             return
         self.__send_frame__(q, 0)
         self._retransmissions += 1
         oh = random.randint(self.TxOverhead[0], self.TxOverhead[1])
         self.__add_timeout__(Timeout.Ack, q.dt + self.get_ack_tout(q.dest) + oh, self.timeout)  # espera por ack
         self.state = state

     def __get_dest__(self):
         return self.base

     def get_range(self, dest):
         return self.range

     def __dequeue__(self):
         while self.queue:
           data = self.queue.popleft()
           if data.app == App.PingResp:
               if self.env.now - data.t0 > 500000:
                   self.ping_lat.lost += 1
                   continue
           self.cw = self.cwmin
           if not data.dest:
               data.dest = self.__get_dest__()
           data.range = self.get_range(data.dest)
           self._last_tx = data
           self._retransmissions = 0
           self.send_frame(data)
           self.u += 1
           self.n += 1
           # print('>>> dequeue: sent frame')
           return True
         return False

     def __send_poll__(self, sta):
       out = Frame(Frame.POLL, self.__airtime__(64), sta, self)
       out.range = self.range
       out.period = self.period# - self.env.now
       sta.add_frame(out, self.PollOverhead+self.backoff)
       self.state = Estado.Idle

     def __update_lat__(self, ev):
       # if ev.t0 == 0: print('update_lat:', self, ev, self.env.now)
       dt = self.env.now - ev.t0
       self.lat.update(dt)
       self._last_lat.update(dt)
       # if Debug: print('lat:', ev.sta, dt)
       # print('lat:', ev.sta, dt, ev.t0)

     def __gen_ping_resp__(self):
         q = self._last_rx
         fr = Frame(Frame.DATA, q.dt, q.sta, self)
         fr.app = App.PingResp
         # fr.seq = self._last_rx.seq
         fr.t0 = q.t0
         # pra enviar em próximo txop
         # print(self.env.now, self, fr)
         # t1 = random.randint(300,500)
         t1 = 0
         self.__sched_frame__(fr, t1)
         # self.queue.append(fr)

     def __update_ping_lat__(self):
         # if self._last_rx.seq < self._last_ping:
         #     return
         # self._last_ping = self._last_rx.seq
         dt = self.env.now - self._last_rx.t0
         if dt < 1000000:
             if Debug: print('update_ping:', self.env.now, dt, self._last_rx.t0, self, self._last_rx.sta)
             self.ping_lat.update(dt)

     def __send_frame__(self, fr:Frame, dt:int):
         # print('send_frame:', fr.dest, fr.t0)
         fr.dest.add_frame(fr, dt)

     def handle_collision_rx(self, ev, tout:Timeout=Timeout.Frame, state:Estado=Estado.Colision):
         self.state = state
         self._last_rx = ev
         self.__cancel_timeout__(tout)
         self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
         self.cols += 1

     def __check_seq__(self):
         try:
             ok = self.rx_sta[self._last_rx.sta] < self._last_rx.seq
         except:
             ok = True
         try:
            self.rx_sta[self._last_rx.sta] = self._last_rx.seq
         except Exception as e:
             pass
             # print('>>>> check_seq: ', self._last_rx, e)
         return ok

     def handle_rx_ok(self, state:Estado=Estado.RxEnd):
         # if self._last_rx.app:
         #     print(self.env.now, self, self._last_rx)
         if self._last_rx.dest == self and self._last_rx.kind == Frame.DATA:
             dt = self.__send_ba__(self._last_rx)
             if self.__check_seq__():
                 self._frames += 1
                 self.__update_lat__(self._last_rx)
                 if self._last_rx.app == App.PingReq:
                     self.__gen_ping_resp__()
                 elif self._last_rx.app == App.PingResp:
                     self.__update_ping_lat__()
             self.__add_timeout__(Timeout.Frame, dt, self.timeout)
             self.state = state
         else:
             self.state = Estado.Idle

     def handle_start_rx(self, ev:Frame, nav:Estado = Estado.NAVOK, defstate:Estado=Estado.Rx):
         self.__cancel_timeout__(Timeout.Backoff)
         self._last_rx = ev
         self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
         if ev.dest == self and ev.kind == ev.DATA:
             self.state = defstate
         elif nav != None:
             self.state = nav

     def handle_finish_rx(self, state:Estado = Estado.BoffOk):
         if self.boff_cnt > 0:
             self.state = state
             self.start_backoff()
         elif len(self.queue) > 0:
             self.start_backoff(self.backoff)
             self.state = Estado.BoffOk
         else:
             self.state = Estado.Idle

     def handle_rx_poll(self, ev):
         # if Debug: print('STA %d: POLL=%.2f' % (self.id, ev.period))
         self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
         self.__add_timeout__(Timeout.Poll, ev.period + ev.dt, self.poll_timeout)
         self.period = self.env.now + ev.dt + ev.period
         self.state = Estado.POLL_RX

     def fsm_tdma(self, ev):
       if Debug: print(self, self.env.now, self.state, len(self.queue), ev)
       # print(self, self.env.now, len(self.queue), ev)
       if ev.kind == ev.MGT:
           if ev.app == Modo.CSMA: self.__switch_csma__()
           return
       if self.state == Estado.Idle:
         if ev.kind == ev.DATA: # veio da base
             self.handle_start_rx(ev, None, Estado.DATA_rx)
         elif ev.kind == ev.POLL: # início do timeslot
             self.handle_rx_poll(ev)

       elif self.state == Estado.DATA_rx: # espera DATA terminar de ser recebido
        if ev.kind == ev.Timeout:
            self.handle_rx_ok(Estado.Idle)

       elif self.state == Estado.POLL_RX:# espera POLL terminar de ser recebido
         if ev.kind == ev.Timeout:
           if not self.__dequeue__(): # fila vazia ... devolve poll
             self.__cancel_timeout__(Timeout.Poll)
             self.__send_poll__(self.base)

       elif self.state == Estado.Wait: # no timeslot
         if ev.kind == ev.BA:
             self.__cancel_timeout__(Timeout.Frame)
             self.ru += (self._last_tx.dt - self.Overhead - self.ifs)
             self.N += 1
             self.octets += self._last_tx.size
             self._frames += 1
             self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
             self.state = Estado.BA_Wait
         elif ev.kind == ev.Timeout:
             print('tout espera BA')
             self.cols += 1
             self.send_frame(self._last_tx)
         elif ev.kind == ev.PollTimeout: # acabou timeslot
           self.state = Estado.POLL_END

       elif self.state == Estado.POLL_END: # acabou timeslot, mas precisa esperar terminar
         if ev.kind == ev.BA:       # envio de DATA
           self.ru += (self._last_tx.dt - self.Overhead - self.ifs)
           self.N += 1
           self._frames += 1
           self.__send_poll__(self.base)
         elif ev.kind == ev.Timeout:       # envio de DATA
             # self.cols += 1
             self.__send_poll__(self.base)

       elif self.state == Estado.BA_Wait:
           if ev.kind == ev.Timeout:
               if not self.__dequeue__():
                   self.__send_poll__(self.base)
           elif ev.kind == ev.PollTimeout:
               self.state = Estado.POLL_END

     def fsm_csma(self, ev:Frame):
       if Debug: print(self.env.now, self, self.state, ev)
       # print(self.env.now, self, self.state, ev)
       if ev.kind == ev.MGT:
           if ev.app == Modo.TDMA: self.__switch_tdma__()
           return
       if self.state == Estado.Idle:
         if ev.kind == ev.DATA: # veio da base
            if ev.sta == self:
                # tx
                self._last_tx = ev
                self.send_frame(ev)
            else:
                self.handle_start_rx(ev)
         elif ev.kind == ev.BA: # veio da base
             self.handle_start_rx(ev)

       elif self.state == Estado.NAV: # espera DATA terminar de ser recebido
            if ev.kind == ev.Timeout:
                self.handle_finish_rx(Estado.Boff)
            elif ev.kind == ev.DATA: # colisão
                self.__add_timeout__(Frame.Timeout, ev.dt, self.timeout)
            elif ev.kind == ev.BA: # veio da base
                self.__add_timeout__(Frame.Timeout, ev.dt, self.timeout)

       elif self.state == Estado.NAVOK: # espera DATA terminar de ser recebido
            if ev.kind == ev.Timeout:
                self.handle_finish_rx()
            elif ev.kind == ev.DATA: # colisão
                self.__add_timeout__(Frame.Timeout, ev.dt, self.timeout)
            elif ev.kind == ev.BA: # veio da base
                self.__add_timeout__(Frame.Timeout, ev.dt, self.timeout)


       elif self.state == Estado.Rx: # espera DATA terminar de ser recebido
            if ev.kind == ev.Timeout:
                self.handle_rx_ok()
                # self.handle_finish_rx()
            elif ev.kind == ev.DATA: # colisão
                self.handle_collision_rx(ev)
            elif ev.kind == ev.BA: # veio da base
                self.handle_collision_rx(ev)

       elif self.state == Estado.RxEnd: # espera termino de BA
           if ev.kind == ev.Timeout:
               self.handle_finish_rx()
           elif ev.kind == ev.DATA: # colisão
               self.handle_collision_rx(ev)
           elif ev.kind == ev.BA: # veio da base
               self.handle_collision_rx(ev)

       elif self.state == Estado.Colision:
           if ev.kind == ev.Timeout:
               self.handle_finish_rx(Estado.Boff)
           elif ev.kind == ev.DATA:
               self.handle_collision_rx(ev)
           elif ev.kind == ev.BA: # veio da base
               self.handle_collision_rx(ev)

       elif self.state == Estado.RxErr:  # espera DATA terminar de ser recebido
           if ev.kind == ev.Timeout:
               self.state = Estado.Boff
               self.start_backoff(self.backoff)
           elif ev.kind == ev.DATA:
               self.handle_collision_rx(ev, Timeout.Frame, Estado.RxErr)
           elif ev.kind == ev.BA: # veio da base
               self.handle_collision_rx(ev, Timeout.Frame, Estado.RxErr)

       elif self.state == Estado.Wait:# espera ACK
         if ev.kind == ev.Timeout:
             self.state = Estado.Boff
             self.start_backoff(self.backoff)
         elif ev.kind == ev.BA:
             self.__cancel_timeout__(Timeout.Ack)
             if ev.dest == self:
                 self.state = Estado.BA_Wait
                 self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
             else:
                 self.handle_collision_rx(ev, Timeout.Ack, Estado.RxErr)
         elif ev.kind == ev.DATA:
             self.handle_collision_rx(ev, Timeout.Ack, Estado.RxErr)

       elif self.state == Estado.BA_Wait:
           if ev.kind == ev.Timeout:
               frame_len = self._last_tx.dt - self.Overhead
               # print('%d %s: len=%d us, qlen=%d' % (self.__last_tx_interval__(), self.state, frame_len, len(self.queue)))
               self._frames += 1
               self.ru += frame_len
               self.N += 1
               self.octets += self._last_tx.size
               self.state = Estado.BoffOk
               self.start_backoff(self.cwmin)
           elif ev.kind == ev.DATA:
               self.handle_collision_rx(ev, Timeout.Ack, Estado.RxErr)
           elif ev.kind == ev.BA:
               self.handle_collision_rx(ev, Timeout.Ack, Estado.RxErr)

       elif self.state == Estado.BoffOk: # backoff após tx com sucesso
           if ev.kind == ev.Timeout:
               if Debug: print('BoffOk: ru=%d' % (self.ru), self.env.now)
               if not self.__dequeue__():
                   self.state = Estado.Idle
           elif ev.kind == ev.DATA:
               self.handle_start_rx(ev)

       elif self.state == Estado.Boff: # backoff após erro
           if ev.kind == ev.Timeout:
               if self._retransmissions < self.MaxCollisions:
                   self.send_frame(self._last_tx)
               elif not self.__dequeue__():
                   self.state = Estado.Idle
           elif ev.kind == ev.DATA:
               self.handle_start_rx(ev, Estado.NAV)



class Base(STA):

     PollPeriod = 5000 # 5ms

     def __init__(self, env, rate, gen, period=PollPeriod):
       STA.__init__(self, env, rate, gen)
       self.period = period
       self.stas = []
       self._stas = []
       self._last = None
       self._mode = Modo.CSMA

     @property
     def num_clients(self)->int:
         return len(self._stas)

     def add_sta(self, sta):
         self.stas.append(sta)
         self._stas.append(sta)

     def get_stations(self):
         self.stas.sort(key=lambda x: x.id)
         return self.stas

     def __get_dest__(self):
         return random.choice(self.stas)

     def get_range(self, dest):
         return dest.range

     def get_ack_tout(self, dest):
         return 2*(self.SIFS + dest.range + self.__airtime__(self.ACK_size))

     def __send_frame__(self, q:Frame, dt:int=0):
         # print('send_frame', self.env.now)
         random.shuffle(self._stas)
         for sta in self._stas:
             fr = Frame(q.kind, q.dt, sta, self)
             fr.app = q.app
             fr.range = sta.range
             fr.t0 = q.t0
             if fr.kind == Frame.DATA:
                fr.seq = q.seq
             sta.add_frame(fr, self.ifs)

     def start(self):
       if not self.stas: raise RuntimeError('falta incluir ao menos um STA')
       # mr = max(map(lambda x: x.range, self.stas))
       self.gen.start(self.env, self)

     def set_tdma(self):
         self._mode = Modo.TDMA

     def set_csma(self):
         self._mode = Modo.CSMA

     def set_mode(self, m:Modo):
         self._mode = m

     @property
     def mode(self)->Modo:
         return self._mode

     @mode.setter
     def mode(self, modo:Modo):
         self._mode = modo

     def __switch_csma__(self):
         STA.__switch_csma__(self)
         fr = Frame(Frame.MGT)
         fr.app = Modo.CSMA
         self.__send_frame__(fr)

     def __switch_tdma__(self):
        STA.__switch_tdma__(self)
        fr = Frame(Frame.MGT)
        fr.app = Modo.TDMA
        self.__send_frame__(fr)
        self.prox = iter(self.stas)
        self.iter_sta = self.__next_sta__()
        # self.gen.start(self.env, self)
        self.poll_timeout()

     def handle_frame_csma(self, fr, *args):
         # print('handle_frame_csma:', self._mode)
         if self._mode == Modo.TDMA:
             # print(self.env.now,self.state)
             if self.state == Estado.Idle:
                self.__switch_tdma__()
                self.handle_frame_tdma(fr, *args)
                return
         STA.handle_frame_csma(self, fr, *args)

     def handle_frame_tdma(self, fr, *args):
         # print('handle_frame_tdma:', self._mode)
         if self._mode == Modo.CSMA:
             # print(self.env.now,self.state)
             if self.state == Estado.Idle:
                 self.__switch_csma__()
                 self.handle_frame_csma(fr, *args)
                 return
         if isinstance(fr, Event):
                fr = fr.value
        # dest = random.choice(self.stas)
        # ev.range = dest.range
        # ev.dest = dest
         fr.seq = self.seqno
         self.seqno += 1
         self.queue.append(fr)
        # print('handle_frame: queue=%d'%len(self.queue), self.env.now)

     def __next_sta__(self):
         while True:
             if self._last == self:
                 try:
                     self._last = next(self.prox)
                 except StopIteration:
                     self.prox = iter(self.stas)
                     self._last = next(self.prox)
             else:
                 self._last = self
             yield self._last

     def __send_poll__(self, sta, period=0):
       out = Frame(Frame.POLL, self.__airtime__(64), sta, self)
       out.period = self.period
       out.range = sta.range
       out.dest = sta
       sta.add_frame(out, self.PollOverhead+self.ifs+self.backoff)
       self.state = Estado.Idle

     def __sched_sta__(self):
       # escolhe proxima sta no ciclo regular
       sta = next(self.iter_sta)
       if sta == self:
         if Debug: print(self, 'selecionada', len(self.queue))
         if self.__dequeue__():
           self.__add_timeout__(Timeout.Poll, self.period, self.poll_timeout)
           self.state = Estado.Wait
           return # base ok .. enviou um quadro
         sta = next(self.iter_sta)
       self.__add_timeout__(Timeout.Poll, 2*self.period, self.poll_timeout)
       self.__send_poll__(sta)
       self.state = Estado.Idle
       return sta

     def fsm_csma(self, ev):
         if Debug: print(self, self.env.now, self.state, ev, self.fsm == self.fsm_tdma)
         STA.fsm_csma(self, ev)

     def fsm_tdma(self, ev):
       if Debug: print(self, self.env.now, self.state, ev, 'queue=%d' % len(self.queue))
       # print(self, self.env.now, self.state, ev)
       if self.state == Estado.Idle:
         #if ev.kind == ev.POLL:
           #self.bw[ev.sta].update(ev.period)
         if ev.kind == ev.POLL:
           if Debug: print('base rx poll: dt=%.2f, t=%.2f' % (ev.dt, self.env.now))
           self.__cancel_timeout__(Timeout.Poll)
           self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
           self.state = Estado.POLL_RX
           # tslot = self.bw[ev.sta]
           # ts = tslot.t - ev.period # o que sobrou do timeslot
           # self.bw[ev.sta].update(ts)
           # self.__sched_sta__()
           #self.__add_timeout__(ev.period+self.IFS, self.poll_timeout)
         elif ev.kind == ev.PollTimeout:
           self.__sched_sta__()
         elif ev.kind == ev.DATA:
           self.handle_start_rx(ev, None, Estado.DATA_rx)
           # self.state = Estado.DATA_rx
           # self._last_rx = ev
           # self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
           # # self.__send_ba__(ev)
           # if Debug: print(self, ' timeout para DATA: ', ev.dt, self.env.now+ev.dt)

       elif self.state == Estado.POLL_RX:
           if ev.kind == ev.Timeout:
               if Debug: print('base fim rx poll: t=%.2f' % self.env.now)
               self.__sched_sta__()

       elif self.state == Estado.DATA_rx:
           if ev.kind == ev.Timeout:
               self.handle_rx_ok(Estado.Idle)
           else:
             if Debug: print("%s em DATA_rx" % ev)

       elif self.state == Estado.Wait: # base em posse do token
           if Debug: print(self, 'POLLED', len(self.queue), ev)
           if ev.kind == ev.BA:
             self.__cancel_timeout__(Timeout.Frame)
             self.ru += (self._last_tx.dt - self.Overhead)
             self.N += 1
             self._frames += 1
             self.octets += self._last_tx.size
             self.__add_timeout__(Timeout.Frame, ev.dt, self.timeout)
             self.state = Estado.BA_Wait
           elif ev.kind == ev.Timeout:
               print('wait: timeout espera por BA')
               self.cols += 1
               self.send_frame(self._last_tx)
           elif ev.kind == ev.PollTimeout:
             self.state = Estado.POLL_END
           else:
             if Debug: print('Base: %s em POLLED ???' % ev)

       elif self.state == Estado.POLL_END: # periodo do Poll acabou, mas estava em transmissao
           if Debug: print(self, 'POLL_END', len(self.queue))
           self._frames += 1
           self.__sched_sta__()

       elif self.state == Estado.BA_Wait:
           if ev.kind == ev.Timeout:
               if not self.__dequeue__():
                   self.__sched_sta__()
           elif ev.kind == ev.PollTimeout:
               self.state = Estado.POLL_END

######################################################################
Um_Segundo = 1000
Debug = False

def pps(nsta, baseT, nburst, fator):
    norm_load = (nsta - nburst) * Um_Segundo/(baseT*1.5)
    burst_load = nburst * Um_Segundo/(baseT*1.5/fator)
    return int(norm_load + burst_load)


if __name__ == '__main__':
    Rate = 150 # 150 Mbps
    CpeRate = 1000
    Range = 5000 # 5000 m entre base e sta
    Nstas = 15 # qtde de estações
    Tempo = 100
    Minsize = 1500
    Maxsize = 16384
    Minperiod = 20
    Maxperiod = 40
    Fator = 5
    Nburst = 0
    Nping = 0


    parser = argparse.ArgumentParser(description='Simulador 802.11n')
    parser.add_argument('-n', '--cpes', help='quamtidade de cpes (default=%d)' % Nstas, type=int, dest='nstas', required=False,
                        default=Nstas)
    parser.add_argument('-t', '--len', help='duração da simulação em segundos (default=%d)' % Tempo, type=int, dest='t', required=False,
                        default=Tempo)
    parser.add_argument('-d', '--range', help='distância máxima entre base e cpe, em metros (default=%d)' % Range, type=int, dest='range', required=False,
                        default=Range)
    parser.add_argument('-f', '--fator', help='fator de multiplicação para tráfego intenso (default=%d)' % Fator, type=int, dest='fator', required=False,
                        default=Fator)
    parser.add_argument('-b', '--bursty', help='qtde de cpes com tráfego intenso (default=%d)' % Nburst, type=int, dest='nburst', required=False,
                        default=Nburst)
    parser.add_argument('-l', '--ping', help='qtde de cpes que fazem ping (default=%d)' % Nping, type=int, dest='nping', required=False,
                        default=Nping)
    parser.add_argument('-B', '--base', help='padrão de tráfego da base (default=ping)', type=str, dest='base', choices=('ping','bursty','normal'),
                        required=False, default='ping')
    parser.add_argument('-m', '--minsize', help='menor tamanho de quadro (default=%d)' % Minsize, type=int, dest='minsize', required=False,
                        default=Minsize)
    parser.add_argument('-M', '--maxsize', help='maior tamanho de quadro (default=%d)' % Maxsize, type=int, dest='maxsize', required=False,
                        default=Maxsize)
    parser.add_argument('-p', '--minperiod', help='menor periodo entre quadros, em milissegundos (default=%d)' % Minperiod, type=int, dest='minperiod', required=False,
                        default=Minperiod)
    parser.add_argument('-P', '--maxperiod', help='maior periodo entre quadros , em milissegundos (default=%d)' % Maxperiod, type=int, dest='maxperiod', required=False,
                        default=Maxperiod)
    parser.add_argument('-R', '--rate', help='Taxa de dados do canal sem-fio, em Mbps (default=%d)' % Rate, type=int, dest='rate', required=False,
                        default=Rate)
    parser.add_argument('-r', '--datarate', help='Taxa de dados do gerador de tráfego, em kBps (default=%d)' % CpeRate, type=int, dest='datarate', required=False,
                        default=CpeRate)
    parser.add_argument('--tdma', help='Modo TDMA (default: CSMA)', dest='tdma', required=False,
                        action='store_true')
    parser.add_argument('--csma', help='Modo CSMA (isto já é o default ...)', dest='tdma', required=False,
                        action='store_false')
    parser.add_argument('--debug', help='Ativa debug', dest='debug', required=False, action='store_true')
    parser.add_argument('-v', help='Verbose: mostra resultados por cpe', dest='verbose', required=False, action='store_true')

    args = parser.parse_args()

    env = Engine()

    # com os valores acima, cada STA ou a base geram um tráfego de 8.5 Mbps

    Debug = args.debug

    if args.base == 'ping':
        gen = PingGen(Um_Segundo, 64)
    elif args.base == 'bursty':
        gen = TrafficGen(args.minperiod*1000/args.fator, args.maxperiod*1000/args.fator, args.minsize, args.maxsize)
    else:
        gen = TrafficGen(args.minperiod*1000, args.maxperiod*1000, args.minsize, args.maxsize)

    # gen = TrafficGen(minT*fator, maxT * fator, 1500, 16384)
    nburst = args.nburst
    nping = args.nping
    base = Base(env, args.rate, gen)
    for x in range(args.nstas):
      if nburst > 0:
         # gen = BurstTrafficGen(50000, 150000, 8, 1500, 32768)
         gen = BurstTrafficGen(args.datarate, args.minperiod, args.minsize,
                               maxsize=args.maxsize, peakduration=args.maxperiod, peakrate=args.datarate*args.fator,
                               start=1000)
         # gen = TrafficGen(args.minperiod * 1000/args.fator, args.maxperiod * 1000/args.fator, args.minsize, args.maxsize)
         nburst -= 1
      elif nping > 0:
          nping -= 1
          gen = PingGen(Um_Segundo, 64)
      # elif nconst > 0:
      #   gen = ConstantTrafficGen(20000, 200,65536)
      #   nconst -= 1
      else:
          gen = RateTrafficGen(args.datarate, args.minsize,
                           args.maxsize, 1000)
      sta = STA(env, args.rate, gen)
      sta.add_base(base, random.uniform(args.range/2, args.range))
      base.add_sta(sta)
      sta.start()

    t0 = time.time()
    tempo = args.t * 1000000
    base.start()
    if args.tdma:
        base.set_tdma()

    env.run(tempo)

    tu = base.u
    tru = base.ru
    tr = base.data_rate(tempo)
    nping = 0
    if args.base == 'ping':
        alat,mlat,Mlat = base.ping_lat.valores
        nping += 1
    else:
        alat,mlat,Mlat = 0,0,0
    if Debug or args.verbose: print('\n\nBase:', base.n, len(base.queue), base.N, base.curr_rate, alat,mlat,Mlat)
    # if Debug or args.verbose: print('\n\nBase:', base.n, len(base.queue), base.N, base.data_rate(tempo), alat,mlat,Mlat)
    # print('\n\nBase:', base.data_rate(Tempo), base.n, base.N, len(base.queue), alat,mlat,Mlat)
    lats = [Mlat]
    qm = len(base.queue)
    lost = base.ping_lat.lost
    rates = 0
    for sta in base.get_stations():
      tu += sta.u
      tru += sta.ru
      rates += sta.curr_rate
      tr += sta.data_rate(tempo)
      lat = (0,0,0)
      try:
          lat = sta.ping_lat.valores
          nping += 1
          lost += sta.ping_lat.lost
          alat += lat[0]
          mlat += lat[1]
          Mlat += lat[2]
          lats.append(lat[2])
      except Exception as e:
          # print(sta, e)
          pass
      qm += len(sta.queue)
      if Debug or args.verbose: print(sta, sta.n, len(sta.queue), sta.N, sta.curr_rate, sta.cols, lat[0], lat[1], lat[2])
      # if Debug or args.verbose: print(sta, sta.n, len(sta.queue), sta.N, sta.data_rate(tempo), lat[0], lat[1], lat[2])
      # if lat[0]: print(sta, sta.data_rate(tempo), sta.n, sta.N, len(sta.queue), sta.cols, lat[0], lat[1], lat[2])
      # else: print(sta, sta.data_rate(tempo), sta.n, sta.N, len(sta.queue), sta.cols)
    lats.sort()
    print('modo=%s, pps=%d, vazão média=%.2f, latências: média=%d, mín=%d, max=%d, perdas=%d' % (base.mode.name, base.currpps, rates, alat/nping, mlat/nping, Mlat/nping, lost))
    # print('modo=%s, pps=%d, vazão média=%.2f, latências: média=%d, mín=%d, max=%d, perdas=%d' % (base.mode.name, base.currpps, tr, alat/nping, mlat/nping, Mlat/nping, lost))
    # alat,mlat,Mlat = base.lat.valores
    # for sta in base.get_stations():
    #     a,m,M = sta.lat.valores
    #     alat += a
    #     mlat += m
    #     Mlat += M
    # N = args.nstas + 1
    # print(tr, alat/N, mlat/N, Mlat/N, base.pps)
    # print()