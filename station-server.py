#!/usr/bin/env python3
"""
station-server.py with Flask integration

Project done by:
    1. Saayella Saayella : 23857608
    2. Rishon Jose : 23836894
    3. Kelvin Choi : 23352805
"""

import subprocess, platform, uuid, datetime, time, os, socket, sys, threading, re
from threading import Event
from flask import Flask, render_template, request

# Global variable as CLASS for IP Address
class IP:
    SERVER_IP = '192.168.1.62'  # Default hardcoded IP, will be updated at runtime

# Global variables
leave_time_int = 0
routing_results = {}
response_timer = None
route_discovery_done = threading.Event()
route_discovery_completed = Event()

# Global dictionaries for UDP messaging
pending_acknowledgements = {}
pending_responses = {}

# Global Flask app instance
app = Flask(__name__)

# These globals will be set in main() and used by Flask routes.
station_name = None
query_port = None
neighbours = []


# ---------------------- Utility Functions ---------------------- #
def get_mac_ip():
    try:
        result = subprocess.run(['ifconfig', 'en0'], capture_output=True, text=True)
        output = result.stdout
        ip_pattern = re.compile(r'inet\s+(\d+\.\d+\.\d+\.\d+)')
        match = ip_pattern.search(output)
        if match:
            return match.group(1)
        else:
            return "localhost"
    except Exception as e:
        return str(e)

def get_ip_address_from_adapter(adapter_name):
    os_type = platform.system()
    command = ['ipconfig'] if os_type == "Windows" else ['ip', 'addr']
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = result.stdout
        if os_type == "Windows":
            ip_marker = "IPv4 Address. . . . . . . . . . . :"
        else:
            ip_marker = "inet "
        if os_type != "Windows":
            adapter_block = ""
            recording = False
            lines = output.split('\n')
            for line in lines:
                if line.strip() and line.split()[0].isdigit():
                    if recording:
                        break
                    if adapter_name in adapter_block:
                        break
                    adapter_block = ""
                adapter_block += line + "\n"
                if adapter_name in line:
                    recording = True
        ip_start = adapter_block.find(ip_marker)
        if ip_start == -1:
            return "IPv4 address not found"
        ip_start += len(ip_marker)
        ip_end = adapter_block.find('\n', ip_start)
        ip_address = adapter_block[ip_start:ip_end].strip().split('/')[0]
        return ip_address
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute command: {e}")
        return "Command execution failed"

def update_leave_time(new_time_str):
    global leave_time_int
    leave_time_int = int(new_time_str) * 100
    print("Updated leave_time_int to:", leave_time_int)

def convert_to_epoch(departure_time_str):
    today = datetime.datetime.now().date()
    departure_time = datetime.datetime.strptime(f"{today} {departure_time_str}", "%Y-%m-%d %H:%M")
    return departure_time.timestamp()

def integer_to_epoch_time(time_integer):
    hours = time_integer // 10000
    minutes = (time_integer // 100) % 100
    seconds = time_integer % 100
    total_seconds = hours * 3600 + minutes * 60 + seconds
    current_date = time.localtime()
    current_epoch_time = time.mktime(current_date)
    epoch_time = current_epoch_time - (current_date.tm_hour * 3600 + current_date.tm_min * 60 + current_date.tm_sec) + total_seconds
    return epoch_time

def generate_uuid():
    return str(uuid.uuid4())

def read_timetable(filename):
    timetable = {}
    try:
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) < 5 or line.startswith('#'):
                    continue
                departure_time, destination = parts[0], parts[4]
                departure_time_int = int(departure_time.replace(":", ''))
                departure_time_int *= 100
                if destination not in timetable:
                    timetable[destination] = []
                details = {
                    'departure_time': parts[0],
                    'bus_train': parts[1],
                    'from_stop': parts[2],
                    'arrival_time': parts[3]
                }
                if departure_time_int > leave_time_int:
                    timetable[destination].append(details)
    except Exception as e:
        print(f"Error reading timetable: {e}")
    return timetable

