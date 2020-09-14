from sarsa import State,Action,Model,Sarsa,QLearn,ExpSarsa
from typing import Tuple
from hibrido import STA,Base,Modo
from trafficgen import *
import math
from mysim import Engine

class MacAdaptativo(Model):
    PPS_Inc = 10
    PPS_Max = 2000
    Alfa = 0.5

    def __init__(self, base:Base, **args):
        '''
        :param base: a base da rede ptmp
        :param args: argumentos opcionais:
        * *pps_inc* (``int``) --
          incrementos no PPS para os estados
        * *pps_max* (``int``) --
          Maior valor de PPS considerado nos estados
        * *alfa* (``float``) --
          Fator para ponderação para EWMA do PPS
        '''
        self._base = base
        self._ppsinc = args.get('pps_inc', MacAdaptativo.PPS_Inc)
        self._ppsmax = args.get('pps_max', MacAdaptativo.PPS_Max)
        self._alfa = args.get('alfa', MacAdaptativo.Alfa)
        self._rate = 0
        Model.__init__(self, **args)

    def __initialize__(self):
        for pps in range(0, self._ppsmax, self._ppsinc):
            for n in range(1, 1+self.base.num_clients):
                val = (pps,n)
                s = State(val)
                s.add_action(Action(Modo.TDMA))
                s.add_action(Action(Modo.CSMA))
                self.states[val] = s

    def evaluate(self, s:State, a:Action)->Tuple[float,State]:
        pps = self.base.pps # a recompensa é o pps atual ??!!
        # calcula PPS médio
        self._rate = pps*self._alfa + (1-self._alfa)*self._rate
        rate = min(math.floor(self._rate/self._ppsinc)*self._ppsinc, self._ppsmax)
        n = self._base.num_clients # normalmente não muda, mas deve-se considerar uma rede em que cpes variam
        stt = self.states[(rate,n)]
        return pps,stt


    def next(self, s:State)->State:
        pass