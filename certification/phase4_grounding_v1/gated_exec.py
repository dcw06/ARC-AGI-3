"""Wait for the owning outer runner before executing a registered worker.

No agent/model imports occur in this standard-library-only bootstrap. EOF denies
launch. The eventual command inherits this process's externally owned group.
"""
import os
import sys


def main():
    fd = int(sys.argv[1])
    token = os.read(fd, 1)
    os.close(fd)
    if token != b'G':
        raise PermissionError('outer owner did not release worker')
    os.execvpe(sys.argv[2], sys.argv[2:], os.environ)


if __name__ == '__main__':
    main()
