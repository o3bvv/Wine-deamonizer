#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wine processes daemonizer.
"""
import atexit
import os
import sys
import time

from signal import SIGTERM
from subprocess import Popen, PIPE


class WineDaemon(object):

    """
    Run a Windows process under Wine as a Unix daemon.
    """

    cmd_prefix = 'cmd_'
    process = None

    def __init__(self, exe_path,
                 stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        exe_name = os.path.basename(exe_path)
        pid_name = "{name}.pid".format(name=os.path.splitext(exe_name)[0])

        self.exe_path = exe_path
        self.pid_path = os.path.join(os.path.dirname(exe_path), pid_name)

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def _daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177).
        """
        # do first fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #1 failed: ({errno}) {errmsg}\n".format(
                             errno=e.errno, errmsg=e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #2 failed: ({errno}) {errmsg}\n".format(
                             errno=e.errno, errmsg=e.strerror))
            sys.exit(1)

        process_info = ["wine", self.exe_path]
        try:
            self.process = Popen(process_info, stdout=PIPE, stderr=PIPE)
        except OSError as err:
            sys.stderr.write(
                "Failed to start process '{info}': {e}\n".format(
                    info=' '.join(process_info), e=str(err)))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self._remove_pid_file)
        file(self.pid_path, 'w+').write("{pid}\n".format(pid=self.process.pid))

    def _remove_pid_file(self):
        if os.path.exists(self.pid_path):
            os.remove(self.pid_path)

    @property
    def pid(self):
        """
        Get PID of Windows process.
        """
        try:
            pf = file(self.pid_path, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        else:
            status_path = "/proc/{pid}/status".format(pid=pid)
            if not os.path.exists(status_path):
                pid = None
        return pid

    def cmd_status(self):
        if self.pid:
            sys.stdout.write(
                "Daemon is running (pid={pid}).\n".format(pid=self.pid))
        else:
            sys.stdout.write("Daemon is not running.\n")

    def cmd_start(self):
        """
        Start the daemon.
        """
        if self.pid:
            sys.stderr.write("pidfile '{path}' already exist. Daemon already "
                             "running?\n".format(path=self.pid_path))
            sys.exit(1)

        # Start the daemon
        self._daemonize()
        if self.process is not None:
            self.run()

    def cmd_stop(self):
        """
        Stop the daemon.
        """
        pid = self.pid
        if not pid:
            sys.stderr.write("pidfile '{path}' does not exist. Daemon not "
                             "running?\n".format(path=self.pid_path))
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pid_path):
                    os.remove(self.pid_path)
            else:
                sys.stderr.write(err)
                sys.exit(1)

    def cmd_restart(self):
        """
        Restart the daemon.
        """
        self.cmd_stop()
        self.cmd_start()

    def run(self):
        """
        You can override this method when you subclass WineDaemon. It will be
        called after the process has been _daemonized by cmd_start() or
        cmd_restart(). By default this method waits for subprocess to finish.
        """
        self.process.wait()

    @property
    def commands(self):
        """
        Get list of public commands without prefixes.
        """
        return [name.lstrip(self.cmd_prefix) for name in dir(self)
                if name.startswith(self.cmd_prefix)]

    def __call__(self, cmd_name):
        """
        Call public command by name without prefix.
        """
        real_name = "{prefix}{name}".format(prefix=self.cmd_prefix,
                                            name=cmd_name)
        result = hasattr(self, real_name)
        try:
            getattr(self, real_name)()
        except AttributeError as e:
            sys.stderr.write("Unknown command '{cmd}.'\n".format(cmd=cmd_name))
            result = False
        return result
