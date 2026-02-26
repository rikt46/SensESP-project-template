"""
MicroPython prototype for SensESP project template

This module implements a minimal, easy-to-flash MicroPython application that
reproduces the basic behaviour of the C++ SensESP template in `src/main.cpp`:

- Connect to WiFi
- Read an analog input periodically and publish when it changes
- Monitor a digital input and publish on change
- Toggle a digital output periodically
- Publish Signal K deltas using HTTP POST or optionally WebSocket

The code is written to be readable and to run on a standard MicroPython build
for ESP32. To make unit-testing possible under CPython, tests inject mocks for
the MicroPython-specific modules (`network`, `machine`, `urequests`, etc.).

Configuration is read from `config.json` on the device filesystem. A
`config.json.example` is provided in the `micropython/` folder.

This file is intentionally small and focuses on clarity rather than
performance or complete SensESP feature parity.
"""

# Features: WiFi connect, ADC read, digital input monitor, digital output toggle,
# and simple Signal K delta HTTP publish (adjust endpoint as needed).

import network
import time
import ujson as json
try:
    import urequests as requests
except Exception:
    import requests
import uasyncio as asyncio
from machine import Pin, ADC
# Try to import a websocket client for MicroPython. Several implementations
# exist; try a few common names and fall back to None.
websocket = None
try:
    import uwebsockets.client as websocket
except Exception:
    try:
        import uwebsocket as websocket
    except Exception:
        websocket = None

CONFIG_PATH = "config.json"

# Load config or defaults
DEFAULT_CONFIG = {
    "wifi_ssid": "your_ssid",
    "wifi_password": "your_password",
    "sk_server": "http://192.168.10.3:3000",
    "analog_pin": 36,
    "analog_interval_ms": 500,
    "analog_threshold": 0.01,
    "digital_input_pin": 14,
    "digital_input_poll_ms": 50,
    "digital_output_pin": 15,
    "digital_output_interval_ms": 650,
    "publish_enabled": False
}


def load_config():
    """Load `config.json` from the filesystem.

    If the file does not exist or cannot be parsed, the default configuration
    from `DEFAULT_CONFIG` is written to `config.json` and returned. Keeping
    configuration in JSON makes it easy to edit on-device or via the REPL.
    """
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
    except Exception:
        # Fall back to defaults and attempt to create the file so users get
        # a starting point to edit.
        cfg = DEFAULT_CONFIG
        try:
            with open(CONFIG_PATH, "w") as f:
                f.write(json.dumps(cfg))
        except Exception:
            # If writing fails (read-only FS, etc.), keep going with defaults
            # but don't crash the runtime.
            pass
    return cfg


def connect_wifi(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(ssid, password)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("WiFi connect timeout")
                break
            time.sleep(0.5)
    if wlan.isconnected():
        print("Connected, IP:", wlan.ifconfig())
    return wlan


# Queue for websocket messages (created in main if used)
ws_queue = None


async def publish_signal_k(cfg, path, value):
    """Send a Signal K delta via HTTP POST. Many Signal K servers accept
    delta messages via WebSocket; HTTP endpoints differ. This function posts
    a minimal delta to /signalk/v1/api/vessels/self which may need adapting
    for your server. If `publish_enabled` is False the function will print instead."""
    server = cfg.get('sk_server')
    if not server:
        print('SK publish:', path, value)
        return
    url = server.rstrip('/') + '/signalk/v1/api/vessels/self'
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    delta = {
        "context": "vessels.self",
        "updates": [{
            "source": {"label": "micropython"},
            "timestamp": timestamp,
            "values": [{"path": path, "value": value}]
        }]
    }
    # If websocket is enabled in config, put the delta into the ws queue and
    # let the websocket manager handle the send. Otherwise fall back to HTTP POST.
    if cfg.get('use_ws') and ws_queue is not None:
        try:
            await ws_queue.put(delta)
            return
        except Exception as e:
            print('WS queue error:', e)

    try:
        requests.post(url, data=json.dumps(delta), headers={"Content-Type": "application/json"})
    except Exception as e:
        print('Publish error:', e)


async def ws_manager(cfg):
    """Background task that maintains a websocket connection and sends
    queued Signal K deltas to the server's /signalk/v1/stream endpoint."""
    global ws_queue
    if websocket is None:
        print('No websocket client available; ws disabled')
        return
    if ws_queue is None:
        ws_queue = asyncio.Queue()
    server = cfg.get('sk_server')
    if not server:
        print('No SK server configured for websocket')
        return
    ws_url = server.rstrip('/').replace('http://', 'ws://').replace('https://', 'wss://') + '/signalk/v1/stream'
    while True:
        try:
            print('Connecting websocket to', ws_url)
            # Many MicroPython websocket clients provide a sync connect function
            # that returns a ws object with a `send` method.
            ws = websocket.connect(ws_url)
            print('Websocket connected')
            while True:
                delta = await ws_queue.get()
                try:
                    ws.send(json.dumps(delta))
                except Exception as e:
                    print('WS send error:', e)
                    raise
        except Exception as e:
            print('Websocket manager error:', e)
            await asyncio.sleep(5)


async def analog_loop(cfg):
    pin = cfg.get('analog_pin', 36)
    interval = cfg.get('analog_interval_ms', 500) / 1000.0
    threshold = cfg.get('analog_threshold', 0.01)
    adc = ADC(Pin(pin))
    try:
        adc.atten(ADC.ATTN_11DB)
    except Exception:
        pass
    last = None
    while True:
        raw = adc.read()
        try:
            voltage = raw / 4095.0 * 3.3
        except Exception:
            voltage = float(raw)
        if last is None or abs(voltage - last) > threshold:
            print('Analog value:', voltage)
            if cfg.get('publish_enabled'):
                await publish_signal_k(cfg, 'sensors.analog_input.voltage', voltage)
            last = voltage
        await asyncio.sleep(interval)


async def digital_toggle_loop(cfg):
    pin = cfg.get('digital_output_pin', 15)
    interval = cfg.get('digital_output_interval_ms', 650) / 1000.0
    out = Pin(pin, Pin.OUT)
    state = 0
    while True:
        state = 1 - state
        out.value(state)
        await asyncio.sleep(interval)


async def digital_input_monitor(cfg):
    pin = cfg.get('digital_input_pin', 14)
    poll = cfg.get('digital_input_poll_ms', 50) / 1000.0
    inp = Pin(pin, Pin.IN, Pin.PULL_UP)
    last = inp.value()
    while True:
        v = inp.value()
        if v != last:
            print('Digital input changed:', v)
            if cfg.get('publish_enabled'):
                await publish_signal_k(cfg, 'sensors.digital_input2.value', v)
            last = v
        await asyncio.sleep(poll)


async def main():
    cfg = load_config()
    print('Loaded config:', cfg)
    connect_wifi(cfg.get('wifi_ssid'), cfg.get('wifi_password'))

    # Start tasks
    tasks = []
    # Websocket manager (optional)
    if cfg.get('use_ws'):
        tasks.append(ws_manager(cfg))
    tasks.extend([analog_loop(cfg), digital_toggle_loop(cfg), digital_input_monitor(cfg)])
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        try:
            asyncio.new_event_loop()
        except Exception:
            pass
