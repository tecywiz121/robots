#!/usr/bin/env python

from locals import *

#
# Values
#

class Value(object):
    def get(self, robot):
        raise Exception('Value not readable')

    def set(self, robot, value):
        raise Exception('Value not writable')

    def __repr__(self):
        return '{*}'

class Constant(Value):
    def __init__(self, value):
        self.value = value

    def get(self, robot):
        return self.value

    def __repr__(self):
        if self in Parser.REVERSED_CONSTANTS:
            return '$' + Parser.REVERSED_CONSTANTS[self]
        return repr(self.value)

class Variable(Value):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '%' + self.name

class Label(Constant):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return super(Label, self).__repr__() + ':' + self.name

class Register(Value):
    def __init__(self, id):
        self.id = id

    def get(self, robot):
        return robot.get_local(self.id)

    def set(self, robot, value):
        return robot.set_local(self.id, value)

    def __repr__(self):
        return 'L{0!r}'.format(self.id)

class Global(Value):
    def __init__(self, id):
        self.id = id

    def get(self, robot):
        return robot.get_global(self.id)

    def set(self, robot, value):
        return robot.set_global(self.id, value)

    def __repr__(self):
        return 'G{0!r}'.format(self.id)

class Team(Value):
    def get(self, robot):
        return robot.team

    def __repr__(self):
        return '$team'

class Identifier(Value):
    def get(self, robot):
        return robot.id

    def __repr__(self):
        return '$id'

class ProgramCounter(Value):
    def get(self, robot):
        return robot.get_program_counter()

    def __repr__(self):
        return '$pc'

class RelativeValue(Value):
    def __init__(self, value):
        self.value = value

    def get(self, robot):
        return self.value.get(robot) + robot.get_program_counter()

    def __repr__(self):
        return '(' + repr(self.value) + ')'

#
# Instructions
#

class Instruction(object):
    duration = 0
    def __init__(self, args=None):
        pass

    def execute(self, robot):
        raise Exception('Invalid instruction')

    def __repr__(self):
        return '-inv-'

class Move(Instruction):
    duration = 10

    def __init__(self, args):
        self.direction = args[0]

    def execute(self, robot):
        # Get variables
        direction = self.direction.get(robot)

        # Calculate offset and destination
        offset = DIRECTIONS[direction]
        destination = robot.p_sum(robot.position, offset)
        if robot.passable(destination):
            robot.position = destination
            robot.result(SUCCESS)
        else:
            robot.result(FAILURE)

    def __repr__(self):
        return 'go {0!r}'.format(self.direction)

class Clone(Instruction):
    duration = 100

    def __init__(self, args):
        self.direction = args[0]

    def execute(self, robot):
        # Get variables
        direction = self.direction.get(robot)

        # Calculate offset and destination
        offset = DIRECTIONS[direction]
        destination = robot.p_sum(robot.position, offset)

        # Make sure destination is empty
        if not robot.passable(destination):
            robot.result(FAILURE) # Something is in the way!
            return

        child = robot.clone(True)
        child.position = destination
        child.program = [Jump([Constant(0)])]
        robot.result(SUCCESS)

    def __repr__(self):
        return 'build {0!r}'.format(self.direction)

class Jump(Instruction):
    def __init__(self, args):
        self.dest = args[0]

    def execute(self, robot):
        robot.set_program_counter(self.dest.get(robot) - 1) # PC is incremented after jump

    def __repr__(self):
        return 'jump {0!r}'.format(self.dest)

class Fork(Instruction):
    duration = 1

    def execute(self, robot):
        thread = robot.get_thread()
        new = thread.clone()
        new.program_counter += 1
        new.set(0, CHILD)       # Set return value to child
        thread.set(0, PARENT)   # Set return value to parent
        robot.threads.append(new)

    def __repr__(self):
        return 'fork'

class Exit(Instruction):
    def execute(self, robot):
        if len(robot.threads) > 1:
            robot.threads[robot.thread_id] = None
        else:
            robot.result(FAILURE)

    def __repr__(self):
        return 'exit'

