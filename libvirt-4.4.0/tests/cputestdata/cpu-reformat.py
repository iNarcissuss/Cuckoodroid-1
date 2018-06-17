#!/usr/bin/env python

import json
import sys

dec = json.JSONDecoder()
data, pos = dec.raw_decode(sys.stdin.read())
json.dump(data, sys.stdout, indent=2, separators=(',', ': '))
print("\n")
