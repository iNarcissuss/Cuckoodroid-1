# Copyright (C) Check Point Software Technologies LTD.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging

from lib.api.adb import dump_droidmon_logs, execute_sample, install_sample, get_package_activity_name, execute_service
from lib.common.abstracts import Package

log = logging.getLogger()


class Apk(Package):
    """Apk analysis package."""
    def __init__(self,options={}):
        Package(options)
        self.package=""
        self.activity=""
        self.service =""

    def start(self, path):
        self.package, self.activity, self.service=get_package_activity_name(path)
        install_sample(path)
        if self.activity != "":
            execute_sample(self.package, self.activity)
        else:
            execute_service(self.package, self.service)

    def check(self):
        return True

    def finish(self):
        dump_droidmon_logs(self.package)
        #dump_data_folder(self.package)
        return True

