import os as _os
import sys as _sys
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))
import asyncore
import configargparse as _configargparse
from core.athana_z3950 import z3950_server
from utils.utils import suppress


def run():
    parser = _configargparse.ArgumentParser("Z3950 start")
    parser.add_argument("-p", "--port", default=2021, help="port to use")
    parser.add_argument("--force-test-db", action="store_true", default=False,
                        help="create / use database server with default database for testing (overrides configured db connection)")
    parser.add_argument("-l", "--loglevel", help="root loglevel, sensible values: DEBUG, INFO, WARN")
    args = parser.parse_args()
    from core import init
    init.full_init(force_test_db=args.force_test_db, root_loglevel=args.loglevel)
    z3950_server(port=args.port)
    while True:
        with suppress(Exception, warn=False):
            asyncore.loop(timeout=0.01)


if __name__ == "__main__":
    run()
