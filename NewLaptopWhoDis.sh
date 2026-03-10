interface=$(ip -o link show up | awk -F': ' '/BROADCAST/ {print $2}')
sudo ip link set dev $interface down
sudo hostnamectl set-hostname $(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c8) --static
sudo macchanger -r $interface 
sudo dhclient -r $interface
sudo dhclient -I $(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c8) $interface
sudo ip link set dev $interface up
