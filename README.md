Robots
======

Robots is a very simple programming game that is loosely based on my memories of
[Robocom][0].  You, as a competitor, develop the software that controls an army
of Robots with the goal of dominating the playing field.

**Due to my overwhelming laziness, this software probably won't run on windows,
and probably has serious bugs related to interprocess communication that result
in deadlocks and the death of your firstborn child.  Use at your own risk!**

[0]: http://atlantis.cyty.com/robocom/

Installation
------------

Robots (the software) is divided into two major components: the interpreter, and
the user interface.  They communicate using a simple pipe based protocol.

Running the interpreter is the easy part, it has no external dependencies that I
can remember.

The user interface module requires a couple external dependencies, which can be
installed using whatever method you prefer.  It needs:

 * wxpython, and
 * pycairo

### Translating the Interpreter

The interpreter component happens to be mostly RPython, so it translates well
with [pypy][1].  Download PyPy's source, and run:

> $ pypy/pypy/translator/goal/translate.py /path/to/main.py

This *should* generate a file named main-c, which is a much faster version of
the interpreter.  If I ever get around to holding a tournament, I'll be using
the translated interpreter.

[1]: http://pypy.org/

Robot Specification
-------------------

### Software

The processor of a Robot is fairly simple.  It reads instructions and executes
them sequentially.  It also supports running multiple threads in parallel at the
cost of performance. The processor has three global registers, shared between all
threads, while each thread has two local registers.

Robots have a huge memory bank that can be used to store a nearly infinite number
of variables.  The memory bank is shared between threads.

### Hardware

Physically each Robot is a mobile factory, capable of building more Robots at
will.  Each robot also comes equipped with a scanner and a close range electron
beam programmer.  The scanner can detect the team and identifier of any
adjacent robots, and the electron beam programmer can transfer instructions into
adjacent robots.

Programs
--------

### Basic Format

Robots are programmed in an assembly like language, with one instruction per line.
Any text following an apostrophe will be ignored, and can be used as comments.

The first non-whitespace word on the line is the instruction.  Each whitespace
separated token after is an argument to the instruction.  For example:

> set L0 10

This line would store the value 10 in the register L0.

### Arguments

Arguments can refer to:

 * Local registers: 'L0' and 'L1';
 * Global registers: 'G0', 'G1', and 'G2'; and
 * Labels: ':main'.

There are also a couple defined quasi-constants, which begin with a '$':

 * $pc: The program counter;
 * $up, $right, $down, $left: Directions;
 * $success, $failure: Fairly obvious;
 * $parent, $child: Used with the fork command;
 * $eq, $ne, $lt, $le, $gt, $ge: Respectively ==, <>, <, <=, >, >=;
 * $id: The id of the current robot; and
 * $team: The team of the current robot

Arguments surrounded by parentheses are *relative arguments*.  For example:

> jump 0

would jump to the absolute position 0, while

> jump (0)

would jump back to right before the jump command, effectively hanging the robot.
Labels can also be used relatively.

See the examples in robots/examples for more information.

### Labels

A line beginning with a colon followed by any number of non-whitespace characters
is a label.  Labels can be used as arguments, and will be replaced by their
position in the code.  A label wrapped in parentheses will be replaced by the
offset from the current position to the label.  Effectively this lets you write
relocatable code.

Instruction Reference
---------------------

> go *direction*
> > Moves the robot in the direction specified.

> build *direction*
> > Builds a robot in the direction specified.  The newly created Robot will be
> > programmed with a single 'jump 0' instruction at position 0.

> jump *position*
> > Jumps to the specified instruction. Jumping past the end of the program will
> > kill the Robot.

> fork
> > Splits the flow of the process into two independent parts.  L0 will be set
> > to $parent in the parent thread, and $child in the child thread. Each new
> > thread consumes more resources and commands will run slower the more threads
> > are active.

> exit
> > Ends the current thread.  If the last remaining thread calls exit, L0 is set
> > to $failure and execution continues.

> if *cmp* *left* *right*
> > Runs the next instruction if the comparison returns True, otherwise skip the
> > next instruction. *cmp* may be any of $eq, $ne, $lt, $le, $gt, or $ge or any
> > argument that evaluates to those values.

> set *dest* *src*
> > Copy the value from *src* into *dest*

> add *dest* *src*
> sub *dest* *src*
> div *dest* *src*
> mul *dest* *src*
> > Perform a math operation between *dest* and *src* and store the value in
> > *dest*.

> xfer *direction* *src* *dest*
> > Transfer a single instruction at *src* in the local Robot to *dest* in the
> > remote Robot in the direction *direction*.  Sets L0 to $success or $failure.

> scan *direction*
> > Scans *direction* for robots.  Sets L0 to $failure if the space is empty, or
> > sets L0 to the team, and L1 to the id of the scanned robot.

> save *src* *variable*
> > Save the value *src* into the memory bank at the location specified by
> > *variable*.  *variable* is a special argument that may be any normal argument,
> > or a percent sign followed by the variable name, for example '%name'.

> load *dest* *variable*
> > Load the value *src* from the memory bank at the location specified by
> > *variable*.  *variable* is a special argument that may be any normal argument,
> > or a percent sign followed by the variable name, for example '%name'.
