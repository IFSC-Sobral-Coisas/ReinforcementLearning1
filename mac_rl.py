from sarsa import State,Action,Model,Sarsa,QLearn,ExpSarsa
from typing import Tuple
from hibrido import STA,Base,Modo
from trafficgen import *
import math
from mysim import Engine
import argparse

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
        self._frames = 0
        self._lost = 0
        Model.__init__(self, **args)

    def __initialize__(self):
        for pps in range(0, self._ppsmax, self._ppsinc):
            for n in range(1, 1+self._base.num_clients):
                val = (pps,n)
                s = State(val)
                s.add_action(Action(Modo.TDMA))
                s.add_action(Action(Modo.CSMA))
                self.states[val] = s

    def __calc_pps__(self, pps:int)->int:
        return min(math.floor(pps/self._ppsinc)*self._ppsinc, self._ppsmax)

    @property
    def currstate(self)->State:
        try:
            pps = self.__calc_pps__(self._base.currpps)
        except:
            pps = 0
        return self.states[(pps,self._base.num_clients)]

    def evaluate(self, s:State, a:Action)->Tuple[float,State]:
        pps = self._base.frames - self._frames
        lost = self._base.cols - self._lost
        self._lost = self._base.cols
        self._frames = self._base.frames
        # r = pps - lost
        r = -lost
        # pps = self._base.pps # a recompensa é o pps atual ??!!
        lat = self._base.currlatency
        # if not lat: lat=3 # ref: 1000 us
        # else: lat = math.log10(lat)-3
        # r /= lat
        lat = min(lat/10, 1000000)
        r -= lat
        # r = pps - self._rate # recompensa é a diferença entre pps atual, e o pps médio
        # r = self.__calc_pps__(abs(r))*math.copysign(1,r)
        # calcula PPS médio
        self._rate = pps*self._alfa + (1-self._alfa)*self._rate
        rate = self.__calc_pps__(self._rate)
        n = self._base.num_clients # normalmente não muda, mas deve-se considerar uma rede em que cpes variam
        stt = self.states[(rate,n)]
        # print('eval:', s.n, stt.n, pps, s.amax.n.name, r, lat)
        return r,stt


    def next(self, s:State)->State:
        pass

