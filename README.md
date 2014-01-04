Wine deamonizer
===============

[![PyPi package](https://badge.fury.io/py/wine-deamonizer.png)](http://badge.fury.io/py/wine-deamonizer/)
[![Downloads](https://pypip.in/d/wine-deamonizer/badge.png)](https://crate.io/packages/wine-deamonizer/)

Run Windows processes under Wine as Unix daemons.

Installation
------------

Via PyPI:

    pip install wine-deamonizer

As an Ubuntu package:

    sudo add-apt-repository ppa:il2horus/ppa
    sudo apt-get update

    sudo apt-get install python-wine-deamonizer

Dependencies
------------

You must have [Wine](http://www.winehq.org) to be installed to make this thing
to work. Installation itself does not require any dependencies.

Features
--------

Available commands for daemon:

1. `start` - start daemon (you can make a starter to block with timeout to wait
             for daemon to start and load);
2. `stop` - stop daemon;
3. `status` - get current status of daemon;
4. `restart` - restart (stop and start) daemon.

Usage
-----

Import `WineDaemon` class:

    from wine_deamonizer import WineDaemon

Create daemon's instance passing `exe_path` parameter as the path to Windows'
executable file:

    exe_path = "/path/to/some/windows/program.exe"
    daemon = WineDaemon(exe_path)

You can pass a timeout (fraction of seconds) for the deamon to start as well
(30 seconds by default):

    daemon = WineDaemon(exe_path, timeout=45.0)

Run some command by calling daemon with command's name as string parameter (
it can be easy to pass a command-line argument to the daemon):

    daemon('status')
    # Daemon is not running.

    daemon('stop')
    # pidfile '/path/to/some/windows/program.pid' does not exist. Daemon not running?

    daemon('start')

    daemon('status')
    # Daemon is running (pid=11192).

    daemon('start')
    # pidfile '/path/to/some/windows/program.pid' already exist. Daemon already running?

    daemon('stop')

    daemon('status')
    # Daemon is not running.

You may override `post_start` method to perform some actions (maybe to wait and
make sure your service is ready to go). This method will block calling process,
so try to leave it as soon as you can. If the parent will be blocked for the
time longer then specified by the timeout, it will exit with error. You can
modify timeout's value as described above, though.

One more thing you can do is to override `run` method. It is called after your
daemon has successfully started and the parent process has went away. By
default this method waits for the Wine subprocess to finish. It is accessable
via `self.process` attribute within the method. Do not forget to wait
subprocess or to call superclass' `run` method. Otherwise your daemon will
exit, delete pid file and leave orphan subprocess alone.

Look through an `examples` directory for more examples.
