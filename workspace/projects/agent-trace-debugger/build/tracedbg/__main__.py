"""CLI entry point stub. Subcommands land in later tasks."""

import sys

USAGE = """\
usage: python -m tracedbg <command> ...

commands:
  record   record an agent execution to a trace file
  replay   step through a stored trace interactively
  diff     compare two traces and show where they diverge
  rerun    re-execute a trace from a pinned step

(not yet implemented)
"""


def main() -> int:
    print(USAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
