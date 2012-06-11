#!/usr/bin/env python

from . import *

class Server(object):
    def __init__(self):
        self.running = True
        self.debug = False
        self.placed = [(-1, -1)]
        self.ticks = 0

    def read_cmd(self):
        cmd = False
        while not cmd:
            cmd = self.readline().lower()
        lines = []

        if cmd[-1] == ':':
            cmd = cmd[:-1]
            line = ' '
            while line <> '':
                lines.append(line)
                line = self.readline()
            lines = lines[1:]
        return (cmd, lines)

    def send_cmd(self, cmd, args=[]):
        if args:
            cmd += ':\n' + '\n'.join(args) + '\n'
        self.writeline(cmd)


    def run(self):
        while self.running:
            cmd, args = self.read_cmd()
            func = self.CMD_MAP[cmd]
            func(self, args)

    def cmd_quit(self, args):
        assert(len(args) == 0)
        self.running = False

    def cmd_size(self, args):
        assert(len(args) == 2)
        width = int(args[0])
        height = int(args[1])
        self.world = World(width, height, debug=self.debug)

    def cmd_debug(self, args):
        assert(len(args) in (0, 1))
        if len(args) == 0:
            self.debug = True
        else:
            self.debug = bool(args[0])

    def cmd_load(self, args):
        for arg in args:
            team_s, path = arg.split(' ', 1)
            team = int(team_s)

            parser = Parser()
            program = parser.parse(path)

            position = (-1, -1)
            while position in self.placed:
                position = (randint(0, self.world.width), randint(0, self.world.height))

            wall_e = Robot()
            wall_e.position = position
            wall_e.program = program
            wall_e.team = team
            self.world.add_robot(wall_e)

    def cmd_tick(self, args):
        assert(len(args) in (0, 1))
        if args:
            count = int(args[0])
        else:
            count = 1

        for x in range(count):
            self.world.tick()
            self.ticks += 1

            if self.world.is_over():
                break

        robots = []
        for robot in self.world.robots:
            robots.append(' '.join([str(robot.id),
                                    str(robot.team),
                                    str(robot.position[0]),
                                    str(robot.position[1])]))
        self.send_cmd('robots', robots)

    def cmd_status(self, args):
        assert(len(args), 0)
        cmd = 'running'
        if self.world.is_over():
            cmd = 'end'
        self.send_cmd(cmd, [str(self.ticks)])


Server.CMD_MAP = dict((name[4:], getattr(Server, name)) for name in dir(Server) if name.startswith('cmd_'))

try:
    from pypy.rlib.streamio import DiskFile

    __io = DiskFile(0)
    def __readline(self):
        return self.io.readline().rstrip('\n')

    def __writeline(self, text):
        print text
        # self.io.write(text + '\n')
    Server.io = __io
    Server.readline = __readline
    Server.writeline = __writeline

except ImportError:
    def __readline(self):
        return raw_input()

    def __writeline(self, text):
        print text

    Server.readline = __readline
    Server.writeline = __writeline