class SkipIfFalse(Instruction):
    def __init__(self, args):
        mode, arg1, arg2 = args
        self.mode = mode
        self.arg1 = arg1
        self.arg2 = arg2

    def execute(self, robot):
        # Get variables
        mode = self.mode.get(robot)
        arg1 = self.arg1.get(robot)
        arg2 = self.arg2.get(robot)

        # Lookup Comparison
        if mode == EQUAL:
            r = arg1 == arg2
        elif mode == NOT_EQUAL:
            r = arg1 <> arg2
        elif mode == LESS_THAN:
            r = arg1 < arg2
        elif mode == LESS_EQUAL:
            r = arg1 <= arg2
        elif mode == GREATER_THAN:
            r = arg1 > arg2
        elif mode == GREATER_EQUAL:
            r = arg1 >= arg2
        else:
            raise Exception('Unknown comparison mode')

        if not r:
            robot.set_program_counter(robot.get_program_counter() + 1)

    def __repr__(self):
        return 'if {0!r} {1!r} {2!r}'.format(self.mode, self.arg1, self.arg2)

class Memory(Instruction):
    def __init__(self, args):
        dest, src = args
        self.dest = dest
        self.src = src

    def execute(self, robot):
        self.dest.set(robot, self.src.get(robot))

    def __repr__(self):
        return 'set {0!r} {1!r}'.format(self.dest, self.src)

class Add(Instruction):
    def __init__(self, args):
        dest, src = args
        self.dest = dest
        self.src = src

    def execute(self, robot):
        dest = self.dest.get(robot)
        src = self.src.get(robot)

        result = dest + src

        self.dest.set(robot, result)

    def __repr__(self):
        return 'add {0!r} {1!r}'.format(self.dest, self.src)

class Subtract(Instruction):
    def __init__(self, args):
        dest, src = args
        self.dest = dest
        self.src = src

    def execute(self, robot):
        dest = self.dest.get(robot)
        src = self.src.get(robot)

        result = dest - src

        self.dest.set(robot, result)

    def __repr__(self):
        return 'sub {0!r} {1!r}'.format(self.dest, self.src)

class Multiply(Instruction):
    def __init__(self, args):
        dest, src = args
        self.dest = dest
        self.src = src

    def execute(self, robot):
        dest = self.dest.get(robot)
        src = self.src.get(robot)

        result = dest * src

        self.dest.set(robot, result)

    def __repr__(self):
        return 'mul {0!r} {1!r}'.format(self.dest, self.src)

class Divide(Instruction):
    def __init__(self, args):
        dest, src = args
        self.dest = dest
        self.src = src

    def execute(self, robot):
        dest = self.dest.get(robot)
        src = self.src.get(robot)

        if src == 0:
            raise Exception('Division by zero')

        result = dest / src

        self.dest.set(robot, result)

    def __repr__(self):
        return 'div {0!r} {1!r}'.format(self.dest, self.src)

class Transfer(Instruction):
    duration = 2

    def __init__(self, args):
        direction, src, dest = args
        self.direction = direction
        self.src = src
        self.dest = dest

    def execute(self, robot):
        # Get variables
        direction = self.direction.get(robot)
        src = self.src.get(robot)
        dest = self.dest.get(robot)

        # Calculate offset, target position
        offset = DIRECTIONS[direction]
        position = robot.p_sum(robot.position, offset)
        target = robot.at(position)

        if not target:
            robot.result(FAILURE)
            return

        if dest < 0:
            raise Exception('Cannot transfer before start of memory')

        if dest >= len(target.program):
            target.program.extend([Instruction()] * (dest - len(target.program) + 1))
        target.program[dest] = robot.program[src]
        robot.result(SUCCESS)

    def __repr__(self):
        return 'xfer {0!r} {1!r} {2!r}'.format(self.direction, self.src, self.dest)

class Scan(Instruction):
    duration = 1

    def __init__(self, args):
        self.direction = args[0]

    def execute(self, robot):
        # Get variables
        direction = self.direction.get(robot)

        # Get target
        offset = DIRECTIONS[direction]
        position = robot.p_sum(robot.position, offset)
        target = robot.at(position)

        if not target:
            robot.result(FAILURE)
            return

        robot.set_local(0, target.team)
        robot.set_local(1, target.id)

    def __repr__(self):
        return 'scan {0!r}'.format(self.direction)

class Save(Instruction):
    duration = 1

    def __init__(self, args):
        value, location = args
        self.location = location
        self.value = value

    def execute(self, robot):
        # Get variables
        if isinstance(self.location, Variable):
            location = '%' + self.location.name
        else:
            location = str(self.location.get(robot))
        value = self.value.get(robot)

        # Save the value
        robot.memory[location] = value

    def __repr__(self):
        return 'save {!r} {!r}'.format(self.value, self.location)

