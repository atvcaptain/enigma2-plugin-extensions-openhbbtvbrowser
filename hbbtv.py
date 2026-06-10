# -*- coding: utf-8 -*-
from __future__ import absolute_import

from Screens.Screen import Screen
from enigma import eTimer, fbClass, eRCInput, eServiceReference
import os
from .browser import Browser
from . import commands

try:
    from enigma import eHbbtv
except ImportError:
    eHbbtv = None

browserinstance = None
g_session = None


class HbbTVWindow(Screen):
    skin = """
        <screen name="HbbTVWindow" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="HbbTV Plugin">
        </screen>
        """

    def __init__(self, session, url=None, onid=0, tsid=0, sid=0):
        Screen.__init__(self, session)

        global g_session
        g_session = session
        self._url = url
        self.onid = int(onid)
        self.tsid = int(tsid)
        self.sid = int(sid)
        self.count = 0
        self._closing = False
        self._browser_locked = False
        self._signal_connections = []
        self._stream_service = None
        self._video_window_active = False
        self._saved_video_window = None
        self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()

        self.hbbtv = eHbbtv.getInstance() if eHbbtv else None
        self.closetimer = eTimer()
        self.closetimer.callback.append(self.stop_hbbtv_application)
        self.starttimer = eTimer()
        self.starttimer.callback.append(self.start_hbbtv_application)
        self.starttimer.start(100)

        global browserinstance
        if not browserinstance:
            browserinstance = Browser()
        browserinstance.start(self._url, self.onid, self.tsid, self.sid)

    def _connect_signal(self, signal, callback):
        try:
            connection = signal.connect(callback)
            self._signal_connections.append(connection)
        except Exception as error:
            print("[OpenHbbTV] Signal connect failed:", error)

    def _connect_hbbtv_signals(self):
        if not self.hbbtv:
            return
        self._connect_signal(self.hbbtv.playServiceRequest, self._on_play_service_request)
        self._connect_signal(self.hbbtv.playStreamRequest, self._on_play_stream_request)
        self._connect_signal(self.hbbtv.pauseStreamRequest, self._on_pause_stream_request)
        self._connect_signal(self.hbbtv.stopStreamRequest, self._on_stop_stream_request)
        self._connect_signal(self.hbbtv.setVideoWindowRequest, self._on_set_video_window_request)
        self._connect_signal(self.hbbtv.unsetVideoWindowRequest, self._on_unset_video_window_request)
        self._connect_signal(self.hbbtv.createApplicationRequest, self._on_create_application_request)
        self._connect_signal(self.hbbtv.show, self._on_show_request)
        self._connect_signal(self.hbbtv.hide, self._on_hide_request)

    def _disconnect_hbbtv_signals(self):
        for connection in self._signal_connections:
            try:
                connection.disconnect()
            except Exception:
                pass
        self._signal_connections = []

    def start_hbbtv_application(self):
        global browserinstance
        if browserinstance.connectedClients() == 0:
            self.count += 1
            if self.count > 50:
                self.close()
            return

        self.starttimer.stop()
        fbClass.getInstance().lock()
        eRCInput.getInstance().lock()
        self._browser_locked = True

        if self.onBrowserCommand not in browserinstance.onCommand:
            browserinstance.onCommand.append(self.onBrowserCommand)
        if self.onExit not in browserinstance.onExit:
            browserinstance.onExit.append(self.onExit)
        self._connect_hbbtv_signals()

    def stop_hbbtv_application(self):
        self.closetimer.stop()
        self.close()

    def _decode_payload(self, data):
        if isinstance(data, bytes):
            return data.decode("utf-8", "replace")
        return str(data or "")

    def onBrowserCommand(self, cmd, data):
        payload = self._decode_payload(data)
        print("[OpenHbbTV] Browser command", cmd, payload)

        if cmd == commands.BROADCAST_PLAY:
            self._request_show()
            self._restore_broadcast_service()
        elif cmd == commands.BROADCAST_STOP:
            self._request_hide()
            self._restore_broadcast_service()
        elif cmd == commands.BROADCAST_HIDDEN:
            self._request_hide()
            self._on_unset_video_window_request()
        elif cmd == commands.SET_VIDEO_WINDOW:
            self._handle_set_video_window_payload(payload)
        elif cmd == commands.UNSET_VIDEO_WINDOW:
            self._on_unset_video_window_request()
        elif cmd == commands.PLAY_STREAM:
            self._request_play_stream(payload)
        elif cmd == commands.STOP_STREAM:
            self._request_stop_stream()
        elif cmd == commands.PAUSE_STREAM:
            self._request_pause_stream()
        elif cmd == commands.SEEK_STREAM:
            self._request_seek_stream(payload)
        elif cmd == commands.CREATE_APPLICATION:
            self._request_create_application(payload)
        elif cmd == commands.PAGE_LOAD_FINISHED:
            self._page_load_finished()
        elif cmd == commands.RESTORE_BROADCAST:
            self._restore_broadcast_service()
        elif cmd == commands.SET_CHANNEL:
            print("[OpenHbbTV] SET_CHANNEL is not implemented yet:", payload)
        elif cmd == commands.PREV_CHANNEL:
            print("[OpenHbbTV] PREV_CHANNEL is not implemented yet")
        elif cmd == commands.NEXT_CHANNEL:
            print("[OpenHbbTV] NEXT_CHANNEL is not implemented yet")
        elif cmd == commands.LOG:
            print("[OpenHbbTV][Browser]", payload)

    def _request_show(self):
        if self.hbbtv and hasattr(self.hbbtv, "debugEmitShow"):
            self.hbbtv.debugEmitShow()
        else:
            self._on_show_request()

    def _request_hide(self):
        if self.hbbtv and hasattr(self.hbbtv, "debugEmitHide"):
            self.hbbtv.debugEmitHide()
        else:
            self._on_hide_request()

    def _request_play_stream(self, uri):
        if not uri:
            return
        if self.hbbtv and hasattr(self.hbbtv, "debugEmitPlayStreamRequest"):
            self.hbbtv.debugEmitPlayStreamRequest(uri)
        else:
            self._on_play_stream_request(uri)

    def _request_stop_stream(self):
        if self.hbbtv and hasattr(self.hbbtv, "debugEmitStopStreamRequest"):
            self.hbbtv.debugEmitStopStreamRequest()
        else:
            self._on_stop_stream_request()

    def _request_pause_stream(self):
        if self.hbbtv and hasattr(self.hbbtv, "debugEmitPauseStreamRequest"):
            self.hbbtv.debugEmitPauseStreamRequest()
        else:
            self._on_pause_stream_request()

    def _request_seek_stream(self, payload):
        try:
            position = int(payload)
        except Exception:
            position = 0
        print("[OpenHbbTV] SEEK_STREAM requested:", position)

    def _request_create_application(self, uri):
        if not uri:
            return
        if self.hbbtv and hasattr(self.hbbtv, "debugEmitCreateApplicationRequest"):
            self.hbbtv.debugEmitCreateApplicationRequest(uri)
        else:
            self._on_create_application_request(uri)

    def _page_load_finished(self):
        # A new page must not inherit a stale small broadcast window.
        # If the page needs a video/broadcast object, the browser will report it again.
        self._on_unset_video_window_request()
        if self.hbbtv and hasattr(self.hbbtv, "pageLoadFinished"):
            try:
                self.hbbtv.pageLoadFinished()
            except Exception as error:
                print("[OpenHbbTV] pageLoadFinished failed:", error)

    def _handle_set_video_window_payload(self, payload):
        try:
            values = [int(float(x.strip())) for x in payload.split(",")]
            x, y, w, h = values[:4]
            browser_w = values[4] if len(values) > 4 and values[4] > 0 else 1280
            browser_h = values[5] if len(values) > 5 and values[5] > 0 else 720
        except Exception as error:
            print("[OpenHbbTV] Invalid SET_VIDEO_WINDOW payload:", payload, error)
            return

        global browserinstance
        screen_w = browserinstance.screen_width if browserinstance else 1280
        screen_h = browserinstance.screen_height if browserinstance else 720
        x = int((float(x) * screen_w) / browser_w)
        y = int((float(y) * screen_h) / browser_h)
        w = int((float(w) * screen_w) / browser_w)
        h = int((float(h) * screen_h) / browser_h)
        x = max(0, min(x, screen_w))
        y = max(0, min(y, screen_h))
        w = max(0, min(w, screen_w - x))
        h = max(0, min(h, screen_h - y))

        if self.hbbtv and hasattr(self.hbbtv, "debugEmitSetVideoWindowRequest"):
            self.hbbtv.debugEmitSetVideoWindowRequest(x, y, w, h)
        else:
            self._on_set_video_window_request(x, y, w, h)

    def _on_play_service_request(self, sref):
        if isinstance(sref, bytes):
            sref = sref.decode("utf-8", "replace")
        if not sref:
            return
        print("[OpenHbbTV] playServiceRequest:", sref)
        self.session.nav.playService(eServiceReference(str(sref)))

    def _on_play_stream_request(self, sref):
        if isinstance(sref, bytes):
            sref = sref.decode("utf-8", "replace")
        if not sref:
            return
        print("[OpenHbbTV] playStreamRequest:", sref)
        if self._stream_service is None:
            self._stream_service = self.session.nav.getCurrentlyPlayingServiceReference() or self.lastservice
        self.session.nav.playService(eServiceReference(str(sref)))
        self._set_stream_state(1, -1)

    def _on_pause_stream_request(self):
        print("[OpenHbbTV] pauseStreamRequest")
        try:
            service = self.session.nav.getCurrentService()
            pauseable = service and service.pause()
            if pauseable:
                pauseable.pause()
        except Exception as error:
            print("[OpenHbbTV] pause failed:", error)
        self._set_stream_state(2, -1)

    def _on_stop_stream_request(self):
        print("[OpenHbbTV] stopStreamRequest")
        self._restore_broadcast_service()
        self._set_stream_state(0, -1)

    def _on_set_video_window_request(self, x, y, w, h):
        print("[OpenHbbTV] setVideoWindowRequest:", x, y, w, h)
        if w <= 0 or h <= 0:
            self._on_unset_video_window_request()
            return
        self._save_video_window()
        self._write_video_window(x, y, w, h)
        self._video_window_active = True

    def _on_unset_video_window_request(self):
        print("[OpenHbbTV] unsetVideoWindowRequest")
        global browserinstance
        screen_w = browserinstance.screen_width if browserinstance else 1280
        screen_h = browserinstance.screen_height if browserinstance else 720
        self._write_video_window(0, 0, screen_w, screen_h)
        self._video_window_active = False

    def _on_create_application_request(self, uri):
        if isinstance(uri, bytes):
            uri = uri.decode("utf-8", "replace")
        resolved = str(uri or "")
        if self.hbbtv and hasattr(self.hbbtv, "resolveApplicationLocator"):
            try:
                tmp = self.hbbtv.resolveApplicationLocator(resolved)
                if tmp:
                    resolved = tmp
            except Exception as error:
                print("[OpenHbbTV] resolveApplicationLocator failed:", error)
        print("[OpenHbbTV] createApplicationRequest:", uri, "->", resolved)
        self._on_unset_video_window_request()
        global browserinstance
        if resolved and browserinstance:
            browserinstance.openUrl(resolved)

    def _on_show_request(self):
        print("[OpenHbbTV] show request")

    def _on_hide_request(self):
        print("[OpenHbbTV] hide request")

    def _restore_broadcast_service(self):
        ref = self._stream_service or self.lastservice
        if ref:
            try:
                current = self.session.nav.getCurrentlyPlayingServiceReference()
                if not current or current.toString() != ref.toString():
                    self.session.nav.playService(ref)
            except Exception as error:
                print("[OpenHbbTV] restore broadcast failed:", error)
        self._stream_service = None

    def _set_stream_state(self, state, error=-1):
        if self.hbbtv and hasattr(self.hbbtv, "setStreamState"):
            try:
                self.hbbtv.setStreamState(int(state), int(error))
            except Exception:
                pass

    def _vmpeg_path(self, name):
        return "/proc/stb/vmpeg/0/%s" % name

    def _read_proc(self, path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except OSError:
            return ""

    def _write_proc(self, path, value):
        try:
            current = self._read_proc(path)
            text = "0x%x" % int(value) if current.lower().startswith("0x") else str(int(value))
            with open(path, "w") as f:
                f.write(text)
            return True
        except OSError as error:
            print("[OpenHbbTV] write failed %s=%s: %s" % (path, value, error))
            return False

    def _save_video_window(self):
        if self._saved_video_window is not None:
            return
        self._saved_video_window = {
            "dst_left": self._read_proc(self._vmpeg_path("dst_left")),
            "dst_top": self._read_proc(self._vmpeg_path("dst_top")),
            "dst_width": self._read_proc(self._vmpeg_path("dst_width")),
            "dst_height": self._read_proc(self._vmpeg_path("dst_height")),
        }

    def _write_video_window(self, x, y, w, h):
        self._write_proc(self._vmpeg_path("dst_left"), x)
        self._write_proc(self._vmpeg_path("dst_top"), y)
        self._write_proc(self._vmpeg_path("dst_width"), w)
        self._write_proc(self._vmpeg_path("dst_height"), h)
        self._write_proc(self._vmpeg_path("dst_apply"), 1)

    def _restore_video_window(self):
        if not self._saved_video_window:
            self._on_unset_video_window_request()
            return
        for key in ("dst_left", "dst_top", "dst_width", "dst_height"):
            value = self._saved_video_window.get(key)
            if value:
                try:
                    with open(self._vmpeg_path(key), "w") as f:
                        f.write(value)
                except OSError:
                    pass
        self._write_proc(self._vmpeg_path("dst_apply"), 1)
        self._saved_video_window = None

    def onExit(self):
        if self._closing:
            return
        self._closing = True
        global browserinstance
        if browserinstance:
            if self.onBrowserCommand in browserinstance.onCommand:
                browserinstance.onCommand.remove(self.onBrowserCommand)
            if self.onExit in browserinstance.onExit:
                browserinstance.onExit.remove(self.onExit)
        self._disconnect_hbbtv_signals()
        self._restore_video_window()
        self._restore_broadcast_service()
        if self._browser_locked:
            try:
                fbClass.getInstance().unlock()
                eRCInput.getInstance().unlock()
            except Exception:
                pass
            self._browser_locked = False
        if browserinstance:
            browserinstance.stop()
        self.close()
