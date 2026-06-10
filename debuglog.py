# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import time
import traceback

LOGFILE = "/tmp/openhbbtv-e2backend.log"


def reset_log():
    try:
        with open(LOGFILE, "w") as f:
            f.write("===== OpenHbbTV E2 backend start %s =====\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        pass


def log(*args):
    text = " ".join(str(x) for x in args)
    line = "%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text)
    try:
        with open(LOGFILE, "a") as f:
            f.write(line)
    except Exception:
        pass
    try:
        print(text)
    except Exception:
        pass


def log_exception(prefix):
    log(prefix)
    try:
        with open(LOGFILE, "a") as f:
            traceback.print_exc(file=f)
    except Exception:
        pass
    try:
        traceback.print_exc()
    except Exception:
        pass
