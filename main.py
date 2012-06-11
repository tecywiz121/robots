#!/usr/bin/env python

from robots import *

def target(*args):
    return entry_point, None

def print_robot(robot):
    print 'Identifier:', robot.id
    print 'Team:      ', robot.team
    print 'Status:    ', 'Dead' if robot.dead else 'Alive'
    if robot.dead:
        print 'Reason:    ', robot.murder_weapon
    print 'Position:  ', robot.position
    print 'Registers: ', robot.registers
    print 'Memory:    ', robot.memory

    for idx, thread in enumerate(robot.threads):
        try:
            inst = robot.program[thread.program_counter]
        except IndexError:
            inst = Instruction()
        print 'Thread', idx
        print '       Locals:', thread.registers
        print '      Counter:', thread.program_counter
        print '  Instruction:', inst,
        if inst.duration:
            print '({}%)'.format(round(thread.progress/inst.duration * 100))
        else:
            print
    print

def entry_point(argv):
    debug = False # Set to true to get useful debugging information (keep False for PyPy)

    if len(argv) > 1:
        # Start in stand alone mode
        width = int(argv[1])
        height = int(argv[2])

        world = World(width, height, debug=debug)
        placed = [(-1, -1)]
        for team, arg in enumerate(argv[3:]):
            parser = Parser()

            position = (-1, -1)
            while position in placed:
                position = (randint(0, width), randint(0, height))

            wall_e = Robot()
            wall_e.team = team + 1
            wall_e.program = parser.parse(arg)
            wall_e.position = position

            world.add_robot(wall_e)


        while not world.is_over():
            if debug:
                results = list(world.robots)
                results.extend(world.dead)
                world.dead = [] # Clear the list to keep clutter down
                results.sort(lambda x,y: cmp(x.id, y.id) if cmp(x.team, y.team) == 0 else cmp(x.team, y.team))
                for robot in results:
                    print_robot(robot)
                raw_input()

            world.tick()

        if debug:
            for robot in world.dead:
                print robot.murder_weapon_long
    else:
        # Start in server mode
        from robots.server import Server
        server = Server()
        server.run()
    return 0

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
