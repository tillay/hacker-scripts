import subprocess, re, hashlib, random, ipaddress, time, sys

packet_spacing = 0.05
sessions = {}

def a(color_num): return f"\033[{color_num}m"

def is_ip(ip):
    try: return ipaddress.ip_address(ip) is not None
    except ValueError: return False

def make_checksum(str1, str2):
    h = hashlib.sha256((str(str1)+str(str2)).encode()).hexdigest()
    return int(''.join(c for c in h if c.isdigit())[:3])

def rand_dots(length):
    dots = ""
    for i in range(length):
        dots += chr(random.randint(0x2800, 0x28FF))
    return dots

def parse_line(tcpdump_line):
    match = re.search(r'(\S+) > \S+: ICMP echo request, id \d+, seq \d+, length (\d+)', tcpdump_line)
    if match: return match.group(1), int(match.group(2)) - 8
    return None, None

def handle_packet(source_ip, number, trigger):
    if number == trigger:
        sessions[source_ip] = {"phase": "len", "chars": []}
        return

    if not source_ip in sessions:
        return

    ses = sessions[source_ip]

    if ses["phase"] == "len":
        ses["planned_len"], ses["phase"] = number, "data"
        print(f"\n{a(36)}Incoming transmission from {a(35)}{source_ip}{a(0)}:")
        print(end=f"{a(34)}>{a(0)} {rand_dots(number)}\033[{number}D", flush=True)

    elif ses["phase"] == "data":
        if len(ses["chars"]) == ses["planned_len"]:
            local_hash = make_checksum(ses["planned_len"], "".join(ses["chars"]))
            if number == local_hash:
                print(f"\n{a(32)}Reception complete!{a(0)}")
            else:
                print(f"\n{a(31)}Bad checksum: got {number}, expected {local_hash}{a(0)}")
            sessions.pop(source_ip)
            return

        try: ascii_val = int(str(number), 8)
        except ValueError:
            print(f"\n{a(31)}Invalid octal {number} from {source_ip}{a(0)}")
            sessions.pop(source_ip)
            return

        input_char = chr(ascii_val) if 32 <= ascii_val <= 126 else f"[{ascii_val}]"
        ses["chars"].append(input_char)
        print(input_char, end="", flush=True)

if len(sys.argv) == 2 and sys.argv[1].isdigit():
    try:
        cmd = ["tcpdump", "-n", "-l", "icmp[icmptype] == icmp-echo"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        print(f"{a(31)}tcpdump not found!{a(0)}")
        exit(1)

    try:
        port = int(sys.argv[1])
        for line in proc.stdout:
            sender, data = parse_line(line.strip())
            if data: handle_packet(sender, data, port)

    except KeyboardInterrupt: proc.terminate()

elif len(sys.argv) == 3 and is_ip(sys.argv[1].split(":")[0]):
    target_ip = sys.argv[1].split(":")[0]
    if sys.argv[1].count(":") == 1:
        message, port = sys.argv[2], sys.argv[1].split(":")[1]
        if not port.isdigit() or int(port) > 1024 or int(port) <= 0:
            print(f"{a(33)}Invalid port: {port} (needs int between 0 and 1024){a(0)}")
            exit(1)
    else:
        print(f"{a(33)}Please include port after ip like {target_ip}:{random.randint(1, 1024)}{a(0)}")
        exit(1)

    if len(message) == 0:
        print(f"{a(33)}A message is required!{a(0)}")
        exit(1)

    for char in message:
        if not 0 <= int(oct(ord(char))[2:]) < 178:
            print(f"{a(33)}Invalid character {char} ({int(oct(ord(char))[2:])}){a(0)}")
            exit(1)

    planned_len = len(message)
    sequence = [port, planned_len] + [int(oct(ord(c))[2:]) for c in message] + [make_checksum(planned_len, message)]

    processes = []
    for num in sequence:
        ping_args = ["ping", "-c", "1", "-s", str(num), "-W", "1", target_ip]
        if len(processes) >= 3: print(message[len(processes)-3], end="", flush=True)
        process = subprocess.Popen(ping_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(process)
        time.sleep(packet_spacing)

    for process in processes:
        process.wait()

    print()

else:
    print(f"Usage:\n"
          f"    python3 {sys.argv[0]} <ip>:<port> <message> - send message to server\n"
          f"    python3 {sys.argv[0]} <port> - set up listening server"
    )
