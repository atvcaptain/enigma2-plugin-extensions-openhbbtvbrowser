# -*- coding: utf-8 -*-
from __future__ import absolute_import

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.InfoBar import InfoBar
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import iPlayableService, iServiceInformation
from .hbbtv import HbbTVWindow

try:
    from enigma import eHbbtv
except ImportError:
    eHbbtv = None


class HBBTVParser(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.started = False
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={iPlayableService.evStart: self.serviceStarted})

    def serviceStarted(self):
        if self.started:
            return
        if InfoBar.instance:
            if self.onHBBTVActivation not in InfoBar.instance.onHBBTVActivation:
                InfoBar.instance.onHBBTVActivation.append(self.onHBBTVActivation)
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
            if not app_id:
                return ""
            app = hbbtv.getApplication(app_id)
            if app and app.isValid():
                return app.getUrl()
        except Exception as error:
            print("[OpenHbbTV] eHbbtv red button lookup failed:", error)
        return ""

    def onHBBTVActivation(self):
        url = self._get_ehbbtv_red_button_url() or self._get_legacy_hbbtv_url()
        onid, tsid, sid = self._get_service_triplet()

        if not url:
            self.close()
            return
        self.session.open(HbbTVWindow, url, onid, tsid, sid)


def autostart(reason, **kwargs):
    if "session" in kwargs:
        HBBTVParser(kwargs["session"])


def Plugins(**kwargs):
    return PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart)
