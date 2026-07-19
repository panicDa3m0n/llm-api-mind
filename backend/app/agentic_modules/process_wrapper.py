"""Linux child launcher that applies hard limits before replacing itself."""

from __future__ import annotations

import os
import resource
import sys


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: process_wrapper.py <memory_mb> <entrypoint> [args...]")
    memory_bytes = int(sys.argv[1]) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    entrypoint = sys.argv[2]
    os.execve(entrypoint, [entrypoint, *sys.argv[3:]], os.environ)


if __name__ == "__main__":
    main()
