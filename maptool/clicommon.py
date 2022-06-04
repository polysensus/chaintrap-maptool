import sys
import traceback
import subprocess as sp
from pathlib import Path


def print_exc():
    """Compact representation of current exception

    Single line tracebacks are individually a little confusing but prevent
    other useful output from being obscured"""

    exc_info = sys.exc_info()
    trace = [
        f'{Path(fn).name}[{ln}].{fun}:"{txt}"'
        for (fn, ln, fun, txt) in traceback.extract_tb(exc_info[2])
    ] + [f"{exc_info[0].__name__}:{exc_info[1]}"]

    print("->".join(trace), file=sys.stderr)


def run_status(runner, *errors):
    """
    Wrap a main entry point so that errors are caught and printed in a
    sensible way.

    Exception Handling:

    CalledProcessError is caught and, if available, stderr is printed to
    stderr. stdout is printed if availalbe.

    Errors: A tuple of all errors that should be reported simply by::

        print(repr(exc), str(exc), file=sys.stderr)

    Exception: is caught and a compact single line traceback is printed to
    stderr.

    In all exceptional cases a -ve status integer is returned.
    On success the value of runner is returned
    """
    try:
        return runner()
    except sp.CalledProcessError as cpe:
        if cpe.stdout:
            print(cpe.stdout)
        print(cpe.stderr, file=sys.stderr)
        return cpe.returncode

    except errors as exc:
        print(repr(exc), str(exc), file=sys.stderr)
    except KeyboardInterrupt:
        print("Caught Ctrl-C")
    except Exception:
        print_exc()

    return -1
