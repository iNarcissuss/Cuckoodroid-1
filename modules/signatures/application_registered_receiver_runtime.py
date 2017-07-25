# Copyright (C) Check Point Software Technologies LTD.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from lib.cuckoo.common.abstracts import Signature

class AndroidRegisteredReceiver(Signature):
    name = "application_registered_receiver_runtime"
    description = "Application Registered Receiver In Runtime (Dynamic)"
    severity = 3
    categories = ["android"]
    authors = ["Check Point Software Technologies LTD"]
    minimum = "2.0"

    def on_complete(self):
        for receiver in self.get_droidmon().get("registered_receivers", []):
        	self.mark_ioc("Receiver", receiver)
        return self.has_marks()
