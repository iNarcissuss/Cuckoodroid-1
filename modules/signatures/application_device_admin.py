# Copyright (C) Check Point Software Technologies LTD.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from lib.cuckoo.common.abstracts import Signature


class AndroidInstalledApps(Signature):
    name = "application_device_admin"
    description = "Application Requested Device Administrator (Dynamic)"
    severity = 4
    categories = ["android"]
    authors = ["idanr1986"]
    minimum = "2.0"

    def on_complete(self):
        for log_line in self.get_results("debug", {}).get("log", []):
            if "Device Admin Granted" in log_line:
                return True
