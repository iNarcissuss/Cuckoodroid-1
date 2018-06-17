# Copyright (C) Check Point Software Technologies LTD.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import time
from threading import Thread

from lib.api import adb
from lib.common.abstracts import Auxiliary

log = logging.getLogger(__name__)
DELAY = 1

class TouchSimulator(Auxiliary, Thread):

    
    def __init__(self):
        Thread.__init__(self)
        self.do_run = True


    def stop(self):

        self.do_run = False

    def run(self):
        while self.do_run:
            time.sleep(DELAY)
            if adb.check_package_on_top("com.android.settings/.DeviceAdminAdd"):
                log.info("TouchSimulator - Device Admin Granted")
                adb.simulate_touch("386","753")
            elif adb.check_package_on_top("com.android.packageinstaller/.PackageInstallerActivity") or adb.check_package_on_top("com.android.packageinstaller/.InstallAppProgress"):
                log.info("TouchSimulator - Package Installer")
                adb.simulate_touch("386","753")
            elif adb.check_package_on_top("com.noshufou.android.su/.SuRequestActivity"):
                log.info("TouchSimulator - SuperSU Root Granted")
                adb.simulate_touch("386","553")
        return True

