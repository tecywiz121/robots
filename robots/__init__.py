#!/usr/bin/env python
from locals import *
from instructions import *

import traceback
try:
    from pypy.rlib.objectmodel import we_are_translated
except ImportError:
    def we_are_translated():
        return False

def format_exc(e):
    if we_are_translated():
        return ''
    else:
        return traceback.format_exc(e)

class Thread:
    def __init__(self):
        self.program_counter = 0
        self.registers = [0, 0]
        self.progress = 0

    def clone(self):
        new = Thread()
        new.program_counter = self.program_counter
        new.registers = list(self.registers)
        return new

    def set(self, idx, value):
        self.registers[idx] = value

    def get(self, idx):
        return self.registers[idx]

    def execute(self, robot, deltaT):
        pc = self.program_counter
        if pc < 0 or pc >= len(robot.program):
            raise Exception("Out of program bounds")
        current = robot.program[pc]
        self.progress += deltaT
        if self.progress >= current.duration:
            current.execute(robot)
            self.progress = 0
            self.program_counter += 1

class World(object):
    dead = []
    robots = {} # Can't use sets in RPython, so use a dict instead :(
    teams = {}

    def __init__(self, width, height, debug=False):
        self.debug = debug
        self.width = width
        self.height = height

    def is_over(self):
        if len(self.robots) <= 1:
            return True

        active = False
        for team in self.teams.itervalues():
            if len(team) > 0:
                if active:
                    return False
                else:
                    active = True
        return active

    def add_robot(self, robot):
        if robot.team == 0:
            raise Exception('Team number must not be 0')

        self.robots[robot] = True
        robot.world = self
        try:
            self.teams[robot.team][robot] = True
        except KeyError:
            self.teams[robot.team] = {robot: True}

    def tick(self):
        robots = list(self.robots.keys())
        for robot in robots:
            try:
                robot.tick()
            except Exception as e:
                log_msg("Robot " + str(robot.id) + " Died!")
                if self.debug:
                    robot.murder_weapon_long = format_exc(e)
                robot.murder_weapon = str(e)
                robot.dead = True
                del self.robots[robot]
                del self.teams[robot.team][robot]
                self.dead.append(robot)


    def run(self, count=-1):
        if count<0:
            while not self.is_over():
                self.tick()
        else:
            while not self.is_over() and count >= 0:
                count -= 1
                self.tick()

    def passable(self, pos):
        for x in self.robots:
            if not x.dead and x.position == pos:
                return False
        return True

    def at(self, pos):
        for x in self.robots:
            if x.position == pos:
                return x
        return None

    def p_sum(self, pos, off):
        return ((pos[0]+off[0]) % self.width,
                (pos[1]+off[1]) % self.height)

class Robot(object):
    counter = Counter()

    def __init__(self):
        self.team = -1
        self.world = None
        self.position = (0, 0)

        self.program = []
        self.threads = [Thread()]
        self.thread_id = 0
        self.registers = [0, 0, 0]
        self.dead = False
        self.memory = {}

        self.id = Robot.counter.next()

    def tick(self):
        threads = list(self.threads)    # so new threads don't mess things up
        tick = 1.0 / len(threads)       # Time allocated to each thread

        for idx, thread in enumerate(threads):
            self.thread_id = idx
            self.get_thread().execute(self, tick)

        self.threads = [x for x in self.threads if x] # Clean out deleted threads

    def result(self, value):
        """Set the result register of the current thread"""
        self.set_local(0, value)

    def clone(self, empty=False):
        """Create an exact copy of the robot"""
        new = Robot()
        new.team = self.team
        new.position = self.position        # Tuples are immutable
        if not empty:
            new.program = list(self.program)    # Programs can be modified independently (but instructions are immutable)
            new.threads = [x.clone() for x in self.threads] # Threads can be modified
            new.thread_id = self.thread_id      # Integer
            new.registers = list(self.registers)
            new.memory = self.memory.copy()
        self.world.add_robot(new)
        return new


    def passable(self, pos):
        """Return True if the target position is passable, False otherwise"""
        return self.world.passable(pos)

    def get_local(self, id):
        """Return the value of the thread-local register specified by id"""
        return self.get_thread().get(id)

    def set_local(self, id, value):
        """Set the value of the thread-local register specified by id"""
        self.get_thread().set(id, value)

    def get_global(self, id):
        """Return the value of the shared register specified by id"""
        return self.registers[id]

    def set_global(self, id, value):
        """Set the value of the shared register specified by id"""
        self.registers[id] = value

    def at(self, pos):
        """Return the object located at the position specified"""
        return self.world.at(pos)

    def get_program_counter(self):
        """The thread-local index of the current instruction"""
        return self.get_thread().program_counter

    def set_program_counter(self, value):
        self.get_thread().program_counter = value

    def get_thread(self):
        """The currently executing thread"""
        return self.threads[self.thread_id]

    def p_sum(self, pos, off):
        return self.world.p_sum(pos, off)
