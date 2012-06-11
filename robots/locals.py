#!/usr/bin/env python

#
# Constants
#

UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

SUCCESS = 1
FAILURE = 0

PARENT = 1
CHILD = 2

DIRECTIONS = {
    UP: (0, -1),
    RIGHT: (1, 0),
    DOWN: (0, 1),
    LEFT: (-1, 0),
}

EQUAL = 0
NOT_EQUAL = 1

LESS_THAN = 2
LESS_EQUAL = 3

GREATER_THAN = 4
GREATER_EQUAL = 5

#
# Utilities
#

class Counter:
    def __init__(self):
        self.next_id = 0

    def next(self):
        value = self.next_id
        self.next_id += 1
        return value

try:
    from pypy.rlib.rrandom import Random
    from time import time

    rand_counter = Counter()

    def randint(a, b):
        gen = Random(rand_counter.next())
        return int((gen.random() * (b - a)) + a)
except ImportError:
    from random import randint

#
# Logging
#
"""
def log(*args, **kwargs):
    args = list(args)
    message = args[0]
    del args[0]

    if 'prefix' in kwargs:
        message = kwargs['prefix'] + message
        del kwargs['prefix']
    if 'suffix' in kwargs:
        message = message + kwargs['suffix']
        del kwargs['suffix']
    if 'level' in kwargs:
        message = '  ' * kwargs['level'] + message
        del kwargs['level']


    print message.format(*args, **kwargs)

log_indent = 0
def log_enter(*args, **kwargs):
    global log_indent
    kwargs['level'] = log_indent
    kwargs['prefix'] = "Entering: " + (kwargs['prefix'] if 'prefix' in kwargs else '')
    log(*args, **kwargs)
    log_indent += 1

def log_exit(*args, **kwargs):
    global log_indent
    log_indent -= 1
    kwargs['level'] = log_indent
    kwargs['prefix'] = "Exiting: " + (kwargs['prefix'] if 'prefix' in kwargs else '')
    log(*args, **kwargs)
"""
def log_msg(msg):
    print msg
