
import sys
import os
from RLTest import Defaults

if sys.version_info > (3, 0):
    Defaults.decode_responses = True

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../deps/readies"))
    import paella
except:
    pass

ONLY_STABLE = os.getenv('ONLY_STABLE', '0') == '1'
SANITIZER = os.getenv('SANITIZER', '')
VALGRIND = os.getenv('VALGRIND', '0') == '1'
CODE_COVERAGE = os.getenv('CODE_COVERAGE', '0') == '1'
NO_LIBEXT = os.getenv('NO_LIBEXT', '0') == '1'

OSNICK = paella.Platform().osnick
OS = paella.Platform().os
ARCH = paella.Platform().arch
