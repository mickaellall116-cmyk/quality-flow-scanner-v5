"""Loopback-only socket guard runner (pattern: -12 preflight harness).
Blocks + logs every non-loopback connect/DNS attempt, then runs the target
test file as __main__. Usage: netguard_run.py <testfile.py> [unittest args]"""
import runpy, socket, sys, pathlib
LOG = pathlib.Path('/tmp/td17_ev/netguard.log')
def note(msg):
    with open(LOG, 'a') as f: f.write(msg + '\n')
_real_socket = socket.socket
_real_gai = socket.getaddrinfo
def _host_ok(host):
    return host in ('127.0.0.1', '::1', 'localhost')
class Guarded(_real_socket):
    def connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if not _host_ok(host):
            note(f'BLOCKED connect {address!r}')
            raise RuntimeError(f'netguard: non-loopback connect blocked: {address!r}')
        return super().connect(address)
    def connect_ex(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if not _host_ok(host):
            note(f'BLOCKED connect_ex {address!r}')
            raise RuntimeError(f'netguard: non-loopback connect blocked: {address!r}')
        return super().connect_ex(address)
def gai(host, *a, **k):
    if host is not None and not _host_ok(host):
        note(f'BLOCKED getaddrinfo {host!r}')
        raise RuntimeError(f'netguard: DNS blocked: {host!r}')
    return _real_gai(host, *a, **k)
socket.socket = Guarded
socket.getaddrinfo = gai
target = sys.argv[1]
sys.argv = [target] + sys.argv[2:]
runpy.run_path(target, run_name='__main__')
