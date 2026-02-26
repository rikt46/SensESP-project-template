[![Coverage Status](https://codecov.io/gh/SensESP/SensESP-project-template/branch/main/graph/badge.svg)](https://codecov.io/gh/SensESP/SensESP-project-template)

# SensESP Project Template

This repository provides a template for [SensESP](https://github.com/SignalK/SensESP/) projects.
Fork, clone or download the repository and try building and uploading the project to an ESP32 device.
You should immediately see output on the serial monitor! Similarly, you should be able to connect to
the WiFi access point with the same name as the device. The password is `thisisfine`.

To customize the template for your own purposes, edit the `src/main.cpp` and `platformio.ini` files.

Comprehensive documentation for SensESP, including how to get started with your own project, is available at the [SensESP documentation site](https://signalk.org/SensESP/).

## MicroPython Prototype

This repository now includes a small MicroPython prototype implementing the
core example from `src/main.cpp` in Python. See `micropython/README.md` for
how to flash the prototype to an ESP32, run it interactively, and run the
unit tests locally. The tests are executed by GitHub Actions on push and PRs.
# SensESP Project Template

This repository provides a template for [SensESP](https://github.com/SignalK/SensESP/) projects.
Fork, clone or download the repository and try building and uploading the project to an ESP32 device.
You should immediately see output on the serial monitor! Similarly, you should be able to connect to
the WiFi access point with the same name as the device. The password is `thisisfine`.

To customize the template for your own purposes, edit the `src/main.cpp` and `platformio.ini` files.

Comprehensive documentation for SensESP, including how to get started with your own project, is available at the [SensESP documentation site](https://signalk.org/SensESP/).

MicroPython Prototype

This repository now includes a small MicroPython prototype implementing the
core example from `src/main.cpp` in Python. See `micropython/README.md` for
how to flash the prototype to an ESP32, run it interactively, and run the
unit tests locally. The tests are executed by GitHub Actions on push and PRs.
