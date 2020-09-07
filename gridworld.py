from sarsa import Model,State,Action
from enum import Enum
from typing import Tuple

class Direction(Enum):
    Up = (0,-1)
    Down = (0,1)
    Right = (1,0)
    Left = (-1,0)
    UpRight = (1,-1)
    UpLeft = (-1,-1)
    DownRight = (1,1)
    DownLeft = (-1,1)
    Nope = (0,0)

class GridWorld(Model):

    Start = (0, 0)

    def __init__(self, ncols:int, nrows:int, **args):
        self.rows = nrows
        self.cols = ncols
        self._start = args.get('start', GridWorld.Start)
        self._goal = args.get('goal', (ncols-1, nrows-1))
        self._diagonal = args.get('diagonal', False)
        self._nomove = args.get('nomove', False)
        Model.__init__(self, **args)

    def __initialize__(self):
        for col in range(self.cols):
            for row in range(self.rows):
                pos = (col, row)
                s = State(pos)
                if col > 0:
                    s.add_action(Action(Direction.Left))
                    if self._diagonal:
                        if row > 0:
                            s.add_action(Action(Direction.UpLeft))
                        if row < self.rows-1:
                            s.add_action(Action(Direction.DownLeft))
                if col < self.cols-1:
                    s.add_action(Action(Direction.Right))
                    if self._diagonal:
                        if row > 0:
                            s.add_action(Action(Direction.UpRight))
                        if row < self.rows-1:
                            s.add_action(Action(Direction.DownRight))
                if row > 0:
                    s.add_action(Action(Direction.Up))
                if row < self.rows-1:
                    s.add_action(Action(Direction.Down))
                if self._nomove:
                    s.add_action(Action(Direction.Nope))
                self.states[pos] = s

        self.goal.final = True

    def __move__(self, s:State, a:Action)->Tuple[int,int]:
        col, row = s.n
        dc, dr = a.n.value
        col += dc
        row += dr
        return col,row

    def evaluate(self, s:State, a:Action)->Tuple[float,State]:
        col, row = self.__move__(s, a)
        stt = self.states[(col,row)]
        if stt.final: r = 0
        else: r = -1

        return r,stt

    @property
    def start(self):
        return self.states[self._start]

    @property
    def goal(self):
        return self.states[self._goal]

    def next(self, s: State=Start) -> State:
        a = s.pi
        col,row = self.__move__(s, a)
        return self.states[(col,row)]