def monitor_file_changes(filepath, interval=5):
    try:
        last_modified = os.path.getmtime(filepath)
    except Exception as e:
        print(f"File {filepath} not found.")
        return
    while True:
        try:
            current_modified = os.path.getmtime(filepath)
            if current_modified != last_modified:
                print(f"File {filepath} has been modified.")
                last_modified = current_modified
                reload_timetable(filepath)
        except FileNotFoundError:
            print(f"File {filepath} not found.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break
        time.sleep(interval)

def reload_timetable(filename):
    global timetable
    timetable = read_timetable(filename)
    print("Timetable data reloaded successfully.")


# ---------------------- Flask Web Routes ---------------------- #
@app.route('/', methods=['GET', 'POST'])
def index():
    # Uses global station_name, query_port, and neighbours set in main()
    if request.method == 'POST':
        destination = request.form.get('destination', "default")
        # Expect departureTime in HH:MM format; remove ':' for processing
        departure_time = request.form.get('departureTime', "23:59").replace(":", "")
        update_leave_time(departure_time)
        new_timetable = read_timetable(f"tt-{station_name}")
        response_content = process_form_data(destination, new_timetable, query_port, neighbours, station_name)
        return render_template('index.html', response=response_content)
    return render_template('index.html', response="Welcome to the Transportation System")

def run_flask_app(port):
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


# ---------------------- Message & UDP Functions ---------------------- #
def process_form_data(destination, timetable, query_port, neighbours, station_name):
    if destination == station_name:
        return "Destination is the same as the current station."
    else:
        print(f"Destination not found: {destination}")
        message = create_message('QUERY', destination, station_name, query_port, 0, 4, query_port, "(" + station_name)
        ask_neighbours_about_destination(destination, query_port, neighbours, message, station_name)
        route_discovery_completed.wait(timeout=30)
        route_discovery_completed.clear()
        best_route = routing_results.pop(destination, "Route not found")
        global response_timer
        response_timer = None
        if best_route == "Route not found":
            if destination in timetable:
                response_content = f"Direct connection to {destination} will arrive at {timetable[destination][0]['arrival_time']}"
            else:
                response_content = f"No Valid Route to {destination}"
        else:
            response_content = f"Best route to {destination}: {best_route}"
        return response_content

def udp_client(message, host, port, msg_id, resend_count=0):
    full_message = f"{msg_id}|{message}"
    print(f"Sending message: {full_message} to {host}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        try:
            client_socket.sendto(full_message.encode(), (host, port))
            if (message.startswith('QUERY') or message.startswith('RESPONSE')) and not message.startswith('RESPONSE_TIMETABLE'):
                pending_acknowledgements[msg_id] = {
                    'time': time.time(),
                    'message': message,
                    'host': host,
                    'port': port,
                    'resend_count': resend_count,
                    'msg_id': msg_id
                }
        except Exception as e:
            print(f"Error sending to {host}:{port}: {e}")

def check_acknowledgments():
    timeout = 2  # seconds
    max_resends = 2
    while True:
        current_time = time.time()
        for msg_id, details in list(pending_acknowledgements.items()):
            if current_time - details['time'] > timeout:
                if details['resend_count'] < max_resends:
                    print(f"Timeout for message ID {msg_id}, resending...")
                    resend_message(msg_id, details)
                else:
                    print(f"Failed to receive ACK for message ID {msg_id} after one resend. Giving up.")
                    pending_acknowledgements.pop(msg_id)
        time.sleep(1)

def resend_message(msg_id, details):
    details['resend_count'] += 1
    details['time'] = time.time()
    udp_client(details['message'], details['host'], details['port'], msg_id, details['resend_count'])

def ask_neighbours_about_destination(destination, query_port, neighbours, message, station_name):
    for neighbour in neighbours:
        host, port = neighbour.split(':')
        udp_client(message, IP.SERVER_IP, int(port), generate_uuid())

def forward_message(message, neighbours, sender_address, port, station_name):
    new_hop_count = message['hop_count'] + 1
    new_path = message['path'] + "," + "(" + station_name
    forwarded_message = create_message('QUERY', message['destination'], message['source'], message['source_port'], new_hop_count, message['max_hops'], port, new_path)
    for neighbour in neighbours:
        host, port = neighbour.split(':')
        if f"{IP.SERVER_IP}:{message['sender']}" != f"{host}:{port}":
            udp_client(forwarded_message, host, int(port), generate_uuid())

def create_message(msg_type, destination, source, source_port, hop_count, max_hops, sender, station_name):
    path = station_name + "," + str(sender) + ")"
    return f"{msg_type}|{destination}|{source}|{source_port}|{hop_count}|{max_hops}|{sender}|{path}"

def create_message2(msg_type, destination_to_look_for, time_to_look_for, source_port):
    return f"{msg_type}|{destination_to_look_for}|{time_to_look_for}|{source_port}"

def create_message3(msg_type, journey):
    return f"{msg_type}|{journey}"

def parse_message(data):
    parts = data.split('|')
    if parts[0] in ['RESPONSE', 'QUERY']:
        return {
            'type': parts[0],
            'destination': parts[1],
            'source': parts[2],
            'source_port': parts[3],
            'hop_count': int(parts[4]),
            'max_hops': int(parts[5]),
            'sender': parts[6],
            'path': parts[7]
        }
    elif parts[0] == 'REQUEST_TIMETABLE':
        return {
            'type': parts[0],
            'destination_to_look_for': parts[1],
            'time_to_look_for': parts[2],
            'source_port': parts[3]
        }
    elif parts[0] == 'RESPONSE_TIMETABLE':
        return {
            'type': parts[0],
            'journey': parts[1],
        }

def udp_server(port, timetable, neighbours, seen_requests, station_name, allpossibleroutes):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(('0.0.0.0', port))
        print(f"UDP server listening on port {port}...")
        while True:
            data, address = server_socket.recvfrom(1024)
            decodeddata = data.decode()
            if decodeddata.startswith("ACK"):
                _, ack_id = decodeddata.split('|')
                if ack_id in pending_acknowledgements:
                    print(f"Received ACK for message ID {ack_id}")
                    pending_acknowledgements.pop(ack_id, None)
                continue
            msg_id, msg_content = decodeddata.split('|', 1)
            print("msg_content:", msg_content)
            message = parse_message(msg_content)
            print("Parsed message:", message)
            if message['type'] in ['QUERY', 'RESPONSE']:
                send_acknowledgment(msg_id, IP.SERVER_IP, int(message['sender']))
                print(f"Received message: {message} from {address}")
            if message['type'] == 'RESPONSE_TIMETABLE':
                if msg_id in pending_responses:
                    pending_responses[msg_id]['data'] = message['journey']
                    pending_responses[msg_id]['event'].set()
            if message['type'] == 'REQUEST_TIMETABLE':
                respond_with_timetable(message, timetable, port, msg_id)
            if message['type'] == 'QUERY':
                request_id = f"{message['source']}-{message['destination']}"
                if message['destination'] == station_name:
                    pass
                else:
                    if request_id not in seen_requests or seen_requests[request_id] < 3:
                        seen_requests[request_id] = seen_requests.get(request_id, 0) + 1
                        if message['hop_count'] < message['max_hops']:
                            forward_message(message, neighbours, address, port, station_name)
                        if message['destination'] in timetable:
                            response = create_message('RESPONSE', message['destination'], station_name, message['source_port'], message['hop_count'], message['max_hops'], str(port), message['path'] + "," + "(" + station_name)
                            udp_client(response, IP.SERVER_IP, int(message['source_port']), msg_id)
                        print(f"Query received on {station_name} from {message['sender']}")
            if message['type'] == 'RESPONSE':
                message['path'] = message['path'] + "," + "(" + message['destination'] + "," + 'None' + ")"
                allpossibleroutes.append(message['path'])
                print(f"Response received on {station_name} from {message['sender']}")
                print("All possible routes discovered:", allpossibleroutes)
                global response_timer
                if response_timer is None:
                    print("Starting response timer")
                    response_timer = threading.Timer(10.0, process_discovered_routes, [route_discovery_done, allpossibleroutes, timetable, message['destination'], station_name])
                    response_timer.start()

def process_discovered_routes(route_discovery_done, allpossibleroutes, timetable, destination, station_name):
    print("\n\nTimeout reached. Assuming all routes have been collected.")
    destination_reached_messages = []
    start_time = integer_to_epoch_time(leave_time_int)
    if destination in timetable:
        for detail in timetable[destination]:
            departure_time_epoch = convert_to_epoch(detail['departure_time'])
            if departure_time_epoch > integer_to_epoch_time(leave_time_int):
                start_time = convert_to_epoch(detail['arrival_time'])
                routemessage = "Destination reached at " + detail['arrival_time'] + " through route: catch " + detail['bus_train'] + " at " + detail['departure_time'] + " from " + station_name + " to " + "next_station" + " arriving at " + detail['arrival_time']
                destination_reached_messages.append(routemessage)
            break
    for route in allpossibleroutes:
        route_discovery_done.set()
        start_time = integer_to_epoch_time(leave_time_int)
        stations_ports = route.strip().split('),')
        stations_ports = [tuple(sp.strip().strip('()').split(',')) for sp in stations_ports]
        stations_ports = [(station.strip(), port.strip()) for station, port in stations_ports]
        route_string = ''
        source_station, source_port = stations_ports[0]
        for i in range(len(stations_ports)):
            if i == len(stations_ports)-1:
                break
            current_station, current_port = stations_ports[i]
            next_station, next_port = stations_ports[i+1]
            if i == 0:
                if next_station in timetable:
                    for detail in timetable[next_station]:
                        departure_time_epoch = convert_to_epoch(detail['departure_time'])
                        if departure_time_epoch > start_time:
                            route_string = "Catch " + detail['bus_train'] + " at " + detail['departure_time'] + " from " + current_station + " to " + next_station + " arriving at " + detail['arrival_time'] + " Then"
                            start_time = detail['arrival_time']
                            break
            else:
                message_id, event = request_timetable(source_port, current_port, next_station, start_time)
                event.wait()
                response_data = pending_responses.pop(message_id, None)
                if response_data and response_data['data'] == '':
                    print("Journey could not be completed before midnight. Hence, route is invalid")
                    continue
                else:
                    data_parts = response_data['data'].split(',')
                    if len(data_parts) > 1:
                        departure_time = data_parts[0]
                        whichbus = data_parts[1]
                        arrival_time = data_parts[2]
                        route_string = route_string + whichbus + " at " + departure_time + " from " + current_station + " to " + next_station + " arriving at " + arrival_time.strip() + " Then"
                        if i == len(stations_ports)-2:
                            time_reach = "Destination reached at " + arrival_time.strip()
                            routeemessagee = str(time_reach + " through route : " + route_string[:-4])
                            destination_reached_messages.append(routeemessagee)
                        else:
                            try:
                                start_time = arrival_time
                            except ValueError as e:
                                print(f"Error converting time: {departure_time}. Error: {e}")
    print("\n\nDestination reached messages:", destination_reached_messages)
    flag = 0
    if len(destination_reached_messages) == 0:
        flag = 1
    best_route = calculate_best_route(destination_reached_messages, flag)
    print(best_route)
    routing_results[destination] = best_route
    route_discovery_completed.set()

def calculate_best_route(destination_reached_messages, flag):
    if flag == 1:
        return "No valid journey before midnight."
    best_time = "23:59"
    time_message_dict = {}
    for message in destination_reached_messages:
        time_part = message.split(' ')[3]
        if time_part < best_time:
            best_time = time_part
        time_message_dict[message] = time_part
    best_route = [message for message, time in time_message_dict.items() if time == best_time]
    return best_route

def request_timetable(source_port, current_port, next_station, start_time):
    event = Event()
    message_id = generate_uuid()
    pending_responses[message_id] = {'event': event, 'data': None}
    message = create_message2('REQUEST_TIMETABLE', next_station, start_time, source_port)
    udp_client(message, IP.SERVER_IP, int(current_port), message_id)
    return message_id, event

def respond_with_timetable(message, timetable, port, message_id):
    destination = message['destination_to_look_for']
    message['time_to_look_for'] = message['time_to_look_for'].strip()
    try:
        start_time = convert_to_epoch(message['time_to_look_for'])
    except:
        start_time = int(float(message['time_to_look_for']))
    source_port = message['source_port']
    journey = ''
    if destination in timetable:
        for detail in timetable[destination]:
            departure_time_epoch = convert_to_epoch(detail['departure_time'])
            if departure_time_epoch > start_time:
                journey = f"{detail['departure_time']}, Catch {detail['bus_train']},{detail['arrival_time']}\n"
                break
        response = create_message3('RESPONSE_TIMETABLE', journey)
    udp_client(response, IP.SERVER_IP, int(message['source_port']), message_id)

def send_acknowledgment(msg_id, host, port):
    acknowledgment = f"ACK|{msg_id}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.sendto(acknowledgment.encode(), (host, port))


# ---------------------- Main Function ---------------------- #
def main():
    global station_name, query_port, neighbours
    ip_address = get_mac_ip()
    IP.SERVER_IP = ip_address
    print(f"IP Address of en0: {IP.SERVER_IP}")
    if len(sys.argv) < 5:
        print("Usage: ./station-server.py station-name browser-port query-port neighbours... [format: host:port]")
        sys.exit(1)
    station_name = sys.argv[1]
    browser_port = int(sys.argv[2])
    query_port = int(sys.argv[3])
    neighbours = sys.argv[4:]
    seen_requests = {}
    allpossibleroutes = []
    # Initialize globals for UDP communication
    global response_timer, pending_responses, pending_acknowledgements
    pending_acknowledgements = {}
    pending_responses = {}
    timetable_filename = f"tt-{station_name}"
    print(f"Station Name: {station_name}")
    print(f"Browser Port: {browser_port}")
    print(f"Query Port: {query_port}")
    print(f"Neighbours: {neighbours}")
    routing_results.clear()
    route_discovery_completed.clear()

    # Start the Flask web server in a separate thread.
    flask_thread = threading.Thread(target=run_flask_app, args=(browser_port,), daemon=True)
    flask_thread.start()

    # Start the UDP server and file monitor threads.
    new_timetable = read_timetable(timetable_filename)
    udp_server_thread = threading.Thread(target=udp_server, args=(query_port, new_timetable, neighbours, seen_requests, station_name, allpossibleroutes), daemon=True)
    file_monitor_thread = threading.Thread(target=monitor_file_changes, args=(timetable_filename,), daemon=True)
    file_monitor_thread.start()
    udp_server_thread.start()

    print("Servers are running. Press CTRL+C to exit.")
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("Shutting down servers. Please wait...")
        if response_timer:
            response_timer.cancel()
    udp_server_thread.join()
    print("Servers have been shut down gracefully.")

if __name__ == "__main__":
    main()
