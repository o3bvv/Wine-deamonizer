#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example of Wine processes daemonizer usage. Using IL-2 Dedicated Server as
experimental process.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from wine_deamonizer import WineDaemon


EXE_PATH = "/home/alex/Games/il2ds/4.12.2/il2server.exe"


class IL2DSDaemon(WineDaemon):
    """
    Test IL-2 Dedicated Server daemon.
    """
    def post_start(self):
        """
        Wait for server to print command prompt indicating it's loaded.
        """
        while True:
            line = self.process.stdout.readline()
            if line == '':
                break
            if line.startswith("1>"):
                break


def main():
    daemon = IL2DSDaemon(EXE_PATH)
    if not (len(sys.argv) == 2 and daemon(sys.argv[1])):
        print "usage: {name} {commands}".format(
            name=sys.argv[0], commands='|'.join(daemon.commands))
        sys.exit(1)


if __name__ == "__main__":
    main()