if __name__ == '__main__':
    import time

    Rate = 150 # 150 Mbps
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
    Step = 200
    Um_Segundo = 1000000
    Debug = False

    parser = argparse.ArgumentParser(description='Simulador 802.11n híbrido, com Aprendizagem por Reforço')
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
    parser.add_argument('-r', '--rate', help='Taxa de dados, em Mbps (default=%d)' % Rate, type=int, dest='rate', required=False,
                        default=Rate)
    parser.add_argument('-T', '--step', help='Duração de episódios do RL, em milissegundos (default=%d)' % Step, type=int, dest='step', required=False,
                        default=Step)
    parser.add_argument('--ppsinc', help='Granularidade do PPS para o RL (default=%d)' % MacAdaptativo.PPS_Inc, type=int, dest='pps_inc', required=False,
                        default=MacAdaptativo.PPS_Inc)
    parser.add_argument('--ppsmax', help='Valor máximo de PPS para o RL (default=%d)' % MacAdaptativo.PPS_Max, type=int, dest='pps_max', required=False,
                        default=MacAdaptativo.PPS_Max)
    parser.add_argument('--epsilon', help='Valor de epsilon, para policy e-greedy do RL (default=%.1f)' % Model.Epsilon, type=float, dest='epsilon', required=False,
                        default=Model.Epsilon)
    parser.add_argument('--alfa', help='Valor de alfa, para Sarsa (default=%.1f)' % Sarsa.Alfa, type=float, dest='alfa', required=False,
                        default=Sarsa.Alfa)
    parser.add_argument('--gamma', help='Valor de gamma, para Sarsa (default=%.1f)' % Sarsa.Gamma, type=float, dest='gamma', required=False,
                        default=Sarsa.Gamma)
    parser.add_argument('--beta', help='Valor de beta, para EWMA do PPS (default=%.1f)' % MacAdaptativo.Alfa, type=float, dest='beta', required=False,
                        default=MacAdaptativo.Alfa)
    parser.add_argument('--debug', help='Ativa debug', dest='debug', required=False, action='store_true')
    parser.add_argument('--policy', help='Mostra policy ao final', dest='policy', required=False, action='store_true')
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
         gen = TrafficGen(args.minperiod * 1000/args.fator, args.maxperiod * 1000/args.fator, args.minsize, args.maxsize)
         nburst -= 1
      elif nping > 0:
          nping -= 1
          gen = PingGen(Um_Segundo, 64)
      # elif nconst > 0:
      #   gen = ConstantTrafficGen(20000, 200,65536)
      #   nconst -= 1
      else:
          gen = TrafficGen(args.minperiod * 1000, args.maxperiod * 1000, args.minsize,
                           args.maxsize)
      sta = STA(env, args.rate, gen)
      sta.add_base(base, random.uniform(args.range/2, args.range))
      base.add_sta(sta)
      sta.start()

    t0 = time.time()
    tempo = args.t * 1000000
    step = args.step * 1000
    base.start()

    modelo = MacAdaptativo(base, pps_inc=args.pps_inc, pps_max=args.pps_max, alfa=args.beta, epsilon=args.epsilon)
    algo = ExpSarsa(modelo, gamma=args.gamma, alfa=args.alfa)
    t0 = step
    s = modelo.currstate
    while t0 <= tempo:
        env.run(t0)
        if t0 > 5000000: # 5 segundos
            s,a = algo.evaluate(s)
            base.set_mode(a.n)
        # print(s.n, a)
        t0 += step

    tu = base.u
    tru = base.ru
    tr = base.data_rate(tempo)
    nping = 0
    if args.base == 'ping':
        alat,mlat,Mlat = base.ping_lat.valores
        nping += 1
    else:
        alat,mlat,Mlat = 0,0,0
    if Debug or args.verbose: print('\n\nBase:', base.n, len(base.queue), base.N, base.data_rate(tempo), alat,mlat,Mlat)
    # print('\n\nBase:', base.data_rate(Tempo), base.n, base.N, len(base.queue), alat,mlat,Mlat)
    lats = [Mlat]
    qm = len(base.queue)
    lost = base.ping_lat.lost
    for sta in base.get_stations():
      tu += sta.u
      tru += sta.ru
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
      if Debug or args.verbose: print(sta, sta.n, len(sta.queue), sta.N, sta.data_rate(tempo), lat[0], lat[1], lat[2])
      # if lat[0]: print(sta, sta.data_rate(tempo), sta.n, sta.N, len(sta.queue), sta.cols, lat[0], lat[1], lat[2])
      # else: print(sta, sta.data_rate(tempo), sta.n, sta.N, len(sta.queue), sta.cols)
    lats.sort()
    print(base.currpps, tr, alat/nping, mlat/nping, Mlat/nping, lats[-1], qm/args.nstas, lost)
    alat,mlat,Mlat = base.lat.valores
    for sta in base.get_stations():
        a,m,M = sta.lat.valores
        alat += a
        mlat += m
        Mlat += M
    N = args.nstas + 1
    print(tr, alat/N, mlat/N, Mlat/N, base.currpps)

    if args.policy:
        # print('%10s %16s %16s,%.3f,%.3f,%d ')
        for s in modelo.states.values():
            n = 0
            for a,p in s.policy_dist:
                n += (a.count > 0)
            if not n: continue
            print(s.n, s.amax.n.name, end=' ')
            for a, p in s.policy_dist:
                print('%s %.2f %.2f, %d' % (a.n.name, a.q, p, a.count), end=', ')
            print('')
