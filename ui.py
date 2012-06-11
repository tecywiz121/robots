#!/usr/bin/env python

import wx
from wx.lib import wxcairo
import cairo
from math import pi
import subprocess
import sys
from select import select, PIPE_BUF
import fcntl
import os
from os.path import abspath

def get_bitmap(id):
    return wx.ArtProvider.GetBitmap(id)

class Robot(object):
    COLORS = [
        (0, 0, 0),
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 1, 0),
        (1, 0, 1),
        (0, 1, 1),
    ]

    def __init__(self, id, team, x, y):
        self.id = int(id)
        self.team = int(team)
        self.position = (int(x), int(y))

    def __repr__(self):
        return 'Robot({}, {}, {}, {})'.format(self.id, self.team, self.position[0], self.position[1])

    def to_grid(self):
        return (Robot.COLORS[self.team], self.position)

class Backend(object):
    def __init__(self, target):
        self.target = target
        self.send_buffer = ''
        self.recv_buffer = ''
        self.server = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def stop(self):
        if self.server:
            self.server.terminate()

    def start(self):
        p = subprocess.Popen(self.target, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=sys.stderr)
        self.server = p

        # Make reads non-blocking
        fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)


    def size(self, width, height):
        self.send_cmd('size', [width, height])

    def debug(self):
        self.send_cmd('debug')

    def tick(self, number=None):
        if number is None:
            self.send_cmd('tick')
        else:
            self.send_cmd('tick', [number])
        cmd = False
        while cmd <> 'robots':
            cmd, args = self.read_cmd()
        return [Robot(*x.split()) for x in args]

    def quit(self):
        self.send_cmd('quit')

    def status(self):
        self.send_cmd('status')
        cmd = False
        while cmd not in ('running', 'end'):
            cmd, args = self.read_cmd()
        return cmd

    def load(self, teams):
        self.send_cmd('load', [str(team) + ' ' + path for team, path in teams])

    def writeline(self, text):
        self.send_buffer += text + '\n'
        while self.send_buffer:
            self.communicate()


    def readline(self):
        while '\n' not in self.recv_buffer:
            self.communicate()
        line, self.recv_buffer = self.recv_buffer.split('\n', 1)
        return line

    def send_cmd(self, cmd, args=None):
        if args:
            cmd += ':\n' + '\n'.join(str(x) for x in args) + '\n'
        self.writeline(cmd)

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

    def communicate(self):
        stdin = [self.server.stdin] if self.send_buffer else []
        stdout = [self.server.stdout]
        (rlist, wlist, xlist) = select(stdout, stdin, [])

        if rlist:
            self.recv_buffer += rlist[0].read()

        if wlist:
            to_write = self.send_buffer[:PIPE_BUF]
            self.send_buffer = self.send_buffer[PIPE_BUF:]
            wlist[0].write(to_write)

class CairoGrid(wx.Panel):
    def __init__(self, *args, **kwargs):
        try:
            self.grid_cols = kwargs['cols']
            del kwargs['cols']
        except KeyError:
            pass

        try:
            self.grid_rows = kwargs['rows']
            del kwargs['rows']
        except KeyError:
            pass

        super(CairoGrid, self).__init__(*args, **kwargs)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.points = []

    def OnSize(self, event):
        self.Refresh()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        ctx = wxcairo.ContextFromDC(dc)

        # Clear Background
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()

        self.DrawGrid(ctx)
        self.DrawPoints(ctx)

    def DrawGrid(self, ctx):
        x1, y1, x2, y2 = ctx.clip_extents()
        width = x2 - x1
        height = y2 - y1

        col_size = width / self.grid_cols
        row_size = height / self.grid_rows

        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1)
        ctx.translate(-0.5, -0.5)

        for col in range(self.grid_cols):
            ctx.move_to(col * col_size, 0)
            ctx.line_to(col * col_size, height)
            ctx.stroke()

        for row in range(self.grid_rows):
            ctx.move_to(0, row * row_size)
            ctx.line_to(width, row * row_size)
            ctx.stroke()

    def DrawPoints(self, ctx):
        width, height = self.GetSize()
        col_size = width / float(self.grid_cols)
        row_size = height / float(self.grid_rows)

        radius = min(col_size, row_size) / 2
        radius *= 0.95

        for color, (col, row) in self.points:
            ctx.set_source_rgb(*color)
            x = (col * col_size) + col_size/2.0
            y = (row * row_size) + row_size/2.0

            ctx.arc(x, y, radius, 0, 2*pi)
            ctx.fill()

