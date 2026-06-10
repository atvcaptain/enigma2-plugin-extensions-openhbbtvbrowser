# -*- coding: utf-8 -*-
from __future__ import absolute_import

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.InfoBar import InfoBar
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import iPlayableService, iServiceInformation
from .hbbtv import HbbTVWindow
from .debuglog import log, reset_log

try:
    from enigma import eHbbtv
except ImportError:
    eHbbtv = None


class HBBTVParser(Screen):
    active_window = None
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.started = False
        reset_log()
        log("[OpenHbbTV] HBBTVParser init")
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={iPlayableService.evStart: self.serviceStarted})

    def serviceStarted(self):
        log("[OpenHbbTV] serviceStarted started=", self.started)
        if self.started:
            return
        if InfoBar.instance:
            if self.onHBBTVActivation not in InfoBar.instance.onHBBTVActivation:
                InfoBar.instance.onHBBTVActivation.append(self.onHBBTVActivation)
                log("[OpenHbbTV] registered InfoBar HBBTV activation hook")
            self.started = True

    def _get_service_triplet(self):
        service = self.session.nav.getCurrentService()
        info = service and service.info()
        onid = info and info.getInfo(iServiceInformation.sONID) or -1
        tsid = info and info.getInfo(iServiceInformation.sTSID) or -1
        sid = info and info.getInfo(iServiceInformation.sSID) or -1
        return onid, tsid, sid

    def _get_legacy_hbbtv_url(self):
        service = self.session.nav.getCurrentService()
        info = service and service.info()
        return info and info.getInfoString(iServiceInformation.sHBBTVUrl) or ""

    def _get_ehbbtv_red_button_url(self):
        if not eHbbtv:
            return ""
        try:
            hbbtv = eHbbtv.getInstance()
            app_id = hbbtv.getRedButtonApplicationId()
            log("[OpenHbbTV] eHbbtv red app id", app_id)
            if not app_id:
                return ""
            app = hbbtv.getApplication(app_id)
            log("[OpenHbbTV] eHbbtv red app", app)
            if app and app.isValid():
                url = app.getUrl()
                log("[OpenHbbTV] eHbbtv red url", url)
                return url
        except Exception as error:
            log("[OpenHbbTV] eHbbtv red button lookup failed:", error)
        return ""

    def onHBBTVActivation(self):
        log("[OpenHbbTV] onHBBTVActivation")
        url = self._get_ehbbtv_red_button_url() or self._get_legacy_hbbtv_url()
        onid, tsid, sid = self._get_service_triplet()
        log("[OpenHbbTV] activation url/triplet", url, onid, tsid, sid)

        if not url:
            log("[OpenHbbTV] no HbbTV URL available")
            self.close()
            return

        if HBBTVParser.active_window and not getattr(HBBTVParser.active_window, "_closing", True):
            log("[OpenHbbTV] reuse active HbbTVWindow")
            try:
                HBBTVParser.active_window.open_hbbtv_url(url, onid, tsid, sid)
                return
            except Exception as error:
                log("[OpenHbbTV] active window reuse failed", error)

        log("[OpenHbbTV] open new HbbTVWindow")
        HBBTVParser.active_window = self.session.open(HbbTVWindow, url, onid, tsid, sid)


def autostart(reason, **kwargs):
    log("[OpenHbbTV] autostart reason", reason, "kwargs", list(kwargs.keys()))
    if "session" in kwargs:
        HBBTVParser(kwargs["session"])


def Plugins(**kwargs):
    return PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart)
