import socket, select, time, struct

def probe_udp(port, timeout=3):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.setblocking(False)
    print(f"[UDP {port}] listening {timeout}s ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r, _, _ = select.select([s], [], [], 0.25)
        if r:
            data, addr = s.recvfrom(4096)
            print(f"  -> {addr}  {len(data)} bytes: {data[:48].hex()}")
    s.close()

def probe_tcp(port, timeout=3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        print(f"[TCP {port}] connected!")
        s.setblocking(False)
        deadline = time.time() + timeout
        got = b""
        while time.time() < deadline:
            r, _, _ = select.select([s], [], [], 0.25)
            if r:
                chunk = s.recv(4096)
                if not chunk:
                    print(f"  server closed connection immediately")
                    break
                got += chunk
                print(f"  recv {len(chunk)} bytes: {chunk[:64].hex()}")
                if len(got) > 256:
                    break
        if not got:
            print(f"  no data received (silent)")
    except ConnectionRefusedError:
        print(f"[TCP {port}] refused")
    except socket.timeout:
        print(f"[TCP {port}] timed out connecting")
    except Exception as e:
        print(f"[TCP {port}] error: {e}")
    finally:
        s.close()

probe_udp(9005)
for port in [9527, 9005, 3680, 8053, 15680]:
    probe_tcp(port)
    time.sleep(0.5)
