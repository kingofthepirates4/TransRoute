# TransRoute

**TransRoute** is a dynamic, distributed transit network simulator that demonstrates advanced ad-hoc routing in a user-friendly, configurable environment. The project combines an automated GUI-based configuration tool, backend station servers implemented in both Python and C, and a polished Flask web interface for querying transit routes and visualizing network topology.

## Overview

TransRoute simulates a public transport network where each station is represented by an independent server process. These servers:
- **Manage Local Timetable Data:** Auto-generated to ensure error-proof configuration.
- **Communicate via UDP/TCP:** Exchange routing information with neighboring stations and serve HTTP requests.
- **Support Dynamic Route Discovery:** Using a reactive, on-demand routing mechanism inspired by protocols like AODV.

The system minimizes manual configuration by automatically generating station names, port assignments, timetables, and neighbor relationships. Users simply choose the number of stations and set a few high-level parameters—TransRoute takes care of the rest.

## Key Features

- **Automated Configuration:**
  - **GUI Tool:** Enter the number of stations and adjust high-level settings.
  - **Auto-Generation:** The system generates station names, port assignments, timetables, and neighbor connections.
  - **Visualization:** Displays a summary, interactive network graph, and an adjacency matrix for review.
  
- **Distributed Station Servers:**
  - Implementations in both **Python** and **C** run as independent processes.
  - Each station server reads its configuration from auto-generated files and communicates using a custom UDP/TCP protocol.
  - Responds to HTTP queries with a simple HTML interface.

- **Flask-Based Web Interface:**
  - A modern, user-friendly website that allows users to:
    - Query routes between stations.
    - View real-time network topology and timetable updates.
    - See interactive visualizations of discovered routes.
  
- **Robust, Reactive Routing:**
  - Utilizes controlled flooding (RREQ/RREP) for dynamic multi-hop route discovery.
  - Automatically updates routes when timetable data changes.
  - Handles concurrent queries and reports valid journeys or errors gracefully.

## Architecture

TransRoute is organized into three main components:

1. **GUI Configuration Tool:**
   - A desktop application (built in Python using Tkinter or PyQt) where users specify the number of stations and high-level parameters.
   - Automatically generates station configuration files and a startup script.
   - Provides visual feedback with network graphs and timetable previews.

2. **Distributed Station Servers:**
   - Two independent implementations (Python and C) that run as separate processes.
   - Each station server reads its configuration, listens on assigned ports, and exchanges messages with neighbors.
   - Uses UDP for inter-station communications and TCP for HTTP interactions.

3. **Flask Web Interface:**
   - A polished web application that provides an intuitive interface for querying routes and visualizing the network.
   - Integrates real-time updates and interactive visualizations using JavaScript libraries.

## Installation and Setup

### Prerequisites
- Python 3.8+  
- C Compiler (e.g., GCC)  
- Git  
- (Optional) Tkinter or PyQt5/PySide2 for the GUI tool  
- Flask and other required Python libraries (see `requirements.txt`)

### Clone the Repository
```bash
git clone https://github.com/yourusername/TransRoute.git
cd TransRoute
