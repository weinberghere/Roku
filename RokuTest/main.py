from flask import Flask, render_template, request
import requests
import ipaddress
import concurrent.futures
import socket
import netifaces as ni

app = Flask(__name__)

# List of available Roku commands
ROKU_COMMANDS = {
    'home': 'Home',
    'volumeup': 'VolumeUp',
    'volumedown': 'VolumeDown',
    'volumemute': 'VolumeMute',
    'left': 'Left',
    'right': 'Right',
    'up': 'Up',
    'down': 'Down',
    'select': 'Select',
    'back': 'Back',
    'play': 'Play',
    'pause': 'Play',
    'rewind': 'Rev',
    'fastforward': 'Fwd',
    'replay': 'InstantReplay',
    'info': 'Info',
    'backspace': 'Backspace',
    'search': 'Search'
    # ... add more commands as needed ...
}


# Function to scan for open port 8060 (typical for Roku devices)
def scan_port(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((str(ip), 8060))
            if result == 0:
                return str(ip)
    except socket.error:
        pass
    return None


# Function to discover Roku devices on the network
def discover_open_ports(network):
    open_ports = []
    host_list = list(network.hosts())
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(scan_port, ip): ip for ip in host_list}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                open_ports.append(result)
    return open_ports


# Function to send command to Roku device
def send_command(ip, command):
    if command in ROKU_COMMANDS:
        try:
            response = requests.post(f'http://{ip}:8060/keypress/{ROKU_COMMANDS[command]}')
            return response.status_code == 200
        except requests.exceptions.RequestException:
            pass
    return False


# Function to get the local network
def get_local_network():
    # Get the default gateway interface
    gws = ni.gateways()
    default_gateway = gws['default'][ni.AF_INET][1]

    # Get the IP address and netmask
    ip_address = ni.ifaddresses(default_gateway)[ni.AF_INET][0]['addr']
    netmask = ni.ifaddresses(default_gateway)[ni.AF_INET][0]['netmask']

    # Calculate the network
    network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
    return network


@app.route('/', methods=['GET'])
def index():
    # Get the local network
    network = get_local_network()

    # Attempt to discover Roku devices
    open_ports = discover_open_ports(network)

    if open_ports:
        return render_template('devices.html', devices=open_ports)
    else:
        return render_template('error.html', message='No Roku devices found.')


@app.route('/remote/<device_ip>', methods=['GET', 'POST'])
def remote(device_ip):
    if request.method == 'POST':
        command = request.form['command']
        success = send_command(device_ip, command)
        feedback_message = f"Command '{command}' sent successfully to {device_ip}." if success \
            else f"Failed to send command '{command}' to {device_ip}."
        return render_template('remote.html', device_ip=device_ip, commands=ROKU_COMMANDS,
                               feedback_message=feedback_message)

    return render_template('remote.html', device_ip=device_ip, commands=ROKU_COMMANDS)


if __name__ == "__main__":
    app.run(debug=True)
