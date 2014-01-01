#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wine processes daemonizer. Inspired by 'A simple unix/linux daemon in Python'
(http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python).
"""
import atexit
import os
import signal
import sys
import threading
import time

from signal import SIGTERM
from subprocess import Popen, PIPE


class WineDaemon(object):

    """
    Run a Windows process under Wine as a Unix daemon.
    """

    cmd_prefix = 'cmd_'
    process = None
    hup_event = None

    def __init__(self, exe_path, timeout=30.0,
                 stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        """
        Init the daemon. Parameters:
            `exe_path`  - path to 'exe' file to be run under Wine.
            `timeout`   - timeout to wait the subprocess to start. Exit daemon
                          start with failure, if timeout will expire.
            `stdin`,
            `stdout`,
            `stderr`    - paths to files to redirect daemon's
                          (not subprocess' !) IO to.
        """
        exe_name = os.path.basename(exe_path)
        pid_name = "{name}.pid".format(name=os.path.splitext(exe_name)[0])

        self.exe_path = exe_path
        self.pid_path = os.path.join(os.path.dirname(exe_path), pid_name)

        self.timeout = timeout
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def _daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced Programming in
        the UNIX Environment", chapter 13 'Daemon Processes', section 'Coding
        rules' for details (ISBN 978-0-321-63773-4).

        See also: http://web.archive.org/web/20120914180018/http://www.steve.org.uk/Reference/Unix/faq_2.html#SEC16
        """
        # Get pid of current process wich will be the grandparent of daemon.
        ppid = os.getpid()

        # Clear file creation mask.
        os.umask(0)

        # Create event for waiting SIGHUP.
        self.hup_event = threading.Event()
        self.hup_event.clear()
        # Set handler for SIGHUP.
        signal.signal(signal.SIGHUP, self.on_sighup)

        # Become a session leader to lose controlling TTY.
        try:
            pid = os.fork()
        except OSError as e:
            sys.stderr.write("fork #1 failed: ({errno}) {errmsg}\n".format(
                             errno=e.errno, errmsg=e.strerror))
            sys.exit(1)
        else:
            if pid > 0:
                # Block terminal untill daemon start is done or timed out.
                if self.hup_event.wait(timeout=self.timeout):
                    sys.exit(0)
                else:
                    sys.stderr.write("Daemon start timed out!")
                    sys.exit(1)
        # Call setsid to create a new session.
        os.setsid()
        # Change the current working directory to the root so we won’t prevent
        # file systems from being unmounted.
        os.chdir("/")

        # Exit the parent (the session group leader), so we can never regain a
        # controlling terminal.
        try:
            pid = os.fork()
        except OSError as e:
            sys.stderr.write("fork #2 failed: ({errno}) {errmsg}\n".format(
                             errno=e.errno, errmsg=e.strerror))
            sys.exit(1)
        else:
            if pid > 0:
                # Exit parent process.
                sys.exit(0)

        process_info = ["wine", self.exe_path]
        try:
            self.process = Popen(process_info, stdout=PIPE, stderr=PIPE)
        except OSError as err:
            sys.stderr.write(
                "Failed to start process '{info}': {e}\n".format(
                    info=' '.join(process_info), e=str(err)))
            sys.exit(1)

        # Redirect standard file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Write subprocess' pid to pidfile.
        atexit.register(self._remove_pid_file)
        file(self.pid_path, 'w+').write("{pid}\n".format(pid=self.process.pid))

        # Call child's handler of process creation event.
        self.post_start()
        # Unblock the grandparent.
        os.kill(ppid, signal.SIGHUP)

    def on_sighup(self, signum, frame):
        if self.hup_event is not None:
            self.hup_event.set()

    def _remove_pid_file(self):
        if os.path.exists(self.pid_path):
            os.remove(self.pid_path)

    @property
    def pid(self):
        """
        Get PID of Windows' subprocess.
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
        """
        Public command for printing daemon's status.
        """
        if self.pid:
            sys.stdout.write(
                "Daemon is running (pid={pid}).\n".format(pid=self.pid))
        else:
            sys.stdout.write("Daemon is not running.\n")

    def cmd_start(self):
        """
        Public command for starting the daemon.
        """
        if self.pid:
            sys.stderr.write("pidfile '{path}' already exist. Daemon already "
                             "running?\n".format(path=self.pid_path))
            sys.exit(1)

        # Start the daemon.
        self._daemonize()
        self.run()

    def cmd_stop(self):
        """
        Public command for stopping the daemon.
        """
        pid = self.pid
        if not pid:
            sys.stderr.write("pidfile '{path}' does not exist. Daemon not "
                             "running?\n".format(path=self.pid_path))
            return # not an error in a restart

        # Try to kill the daemon process.
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
        Public command for restarting the daemon.
        """
        self.cmd_stop()
        self.cmd_start()

    def post_start(self):
        """
        This method will be called just after process has spawned. You can use
        this method to block the calling terminal until you will be sure that a
        subprocess has successfully started and it can communicate with the
        outside world. Note that the parent has a timeout on waiting the daemon
        to start. If timeout will expire before this method exists, then parent
        will exit with error.
        """

    def run(self):
        """
        This method will be called after the process has been _daemonized by
        cmd_start() or cmd_restart(). By default this method waits for
        subprocess to finish.
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