class Load(Instruction):
    duration = 1

    def __init__(self, args):
        dest, location = args
        self.dest = dest
        self.location = location

    def execute(self, robot):
        # Get variables
        if isinstance(self.location, Variable):
            location = '%' + self.location.name
        else:
            location = str(self.location.get(robot))

        # Load the value
        self.dest.set(robot, robot.memory[location])

    def __repr__(self):
        return 'load {!r} {!r}'.format(self.dest, self.location)

#
# Parser
#

class Parser(object):
    COMMAND_MAP = {
        'go': Move,
        'build': Clone,
        'jump': Jump,
        'fork': Fork,
        'exit': Exit,
        'if': SkipIfFalse,
        'set': Memory,
        'add': Add,
        'sub': Subtract,
        'div': Divide,
        'mul': Multiply,
        'xfer': Transfer,
        'scan': Scan,
        'save': Save,
        'load': Load,
    }

    CONSTANTS = {
        'up': Constant(UP),
        'down': Constant(DOWN),
        'right': Constant(RIGHT),
        'left': Constant(LEFT),

        'success': Constant(SUCCESS),
        'failure': Constant(FAILURE),

        'parent': Constant(PARENT),
        'child': Constant(CHILD),

        'eq': Constant(EQUAL),
        'ne': Constant(NOT_EQUAL),

        'lt': Constant(LESS_THAN),
        'le': Constant(LESS_EQUAL),

        'gt': Constant(GREATER_THAN),
        'ge': Constant(GREATER_EQUAL),

        'id': Identifier(),
        'team': Team(),
        'pc': ProgramCounter(),
    }

    def __init__(self):
        self.labels = {}
        self.relatives = []
        self.position = 0
        self.program = []

    def parse_string(self, string):
        for x in string.split('\n'):
            self.parse_line(x)
        return self.finalize()

    def finalize(self):
        for pos, relval in self.relatives:
            inner = relval.value
            if isinstance(inner, Label):
                relval.value = Label(inner.name, inner.value-pos)
        return self.program

    def parse_line(self, line):
        line = line.strip(' ').strip('\n')
        if not line or line[0] == '\'':
            return

        # Remove comments
        idx = line.find("'")
        if idx >= 0:
            line = line[:idx]

        if line[0] == ':':
            label = line[1:]
            if label in self.labels:
                if self.labels[label].value <> -1:
                    raise Exception('Duplicate label')
                self.labels[label].value = self.position
            else:
                self.labels[label] = Label(label, self.position)
            return

        parts = [x for x in line.split(' ') if x]
        cmd = parts[0]
        args_str = parts[1:]

        args = []
        for x in args_str:
            args.append(self.parse_arg(x))

        opcode = self.COMMAND_MAP[cmd.lower()]
        self.position += 1
        self.program.append(opcode(args))

    def parse_arg(self, arg):
        det = arg[0].upper()
        val = arg[1:].lower()
        relative = False

        # Check if argument is supposed to be relative
        if det == '(':
            if len(arg) < 3:
                raise Exception('No variable name supplied')
            relative = True
            det = arg[1].upper()            # Chop off the '(' and ')'
            val = arg[2:]
            val = val[:-1].lower()

        result = self._parse_arg(det, val)  # Actually parse the argument

        if relative:
            result = RelativeValue(result)
            self.relatives.append((self.position, result))
        return result

    def _parse_arg(self, det, val):
        if det == 'L':
            return Register(int(val))
        elif det == '%':
            return Variable(val)
        elif det == 'G':
            return Global(int(val))
        elif det == '$':
            return self.CONSTANTS[val]
        elif det == ':':
            try:
                label = self.labels[val]
            except KeyError:
                label = Label(val, -1)
                self.labels[val] = label
            return label
        else:
            return Constant(int(det+val))

# Lookup table to show constants in repr for instructions
Parser.REVERSED_CONSTANTS = dict((value, key) for key, value in Parser.CONSTANTS.iteritems())

try:
    from pypy.rlib.streamio import DiskFile
    import os

    def __parse(self, path):
        fd = os.open(path, os.O_RDONLY, 0777)
        f = DiskFile(fd)
        try:
            data = f.readall()
            lines = data.split('\n')
            for x in lines:
                self.parse_line(x)
            return self.finalize()
        finally:
            f.close()
    Parser.parse = __parse

except ImportError:
    def __parse(self, path):
        with file(path) as f:
            for x in f.readlines():
                self.parse_line(x)
        return self.finalize()
    Parser.parse = __parse
