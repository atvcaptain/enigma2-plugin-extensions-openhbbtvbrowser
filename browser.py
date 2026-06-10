# -*- coding: utf-8 -*-
from __future__ import absolute_import

from enigma import eConsoleAppContainer
from boxbranding import getBrandOEM
import shlex
from . import commands
from . import datasocket
from .debuglog import log, log_exception


class Browser:
    def __init__(self):
        log("[OpenHbbTV] Browser init")
        self.resolution = "1920x1080"
        self.screen_width = 1920
        self.screen_height = 1080
        self._detect_resolution()

        self.onCommand = []
        self.onExit = []
        self.commandserver = None
        self.container = None

    def _detect_resolution(self):
        log("[OpenHbbTV] detect resolution")
        try:
            with open("/proc/stb/video/videomode_50hz", "r") as f:
                vmode = f.read().strip()
        except OSError:
            vmode = "1080"

        if vmode.startswith("480"):
            self.resolution = "720x480"
        elif vmode.startswith("576"):
            self.resolution = "720x576"
        elif vmode.startswith("720"):
            self.resolution = "1280x720"
        elif vmode.startswith("216"):
            self.resolution = "3840x2160"
        else:
            self.resolution = "1920x1080"

        try:
            self.screen_width, self.screen_height = [int(x) for x in self.resolution.split("x", 1)]
        except Exception:
            self.screen_width = 1920
            self.screen_height = 1080

    def connectedClients(self):
        return self.commandserver.connectedClients() if self.commandserver else 0

    def start(self, url, onid, tsid, sid):
        log("[OpenHbbTV] Browser.start", url, onid, tsid, sid, "existing_server", bool(self.commandserver), "clients", self.connectedClients())
        if self.commandserver:
            if self.connectedClients():
                log("[OpenHbbTV] Browser already running, sending OPEN_URL")
                self.openUrl(url)
            return

        self.commandserver = datasocket.CommandServer()
        log("[OpenHbbTV] CommandServer started", datasocket.SOCKET_PATH)
        if self.onCommandReceived not in datasocket.onCommandReceived:
            datasocket.onCommandReceived.append(self.onCommandReceived)
        if self.onBrowserClosed not in datasocket.onBrowserClosed:
            datasocket.onBrowserClosed.append(self.onBrowserClosed)

        self.container = eConsoleAppContainer()
        quoted_url = shlex.quote(str(url))
        cmd = "OPENHBBTV_LOGFILE=/tmp/openhbbtvbrowser-debug.log /usr/bin/openhbbtvbrowser %s --onid %d --tsid %d --sid %d" % (quoted_url, int(onid), int(tsid), int(sid))
        if getBrandOEM() == "vuplus":
            cmd = "export EGLFS_LIBVUPL_SIZE=%s; %s" % (self.resolution, cmd)
        log("[OpenHbbTV] execute", cmd)
        self.container.execute(cmd)

    def stop(self):
        log("[OpenHbbTV] Browser.stop")
        self.sendCommand(commands.QUIT)
        if self.commandserver:
            self.commandserver.close()
            self.commandserver = None
        if self.onCommandReceived in datasocket.onCommandReceived:
            datasocket.onCommandReceived.remove(self.onCommandReceived)
        if self.onBrowserClosed in datasocket.onBrowserClosed:
            datasocket.onBrowserClosed.remove(self.onBrowserClosed)
        self.container = None

    def sendCommand(self, cmd, data=b""):
        log("[OpenHbbTV] E2->Browser sendCommand", cmd, data, "has_server", bool(self.commandserver), "clients", self.connectedClients())
        if self.commandserver:
            self.commandserver.sendCommand(cmd, data)

    def openUrl(self, url):
        self.sendCommand(commands.OPEN_URL, url)

    def setCurrentChannel(self, onid, tsid, sid):
        self.sendCommand(commands.SET_CURRENT_CHANNEL, "%d,%d,%d" % (int(onid), int(tsid), int(sid)))

    def onCommandReceived(self, cmd, data):
        log("[OpenHbbTV] Browser->E2 onCommandReceived", cmd, data)
        if cmd == commands.EXIT:
            for callback in list(self.onExit):
                callback()
            return
        for callback in list(self.onCommand):
            callback(cmd, data)

    def onBrowserClosed(self):
        log("[OpenHbbTV] Browser closed/disconnected")
        self.commandserver = None
        for callback in list(self.onExit):
            callback()
