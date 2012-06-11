#!/usr/bin/env python

from protocol import read_cmd

def target(*args):
    return entry_point, None

def entry_point(argv):
    print read_cmd()
    return 0

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
