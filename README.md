# Biodesign Center IoT Network

A wireless sensor network for monitoring lab environments (fridges, doors, current draw, light events) in real time. Sensor nodes transmit readings over LoRa radio to a receiver bridge, which feeds a Windows host application that pushes data to a Grafana Cloud dashboard.

---

## Conceptual Overview

The system has three physical layers:

1. **Transmitter nodes** — Adafruit Feather RP2040 + RFM95 LoRa boards flashed with CircuitPython firmware. Each node reads one or more sensors and periodically broadcasts packets over 915 MHz LoRa radio.
2. **Receiver node** — An identical RP2040 board acting as a transparent radio-to-serial bridge. It listens for all transmitter packets and forwards raw bytes to a host PC over USB serial.
3. **Host PC application** — A Windows `.exe` that reads the receiver's serial output, decodes packets, and pushes sensor readings to Grafana Cloud.

### Roles

| Role | What they do |
|------|-------------|
| **Lab technician / operator** | Runs the host app on a Windows machine, starts listening, selects which sensor nodes to broadcast to the dashboard. |
| **Hardware deployer** | Uses the Flash Device tab to configure and flash new sensor nodes or re-flash existing ones to change sensor configuration or recalibrate thresholds. May need to remove a board from its enclosure to plug it in. |
| **Dashboard viewer** | Monitors sensor data and node status via Grafana Cloud. No interaction with the desktop app required. |
| **Developer / template author** | Adds new sensor types by writing sensor template files, rebuilds the `.exe` via PyInstaller, maintains firmware and host app code. |

---

## Functional Requirements

| ID | Requirement | How it is met |
|----|-------------|---------------|
| **FR-01** | The product will allow for the sensing of fridge temperature. The sensor will be able to determine the ambient temperature inside the fridge. | DS18B20 OneWire temperature sensor template (`hardware/sensor_templates/temperature_ds18b20.py`). |
| **FR-02** | The product will allow for the sensing of fridge door status. The sensor will be able to determine if the fridge door is opened or closed. | Digital push-button door sensor template (`hardware/sensor_templates/door_button.py`). |
| **FR-03** | The product will allow for the sensing of colored light. The sensor will be able to detect the blue light from the doorbell when it rings. | TSL2591 I2C light event sensor template with configurable threshold (`hardware/sensor_templates/light_event_tsl2591.py`). |
| **FR-04** | The product will collect hours of operation data from multiple 3D printers. The hours of operation of the resin 3D printers will be tracked through current sensing. | CTS-CS-CAX-04 current transformer template with RMS sensing and calibration mode (`hardware/sensor_templates/current_amps_cts-cs-cax-04.py`). |
| **FR-05** | Sensor readings will be displayed on the laptop. | Data Stream tab in the host app shows a live scrolling log; Grafana Cloud dashboard displays all sensor data. |
| **FR-06** | The product will have a 3D printed enclosure that can be opened or closed as well as a USB port. This will allow easy access to the internals of the sensor for troubleshooting. | Hardware design (out of software scope). The Flash Device tab supports re-flashing once the board is removed from the enclosure. |
| **FR-07** | The sensors will be a peripheral device that could be attached to the equipment. The sensors will not be hard-wired into the equipment for easy installation and no interference. | Transmitter nodes communicate over 915 MHz LoRa radio; no physical wiring to monitored equipment is required. |
| **FR-08** | The product will send sensor data to a Windows 11 Laptop. The data from all the sensors will be sent wirelessly to a Windows 11 laptop which will have a local server that will then send the sensor data to the cloud dashboard. | Receiver node bridges LoRa packets to USB serial; the host app (`windows-exe/`) reads the serial output on Windows. |
| **FR-09** | The user can check the local server, which contains a list of broadcasting sensors that can be selected from. The sensors will connect to the local server through LoRa. | Receiver Pairing tab (tab 2) lists all nodes discovered over LoRa this session or loaded from saved state, with per-node listen toggle. |
| **FR-10** | The system will send the collected sensor data from the local server to a cloud dashboard. Local server will collect the sensor data and send it to the cloud dashboard which could display the data. | Host app formats readings as InfluxDB line protocol and pushes to Grafana Cloud (`windows-exe/grafana.py`). |
| **FR-11** | The system will allow users to log in. The users will be able to log in to access the dashboard, making the sensor information secure. | Grafana Cloud authentication — dashboard access requires a Grafana login. |
| **FR-12** | The system will allow users to view sensor data. The users will be able to view the sensor data on a dashboard (temperature, door status, doorbell status, hours of operation, and sensor status for each sensor). | All sensor readings and node status metrics are pushed to Grafana Cloud and visible on the dashboard. |
| **FR-13** | The sensors will be powered by standard 120v plugs. The sensors will be continuously powered from wall outlets and will not have to rely on batteries. | Hardware design (out of software scope). |
| **FR-14** | The system will allow users to view if a sensor is down. The dashboard will display the status of the sensor. | Node status metrics (online / degraded / offline) are pushed to Grafana every 30 seconds (`windows-exe/grafana.py`). |
| **FR-15** | The system will send a push notification when the temperature crosses a threshold. A text message or email alert will be sent about the status of the temperature in the fridge. | Alert rules are configured in Grafana Cloud (not part of this codebase). Grafana supports email and webhook notifications when a metric crosses a defined threshold. |

