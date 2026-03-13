import random, subprocess, string

def run(command):
  return subprocess.check_output(command, shell=True, text=True).strip()

def run_sudo(command):
  result = subprocess.run(command, shell=True, capture_output=True, text=True)
  if result.returncode != 0:
    print(f"Error: {command}\n{result.stderr.strip()}")
  return result.returncode == 0

def random_string(length):
  chars = string.ascii_uppercase + string.digits
  return ''.join(random.choice(chars) for _ in range(length))

def generate_random_mac(prefix_list):
  prefix = random.choice(prefix_list)
  prefix = ":".join(prefix[i:i + 2] for i in range(0, 6, 2))
  tail = [random.randint(0, 255) for _ in range(3)]
  return prefix + ":" + ":".join(f"{b:02X}" for b in tail)

def generate_device_name():
  names = "Jennifer Michael Amanda Christopher Jessica Jason Melissa David Sarah James Heather Matthew Nicole Joshua Amy John Elizabeth Robert Michelle Joseph Kimberly Daniel Angela Brian Stephanie Justin Tiffany William Christina Ryan Lisa Eric Rebecca Nicholas Crystal Jeremy Kelly Andrew Erin Timothy Laura Jonathan Amber Adam Rachel Kevin Jamie Anthony Mary Thomas April Richard Sara Jeffrey Andrea Steven Shannon Charles Megan Brandon Emily Mark Julie Benjamin Danielle Scott Erica Aaron Katherine Paul Maria Nathan Kristin Travis Lauren Patrick Kristen Chad Ashley Stephen Christine Kenneth Brandy Gregory Tara Jacob Katie Dustin Monica Jesse Carrie Jose Alicia Shawn Courtney Sean Misty Bryan Kathryn Derek Patricia Bradley Holly Edward Stacy Donald Karen Samuel Anna Peter Tracy Keith Brooke Kyle Samantha Ronald Allison Juan Melanie George Leslie Jared Susan Douglas Brandi Gary Cynthia Erik Natalie Phillip Jill Raymond Dawn Joel Dana Corey Vanessa Shane Veronica Larry Lindsay Marcus Tina Zachary Kristina Craig Stacey Derrick Wendy Todd Lori Jeremiah".split()
  apple_devices = ["MacBook-Pro", "MacBook-Air", "MacBook", "iMac", "iMac-Pro", "Mac-mini", "Mac-Studio", "iPhone", "iPhone-Pro", "iPhone-Pro-Max"]
  samsung_devices = ["Galaxy-S24", "Galaxy-S23", "Galaxy-S22", "Galaxy-A54", "Galaxy-A34", "Galaxy-Z-Fold5", "Galaxy-Z-Flip5", "Galaxy-Note20"]
  google_devices = ["Pixel-8", "Pixel-8-Pro", "Pixel-7", "Pixel-7-Pro", "Pixel-7a", "Pixel-6", "Pixel-6a", "Pixel-Fold"]

  rand_device_type = random.randrange(3)

  if rand_device_type == 0:
    device = random.choice(apple_devices)
    name = random.choice(names) + "s-" + device if random.randrange(2) else device
    return name, "apple"
  if rand_device_type == 1:
    prefix = random.choice(["DESKTOP", "LAPTOP"])
    return f"{prefix}-{random_string(7)}", "windows"

  rand_phone_type = random.randrange(3)

  if rand_phone_type == 0:
    device = random.choice(samsung_devices)
    name = random.choice(names) + "s-" + device if random.randrange(2) else device
    return name, "samsung"
  elif rand_phone_type == 1:
    device = random.choice(google_devices)
    name = random.choice(names) + "s-" + device if random.randrange(2) else device
    return name, "google"
  else:
    return random_string(6) + "-" + random_string(6), ""

def get_local_ip(iname):
  try:
    return run(f"ip -4 addr show {iname} | awk '/inet / {{print $2}}' | cut -d/ -f1")
  except subprocess.CalledProcessError:
    return "unknown"

def get_mac(iname):
  try: return run(f"ip link show {iname} | awk '/link\\/ether/ {{print $2}}'")
  except subprocess.CalledProcessError: return "unknown"

device_name, device_type = generate_device_name()
interface_name = run("ip -o link show up | awk -F': ' '/BROADCAST/ {print $2}' | head -1")

print(f"Current hostname: '{open('/etc/hostname').read().strip()}'")
print(f"Current MAC: {get_mac(interface_name)}")
print(f"Current IP: {get_local_ip(interface_name)}\n")

run_sudo(f"sudo ip link set dev {interface_name} down")
run_sudo(f"sudo hostnamectl set-hostname {device_name} --static")

if device_type == "apple":
  new_mac = generate_random_mac(["F0EE7A", "F02475", "F02475", "DC2B61", "A85C2C", "BC9FEF", "C82A14", "ACE4B5", "A4B197", "D0E140", "8C7B9D", "80ED2C", "3C0754"])
elif device_type == "windows":
  new_mac = generate_random_mac(["E4C767", "001109", "00040F", "000C87", "0003FF"])
elif device_type == "google":
  new_mac = generate_random_mac(["3C5AB4", "F4F5E8", "F4F5D8", "546009", "94EB2C", "A47733", "1CF29A", "20DFB9", "D86C63", "B8DB38"])
elif device_type == "samsung":
  new_mac = generate_random_mac(["5001BB", "CC07AB", "8C7712", "9C0298", "F4428F", "B8BBAF", "FC039F", "3C5A37", "5CE8EB", "B8D9CE"])
else:
  new_mac = generate_random_mac(["DA91F2", "BE3A7C", "CA4D1E", "FA7B32", "2A5E9D", "3E8C14", "4AB267", "6A3F8E", "9EC451", "AE72B3"])

run_sudo(f"sudo ip link set dev {interface_name} address {new_mac}")
run_sudo(f"sudo ip link set dev {interface_name} up")

print(f"New hostname: {device_name}")
print(f"New MAC: {get_mac(interface_name)}\n")

print("Waiting for interface to come up...")
ping_output = run("ping -c 1 -W 4 cloudflare.com 2>&1 || true")
print("Success!" if "1 received" in ping_output else "No internet")

print(f"\nNew IP: {get_local_ip(interface_name)}")