import subprocess, re, hashlib, random, ipaddress, time, sys

passkey = "password"
max_packet_size = 1024
packet_interval = 0.05
sessions = {}

# define an initial substitution table for the cypher later
random.seed(int.from_bytes(passkey.encode(), 'big'))
sub_table = list(range(256))
indices = list(range(256))
random.shuffle(indices)
for i in range(0, 256, 2):
    a, b = indices[i], indices[i+1]
    sub_table[a], sub_table[b] = sub_table[b], sub_table[a]
random.seed()

# shortcut for making ansi color codes
def an(color_num): return f"\033[{color_num}m"

def is_ip(ip):
    try: return ipaddress.ip_address(ip) is not None
    except ValueError: return False

def make_checksum(str1, str2):
    # make checksum from two strings. returns an int of length 3
    h = hashlib.sha256((str(str1)+str(str2)).encode()).hexdigest()
    return int(''.join(c for c in h if c.isdigit())[:3])

def rand_dots(length):
    # return random braille characters (very haxxory)
    dots = ""
    for dot in range(length):
        dots += chr(random.randint(0x2800, 0x28FF))
    return dots

def parse_line(tcpdump_line):
    # runs regex on incoming lines. returns <ip, size>
    match = re.search(r'(\S+) > \S+: ICMP echo request, id \d+, seq \d+, length (\d+)', tcpdump_line)
    if match: return match.group(1), int(match.group(2)) - 8
    return None, None

# convert number to ascii char or vice versa (is smart about it)
def codec(x):
    return chr(x) if isinstance(x, int) else ord(x)

def cypher(n): return (n & ~0xFF) | sub_table[n & 0xFF]

def handle_packet(source_ip, number, trigger):
    if number == trigger: # only start receiving if it gets a 'magic number' (port) as a number
        sessions[source_ip] = {'phase': 'len', 'chars': []}
        return

    if not source_ip in sessions: # stop trying to analyze starting packet and wait for next one
        return

    ses = sessions[source_ip]

    # if its determined that it's time to get packet length, do so
    if ses['phase'] == 'len':
        ses['len'], ses['phase'] = cypher(number), "data"
        print(f"\n{an(36)}Incoming transmission from {an(35)}{source_ip}{an(0)}:")

        # print the funny braille dots based on length
        print(end=f"{an(34)}>{an(0)} {rand_dots(ses['len'])}\033[{ses['len']}D", flush=True)

    elif ses['phase'] == "data":
        if len(ses['chars']) == ses['len']: # data finished, check checksum now
            local_hash = make_checksum(ses['len'], "".join(ses['chars']))
            if number == local_hash:
                print(f"\n{an(32)}Reception complete!{an(0)}")
            else:
                print(f"\n{an(31)}Bad checksum: got {number}, expected {local_hash}{an(0)}")
            sessions.pop(source_ip)
            return

        # convert incoming number to ascii char
        try: input_char = codec(cypher(number))
        except ValueError:
            print(f"\n{an(31)}Invalid packet {cypher(number)} from {source_ip}{an(0)}")
            sessions.pop(source_ip)
            return

        # add ascii char to list of ones from this transmission
        ses['chars'].append(input_char)
        print(input_char, end="", flush=True)

def engage_listener():
    try:
        # spawn a subprocess that listens to all incoming ping packets
        cmd = ["tcpdump", "-n", "-l", "icmp[icmptype] == icmp-echo"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        print(f"{an(31)}tcpdump not found!{an(0)}")
        exit(1)

    try:
        port = int(sys.argv[1]) + max_packet_size
        for line in proc.stdout:
            sender, data = parse_line(line.strip())
            if data: handle_packet(sender, data, port)

    except KeyboardInterrupt: proc.terminate()

def engage_sender():
    # make sure that the ip argument is properly in the form <ip>:<port> and spit out error if it's wrong
    target_ip = sys.argv[1].split(":")[0]
    if sys.argv[1].count(":") == 1:
        message, port = sys.argv[2], sys.argv[1].split(":")[1]
        if not port.isdigit() or int(port) > max_packet_size or int(port) <= 0:
            print(f"{an(33)}Invalid port: {port} (needs int between 0 and {max_packet_size}){an(0)}")
            exit(1)
    else:
        print(f"{an(33)}Please include port after ip like {target_ip}:{random.randint(1, max_packet_size)}{an(0)}")
        exit(1)

    if len(message) == 0:
        print(f"{an(33)}A message is required!{an(0)}")
        exit(1)

    # limit message length - messages that are too long sometimes lead to ratelimiting by ???
    if len(message) >= 256:
        print(f"{an(33)}Message is too long!{an(0)}")
        exit(1)

    for char in message:
        # scan all characters to make sure they aren't too high in unicode registry
        if not 0 <= codec(char) <= max_packet_size:
            print(f"{an(33)}Invalid character {char} ({codec(char)} > {max_packet_size}){an(0)}")
            exit(1)

    planned_len = len(message)
    # build a list of numbers to send
    sequence = (
        [int(port) + max_packet_size, cypher(planned_len)] +
        [cypher(codec(c)) for c in message] +
        [make_checksum(planned_len, message)]
    )

    processes = []
    for num in sequence:
        # for every packet it needs to send, do this

        # print out the message being sent in real time
        if len(processes) >= 3: print(message[len(processes)-3], end="", flush=True)

        # build and run ping command subprocess
        ping_args = ["ping", "-c", "1", "-s", str(num), "-W", "1", target_ip]
        process = subprocess.Popen(ping_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(process)
        time.sleep(packet_interval)

    for process in processes:
        process.wait()

    print()

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        # check to make sure there's just one argument and it's an integer (the port)
        engage_listener()
    elif len(sys.argv) == 3 and is_ip(sys.argv[1].split(":")[0]):
        # check if there are two arguments and if there's a : in the second argument (make sure its like <ip>:<port>)
        engage_sender()
    else:
        print(f"Usage:\n"
              f"    python3 {sys.argv[0]} <ip>:<port> <message> - send message to server\n"
              f"    python3 {sys.argv[0]} <port> - set up listening server\n\n"
              f"Modify the passkey instance variable to customize (still not secure)\n"
              f"Modify the max_packet_size instance variable to increase number of usable characters and ports"
        )