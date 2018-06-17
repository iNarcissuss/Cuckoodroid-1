# Copyright (C) 2010-2015 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from lib.cuckoo.common.abstracts import Signature
from lib.cuckoo.core.plugins import enumerate_plugins

plugins = enumerate_plugins(__file__, "modules.signatures.network",
                            globals(), Signature)
