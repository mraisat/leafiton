import json                     # turns Python data into JSON for the web page
import os                       # finds the folder this file is in
import threading                # lets serial reading and the web server run at the same time
import time                     # measures time between readings
from datetime import datetime   # makes the clock times shown in the activity log
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler  # tiny built-in web server
import serial                   # pyserial: reads the Arduino over USB

PORT_NAME = "COM3"              # the Arduino's USB port on this laptop
BAUD = 9600                     # same speed as Serial.begin(9600) on the Uno
WEB_PORT = 8000                 # open http://localhost:8000 in the browser
ROOM_NAME = "Omra & Raisa"      # name shown for the live room
WATTS = 60                      # assumed power of the room lights, in watts
SPEED = 600                     # demo speed-up so the kWh number visibly moves
IDLE_LIMIT = 10                 # seconds before waste; must match NO_MOTION_LIMIT on the Uno

FOLDER = os.path.dirname(os.path.abspath(__file__))  # folder holding this file and index.html

lock = threading.Lock()         # stops the two threads from editing state at the same moment
state = {                       # everything the web page asks for at /api/state
    "lights": False,            # are the room lights on?
    "motion": False,            # is someone moving right now?
    "idle_seconds": 0,          # seconds the room has been lit and empty
    "warning": False,           # true while energy is being wasted (buzzer beeping)
    "relay_cut": False,         # no relay anymore, so this stays false
    "wasted_kwh": 0.50,         # running total of wasted energy
    "log": [],                  # recent events for the activity list
    "room_name": ROOM_NAME,     # shown on the page
    "idle_limit": IDLE_LIMIT,   # shown on the page as "warning at 0:10"
}


def add_log(kind, msg):                                        # add one line to the activity list
    t = datetime.now().strftime("%I:%M:%S %p").lstrip("0")     # current time, like 5:09:42 PM
    state["log"].insert(0, {"time": t, "kind": kind, "msg": msg})  # newest event goes first
    del state["log"][20:]                                      # keep only the last 20 events


def read_serial():                                             # runs forever in the background
    try:
        ser = serial.Serial(PORT_NAME, BAUD, timeout=2)        # open the Arduino's port
    except serial.SerialException as e:                        # port missing or busy
        print("Could not open", PORT_NAME, "-", e)             # explain what went wrong
        print("Close the Arduino IDE / read_arduino.py and check the USB cable.")  # how to fix it
        return                                                 # stop this thread
    print("Connected to Arduino on", PORT_NAME)                # confirm it worked
    last = time.time()                                         # time of the previous reading
    while True:                                                # keep reading forever
        line = ser.readline().decode(errors="ignore").strip()  # read one line as text
        if not line.startswith("DATA,"):                       # skip anything that isn't our data
            continue
        parts = line.split(",")                                # split at the commas
        if len(parts) != 6:                                    # skip broken or half lines
            continue
        try:
            lights = parts[2] == "1"                           # lights on?
            motion = parts[3] == "1"                           # motion right now?
            still = int(parts[4])                              # seconds since last motion
            waste = parts[5] == "1"                            # Uno says energy is wasted?
        except ValueError:                                     # garbled numbers
            continue
        now = time.time()                                      # time of this reading
        dt = now - last                                        # seconds since the last reading
        last = now                                             # remember for next time
        with lock:                                             # edit state safely
            if lights != state["lights"]:                      # lights changed
                add_log("lights_on" if lights else "lights_off",
                        "Lights turned on" if lights else "Lights turned off")
            if motion and not state["motion"]:                 # motion just started
                add_log("motion", "Motion detected")
            if waste and not state["warning"]:                 # waste just started
                add_log("warn", "Lights on in an empty room, buzzer warning")
            if not waste and state["warning"]:                 # waste just stopped
                add_log("power_on", "Waste stopped")
            if waste:                                          # add up wasted energy
                state["wasted_kwh"] += WATTS / 1000 / 3600 * dt * SPEED
            state["lights"] = lights                           # save the new values
            state["motion"] = motion
            state["idle_seconds"] = still if lights and not motion else 0  # only count when lit and empty
            state["warning"] = waste


class Handler(SimpleHTTPRequestHandler):                       # answers the browser's requests
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FOLDER, **kwargs)    # serve files from this folder

    def do_GET(self):                                          # called for every page request
        if self.path.startswith("/api/state"):                 # the page asking for live data
            with lock:
                body = json.dumps(state).encode()              # turn state into JSON bytes
            self.send_response(200)                            # "OK"
            self.send_header("Content-Type", "application/json")  # tell the browser it's JSON
            self.send_header("Content-Length", str(len(body)))    # size of the reply
            self.send_header("Cache-Control", "no-store")         # always send fresh data
            self.end_headers()
            self.wfile.write(body)                             # send it
        else:
            super().do_GET()                                   # otherwise send index.html etc.

    def log_message(self, *args):                              # hide the request spam in PowerShell
        pass


threading.Thread(target=read_serial, daemon=True).start()     # start reading the Arduino in the background
print(f"Open http://localhost:{WEB_PORT} in your browser (Ctrl + C to stop)")  # where to look
ThreadingHTTPServer(("", WEB_PORT), Handler).serve_forever()  # start the web server