---

## Host Application Specification

### Tab 1 — Data Stream

- Start and stop the serial read loop (connects to the receiver over USB)
- Auto-detect the correct COM port; prompt the user to choose if ambiguous
- Display a scrolling log of all received packets and Grafana push results
- Warn if no data is received from the receiver for more than 30 seconds

### Tab 2 — Receiver Pairing

- List all transmitter nodes discovered this session or loaded from saved state
- Show each node's lab ID, node ID, optional name, and last-seen time
- Toggle "Listen" per node (only listened nodes are pushed to Grafana)
- Forget a node entirely (removes from all state and flash history)
- Persist listen state and node names across application restarts

### Tab 3 — Known Flashes

- List all previously flashed nodes with their name, lab/node ID, flash timestamp, and sensor summary
- Re-flash a saved node: pre-populate the Flash Device tab with the same configuration so the user only needs to pick a drive and click Flash
- Delete a saved flash record without affecting the node's pairing state

### Tab 4 — Flash Device

- Select role: transmitter or receiver
- Enter Lab ID and Node ID for transmitter flashing
- Browse available sensor types (auto-discovered from `hardware/sensor_templates/`)
- Add sensors to the node configuration, choosing pin assignments and parameters per sensor
- Preview generated `sensors.py` and `config.py` before flashing
- Auto-detect or manually select the mounted CircuitPython drive
- Flash: generate firmware files, copy them plus required libraries onto the board
- Block re-use of an already-active node ID unless the user explicitly confirms a re-flash
- Prompt for a unique name after a successful flash

---

## Third-Party Integrations

| Service | Purpose |
|---------|---------|
| **Grafana Cloud** | Time-series dashboard for sensor readings and node status. The host app formats data as InfluxDB line protocol and pushes to the Grafana Cloud push endpoint. Credentials (URL, username, API token) are loaded from a `.env` file at runtime. Node status metrics (online / degraded / offline) are pushed every 30 seconds alongside sensor readings. |

No other third-party services (auth providers, payment processors, etc.) are used.

---

## Tech Stack

Desktop application:

| Layer | Technology |
|-------|-----------|
| **Host application** | Python 3, Tkinter (GUI) |
| **Firmware** | CircuitPython (Python subset for microcontrollers) |
| **Packaging** | PyInstaller — bundles the host app into a standalone Windows `.exe` |
| **Serial communication** | pyserial |
| **Grafana push** | requests (HTTP POST, InfluxDB line protocol) |
| **Environment config** | python-dotenv |
| **Microcontroller** | Adafruit Feather RP2040 + RFM95 LoRa 915 MHz |
| **Radio protocol** | LoRa 915 MHz, custom binary packet format (v1) |
| **Dashboard** | Grafana Cloud |

