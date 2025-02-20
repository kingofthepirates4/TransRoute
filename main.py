import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import sys
import webbrowser
import os
import time

# ------------------- Helper Functions ------------------- #
def remove_quarantine(file_path):
    try:
        result = subprocess.run(
            ["xattr", "-l", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace"
        )
        if "com.apple.quarantine" in result.stdout:
            print(f"Removing quarantine attribute from {file_path}...")
            subprocess.run(["xattr", "-d", "com.apple.quarantine", file_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error removing quarantine attribute from {file_path}: {e}")

def view_topology():
    if sys.platform == "darwin":
        subprocess.run(["open", "adjacency"], check=True)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", "adjacency"], check=True)
    elif sys.platform == "win32":
        subprocess.run(["notepad.exe", "adjacency"], check=True)
    else:
        print("Unsupported platform.")

def view_timetables():
    if sys.platform == "darwin":
        subprocess.run(["open", "."], check=True)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", "."], check=True)
    elif sys.platform == "win32":
        subprocess.run(["explorer.exe", "."], check=True)
    else:
        print("Unsupported platform.")

def read_configurations():
    """
    Reads the startstations.sh file and parses each line to extract the station name and browser port.
    Returns a list of dictionaries, each with keys: 'station', 'browser_port'.
    
    Expected line format (tokens):
    ./station-server.py <StationName> <BrowserPort> <QueryPort> <Neighbour1> [...]
    """
    configs = []
    if not os.path.exists("startstations.sh"):
        print("startstations.sh not found.")
        return configs

    with open("startstations.sh", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Remove any leading './' and trailing '&' because they are not part of the station name.
            line = line.lstrip("./").rstrip(" &")
            tokens = line.split()
            if len(tokens) >= 3:
                station = tokens[1]
                browser_port = tokens[2]  # Using the browser port (second token)
                configs.append({"station": station, "browser_port": browser_port})
    return configs

def start_selected_station(config):
    """
    Opens the URL for the selected station using its browser port.
    """
    url = f"http://localhost:{config['browser_port']}"
    print(f"Opening {url} for station {config['station']}")
    webbrowser.open(url)

def setup_new_screen(num_stations):
    # Clear all existing widgets from the root window. 
    for widget in root.winfo_children():
        widget.destroy()
    root.geometry("600x500")
    
    info_label = tk.Label(root, text=f"We have randomly generated {num_stations} servers.",
                          bg="green", fg="white", font=("Helvetica", 24))
    info_label.pack(pady=10)
    
    button_frame = tk.Frame(root, bg="green")
    button_frame.pack(pady=10)
    
    topology_button = tk.Button(button_frame, text="View Network Topology",
                                font=("Helvetica", 14), bg="white", fg="green", command=view_topology)
    topology_button.grid(row=0, column=0, padx=10)
    
    timetables_button = tk.Button(button_frame, text="View Timetables",
                                  font=("Helvetica", 14), bg="white", fg="green", command=view_timetables)
    timetables_button.grid(row=0, column=1, padx=10)
    
    # Station selection question.
    question_frame = tk.Frame(root, bg="green")
    question_frame.pack(pady=10)
    
    start_label = tk.Label(question_frame, text="Which station would you like to start with?",
                           bg="green", fg="white", font=("Helvetica", 18))
    start_label.pack()
    
    # Reading configurations from startstations.sh to populate the station dropdown.
    configs = read_configurations()
    if not configs:
        error_label = tk.Label(root, text="No station configurations found.", 
                               bg="green", fg="red", font=("Helvetica", 18))
        error_label.pack(pady=20)
        return
    
    # Building dropdown options in the format "StationName (BrowserPort: XXXX)"
    dropdown_options = [f"{conf['station']} (BrowserPort: {conf['browser_port']})" for conf in configs]
    
    selected_station_var = tk.StringVar()
    selected_station_var.set(dropdown_options[0])

    dropdown_frame = tk.Frame(root, bg="green")
    dropdown_frame.pack(pady=5)
    
    start_dropdown = ttk.Combobox(dropdown_frame, textvariable=selected_station_var,
                                  values=dropdown_options, font=("Helvetica", 14), state="readonly", width=30)
    start_dropdown.pack()
    
    # Start button to open the URL for the selected station.
    def on_start():
        selected_text = selected_station_var.get()
        for conf in configs:
            option_text = f"{conf['station']} (BrowserPort: {conf['browser_port']})"
            if selected_text == option_text:
                start_selected_station(conf)
                break
    
    start_button = tk.Button(root, text="Start", command=on_start,
                             font=("Helvetica", 16), bg="white", fg="green")
    start_button.pack(pady=20)
    
    print("New GUI screen is now displayed with station selection.")

def launch_network():
    num_stations = station_var.get()
    print(f"Launching network with {num_stations} stations")
    
    # Removing quarantine attributes from required scripts.
    remove_quarantine("station-server.sh")
    remove_quarantine("assignports.sh")
    remove_quarantine("remove_test_file.sh")
    
    # Run the startup script with the number of stations.
    command = f"./station-server.sh {num_stations}"
    try:
        subprocess.Popen(command, shell=True)
    except subprocess.CalledProcessError as e:
        print("An error occurred while launching the network:", e)
        return
    
    print("Waiting 8 seconds before checking for startstations.sh...")
    time.sleep(8)
    
    # Poll for startstations.sh (up to an additional 30 seconds).
    max_wait = 30  
    waited = 0
    while not os.path.exists("startstations.sh") and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
        print(f"Polling for startstations.sh... ({waited:.1f}s elapsed after initial delay)")
    if not os.path.exists("startstations.sh"):
        print("startstations.sh not found after waiting additional 30 seconds. Network launch may have failed.")
        return
    
    # Update the GUI on the main thread.
    root.after(0, lambda: setup_new_screen(num_stations))

def launch_network_thread():
    thread = threading.Thread(target=launch_network)
    thread.start()

# ------------------- Main GUI Setup ------------------- #
root = tk.Tk()
root.title("TransRoute Configuration")
root.configure(bg="green")
root.geometry("600x200")

label = tk.Label(root, text="How many stations do you want in your network?",
                 bg="green", fg="white", font=("Helvetica", 26))
label.pack(pady=10)

station_var = tk.IntVar()
station_var.set(1)

options = list(range(1, 16))
dropdown = ttk.Combobox(root, textvariable=station_var, values=options,
                        font=("Helvetica", 12), state="readonly")
dropdown.pack(pady=5)

launch_button = tk.Button(root, text="Launch Network", command=launch_network_thread,
                          font=("Helvetica", 14), bg="white", fg="green")
launch_button.config(height=3, width=10)
launch_button.pack(pady=10)

root.mainloop()