class MainWindow(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.interpreter = './main-c'

        self.BuildUI()

        self.timer = wx.Timer(self)
        self.dirname = ''
        self.teams = 1

        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def BuildUI(self):
        #
        # Build Menus
        #
        menu = wx.MenuBar()

        fileMenu = wx.Menu()
        load = fileMenu.Append(wx.ID_OPEN, '&Open...', 'Add robot to match')
        self.Bind(wx.EVT_MENU, self.OnLoad, load)

        quit = fileMenu.Append(wx.ID_EXIT, '&Quit', 'Quit application')
        self.Bind(wx.EVT_MENU, self.OnQuit, quit)
        menu.Append(fileMenu, '&File')

        matchMenu = wx.Menu()
        start = matchMenu.Append(wx.ID_FORWARD, 'St&art', 'Run match')
        self.Bind(wx.EVT_MENU, self.OnStart, start)

        stop = matchMenu.Append(wx.ID_STOP, 'S&top', 'Pause match')
        self.Bind(wx.EVT_MENU, self.OnStop, stop)

        step = matchMenu.Append(wx.ID_ANY, '&Step', 'Run one tick')
        self.Bind(wx.EVT_MENU, self.OnStep, step)

        menu.Append(matchMenu, '&Match')

        self.SetMenuBar(menu)

        #
        # Build Toolbar
        #
        toolbar = self.CreateToolBar()
        tb_open = toolbar.AddLabelTool(wx.ID_OPEN, 'Open', get_bitmap(wx.ART_FILE_OPEN))
        self.Bind(wx.EVT_TOOL, self.OnLoad, tb_open)

        tb_start = toolbar.AddLabelTool(wx.ID_FORWARD, 'Start', get_bitmap(wx.ART_GO_FORWARD))
        self.Bind(wx.EVT_TOOL, self.OnStart, tb_start)

        tb_stop = toolbar.AddLabelTool(wx.ID_STOP, 'Stop', get_bitmap(wx.ART_DELETE))
        self.Bind(wx.EVT_TOOL, self.OnStop, tb_stop)

        toolbar.Realize()

        #
        # Layout Game Area
        #
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox = vbox

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox = hbox
        hbox.Add(vbox, 1)

        grid = CairoGrid(self)
        self.grid = grid
        grid.grid_cols = 100
        grid.grid_rows = 100
        hbox.Add(grid, 5)

        self.control = hbox


    def Start(self):
        self.timer.Start(10)

    def Stop(self):
        self.timer.Stop()

    def OnLoad(self, event):
        dlg = wx.FileDialog(self, "Choose a Robot...", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = dlg.GetDirectory()
            filename = abspath(dlg.GetPath())
            team = self.teams
            self.teams += 1
            self.backend.load([(team, filename)])
            robots = self.backend.tick(0)
            self.update(robots)

    def OnStop(self, event):
        self.Stop()

    def OnStart(self, event):
        self.Start()

    def OnStep(self, event):
        self.Tick()

    def OnQuit(self, event):
        self.Close()

    def OnClose(self, event):
        self.Stop()
        event.Skip()

    def OnTimer(self, event):
        self.Tick()

    def Tick(self):
        robots = self.backend.tick(10)
        self.update(robots)

        status = self.backend.status()
        if status == 'end':
            self.Stop()

    def update(self, robots):
        self.grid.points = [x.to_grid() for x in robots]
        self.grid.Refresh()

    def run(self):
        with Backend(self.intepreter) as b:
            self.backend = b
            b.start()
            b.size(100, 100)
            app.MainLoop()

import os
def can_exec(path):
    # Stolen from: http://stackoverflow.com/a/377028
    return os.path.isfile(path) and os.access(path, os.X_OK)


if __name__ == '__main__':
        app = wx.App(False)
        frame = MainWindow(None, wx.ID_ANY, "Robots")

        path = ['python', '-u', 'main.py'] # Disable buffering or else deadlock :(
        # Find intepreter
        for x in ('./main-c', './main-c.exe'):
            if can_exec(x):
                path = x
                break
        frame.intepreter = path


        frame.Size = (1000, 1000)
        frame.Show(True)
        frame.run()