No database is used. Persistent state (node names, listen toggles, flash history) is stored in `%LOCALAPPDATA%\biosensing\state.json`.

---

## Deployment Notes

The host application is distributed as a standalone Windows executable (`windows-exe/dist/app.exe`) built with PyInstaller. No installation is required on the end user's machine beyond copying the `.exe` and a `.env` file.

---

## Development Environment Setup

### Prerequisites

- Python 3.10+ with `pip`
- A Python virtual environment tool (`venv`)
- CircuitPython-compatible boards (Adafruit Feather RP2040 + RFM95) for hardware testing
- A Grafana Cloud account for dashboard testing

### 1. Clone the repository

```
git clone <repo-url>
cd Biodesign-Center-IoT-Network
```

### 2. Set up credentials

Copy `.env.example` to `.env` (in windows-exe) and fill in your Grafana Cloud credentials:

```
cp .env.example .env
```

Edit `.env`:

```
GRAFANA_CLOUD_URL=https://prometheus-prod-XX-prod-us-REGION.grafana.net/api/v1/push/influx/write
GRAFANA_CLOUD_USERNAME=your_username
GRAFANA_CLOUD_API_TOKEN=your_api_token
```

The `.env` file must be placed in the same directory you build from. If the Grafana token is misconfigured, this is likely why.

### 3. Set up a virtual environment and install dependencies

```
cd windows-exe
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 4. Build the Windows executable

From inside the `windows-exe/` directory with the venv active:

```
pyinstaller app.spec
```

Output is written to `windows-exe/dist/app.exe`.

---

## How to Flash Hardware

### Install Software on Hardware

Download the `.exe` from the `windows-exe/dist/` folder (or build it from source as above).

**If creating a new sensor type:**

1. Download the full GitHub repo.
2. Create the new sensor file in `hardware/sensor_templates/`.
3. Create or activate a Python venv.
4. Install all requirements in `windows-exe/requirements.txt`.
5. Run PyInstaller on `app.spec`.
6. Follow the steps below — you should see the new sensor type in the sensor list.

**Flashing a microcontroller:**

1. Run the `.exe`.
2. Plug the microcontroller you want to flash into the computer running the `.exe`.
   - For current nodes, this will require removing the microcontroller from its enclosure.
3. Go to the **Flash Device** tab (tab 4).

**If re-flashing an existing sensor** (e.g., to recalibrate thresholds):

- If the node has been flashed before: go to the **Known Flashes** tab (tab 3) and press **Re-flash**. Select the desired sensors. To change pre-selected values, delete and re-add the sensor.
- Otherwise: go to the **Receiver Pairing** tab (tab 2) and **Forget** the node first. Then go to the **Flash Device** tab and select the desired sensors.

**If flashing a new node:**

1. Go to the **Flash Device** tab (tab 4).
2. Select the desired sensors.
3. Select the drive of the microcontroller to flash. **Detect** selects the first detected drive — verify it is the correct one.
4. Click **Flash**.

> **Note on current sensors:** Current sensors have a calibration mode that outputs the base ADC value when no current is flowing. Take multiple readings and average them. The output is formatted as `2NNNNNN`; the average should be entered as `2.NNNNNN` (insert a decimal point after the first digit).

---

## How to Set Up the Local Server (Receiver / Host App)

1. Download the `.exe` from `windows-exe/dist/` (or build from source).
4. Go to the **Data Stream** tab (tab 1) and click **Start Listening**.
5. After listening starts, the **Receiver Pairing** tab (tab 2) will begin to populate with all broadcasting sensor nodes.
6. Select all nodes you want to broadcast to the Grafana dashboard by toggling **Listen** for each one.
7. Verify data is appearing in Grafana Cloud.
