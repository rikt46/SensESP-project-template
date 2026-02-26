MicroPython Prototype for SensESP Project Template

This folder contains a minimal MicroPython prototype that reproduces the
behaviour of `src/main.cpp` from the C++ SensESP template: an analog read,
a digital input monitor, and a toggled digital output. It also includes a
very small Signal K delta POST implementation (may require adaptation).

Files

- main.py — MicroPython application to copy to the ESP32 filesystem.
- config.json.example — example configuration you should copy to `config.json`.

Quick start

1. Flash MicroPython firmware to your ESP32 if you haven't already. Get
   the latest firmware for your board from <https://micropython.org/download/esp32/>.

   Example (using esptool.py):

   ```bash
   python -m esptool erase_flash
   python -m esptool --chip esp32 write_flash -z 0x1000 esp32-*.bin
   ```

2. Copy files to the device using `mpremote`, `ampy`, or `rshell`.
   Example with `mpremote`:

   ```bash
   pip install mpremote
   mpremote connect auto fs cp micropython/main.py :/main.py
   mpremote connect auto fs cp micropython/config.json.example :/config.json
   ```

3. Edit `/config.json` on the device to set `wifi_ssid`, `wifi_password`, and
   `sk_server`. By default `publish_enabled` is false — set it to `true` to
   attempt HTTP publish of Signal K deltas.

4. Reboot the board or run `main.py` from the REPL.

Notes

- MicroPython builds vary; some firmwares do not include `urequests` or `ssl`.
  You may need to add or adapt libraries.
- Signal K servers typically expect deltas over WebSocket; this prototype
  posts a minimal delta JSON via HTTP which may need server-side support.
- For reliable TLS and WebSocket support, consider using a Raspberry Pi
  with CPython if you require full SensESP parity.

- WebSocket note: To enable Signal K websocket publishing set `use_ws` to
   `true` in `config.json`. MicroPython firmware must include a websocket
   client (for example `uwebsockets`) and proper TLS support for `wss://`.

Testing the project (on your development machine)
1. Install pytest:

```bash
pip install pytest
```

2. Run tests from the repository root. The tests mock MicroPython modules so
   they run on CPython.

```bash
pytest -q
```

Continuous Integration
- A GitHub Actions workflow is included at `.github/workflows/ci.yml` and
  will run the test suite on push and pull requests.

Notes on editing the code
- The main application is intentionally small and commented to help you port
  or extend it. If you need advanced features from SensESP (dynamic
  configuration UI, plugin system, TLS websockets, OTA), prefer a CPython
  target (Raspberry Pi) or accept that additional work and firmware builds
  will be required for MicroPython.
