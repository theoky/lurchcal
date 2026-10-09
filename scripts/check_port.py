import os
import socket
import sys

host = os.environ[sys.argv[1]]
port = int(os.environ[sys.argv[2]])

try:
    with socket.create_connection((host, port), timeout=1):
        sys.exit(0)
except OSError:
    sys.exit(1)