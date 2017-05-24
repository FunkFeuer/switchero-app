Contains implementations for the [gRPC protocol](../switchero.proto).

# usb
Implementation supporting the [USB switch board](https://github.com/FunkFeuer/switchero-pcb/) as provided here.

## Installation
1. `pip install adafruit-gpio grpcio grpcio-tools`
2. `python -m grpc_tools.protoc -I../ --python_out=. --grpc_python_out=. switchero.proto`

# mpower
Implementation supporting the [Ubiquity MPower](https://www.ubnt.com/mfi/mpower/) switches.
