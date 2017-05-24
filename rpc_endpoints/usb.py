#!/usr/bin/python -u
OUTLET_MAPPING = {
  "krypta2:e1:1:1": { "addr": (1, 0x20), "ctl": 0, "flag": 1 },
  "krypta2:e1:1:2": { "addr": (1, 0x20), "ctl": 2, "flag": 3 },
  "krypta2:e1:1:3": { "addr": (1, 0x20), "ctl": 4, "flag": 5 },
  "krypta2:e1:1:4": { "addr": (1, 0x20), "ctl": 6, "flag": 7 },
  "krypta2:e1:1:5": { "addr": (1, 0x20), "ctl": 8, "flag": 9 },
  "krypta2:e1:1:6": { "addr": (1, 0x20), "ctl": 10, "flag": 11 },
  "krypta2:e1:1:7": { "addr": (1, 0x20), "ctl": 12, "flag": 13 },
  "krypta2:e1:1:8": { "addr": (1, 0x20), "ctl": 14, "flag": 15 }
}


from concurrent import futures
import time
import grpc
import switchero_pb2
import switchero_pb2_grpc
import Adafruit_GPIO as GPIO
import Adafruit_GPIO.MCP230xx as MCP


CHIP_MAPPING = {}
for entry in sorted(OUTLET_MAPPING.items(), key = lambda x: x[1]["ctl"]): # Pins need to be initialised in ascending order. Bug in lib?
  locator = entry[0]
  cfg = entry[1]
  addr = cfg["addr"]
  chip = CHIP_MAPPING.get(addr)
  if chip is None:
    chip = MCP.MCP23017(busnum = addr[0], address = addr[1])
    CHIP_MAPPING[addr] = chip
  chip.setup(cfg["ctl"], GPIO.OUT)
  chip.setup(cfg["flag"], GPIO.IN)
  chip.pullup(cfg["flag"], True)


STATE_MAPPING = { locator: "ON" for locator in OUTLET_MAPPING }


class Switchero(switchero_pb2_grpc.SwitcheroServicer):
  def PowerOn(self, request, context):
    print "Power ON: %s" % request.locator

    cfg = OUTLET_MAPPING.get(request.locator)
    if cfg is None:
      return switchero_pb2.Void(error = "NOT_FOUND")

    chip = CHIP_MAPPING[cfg["addr"]]
    chip.output(cfg["ctl"], GPIO.LOW)
    STATE_MAPPING[request.locator] = "ON"
    return switchero_pb2.Void()


  def PowerOff(self, request, context):
    print "Power OFF: %s" % request.locator

    cfg = OUTLET_MAPPING.get(request.locator)
    if cfg is None:
      return switchero_pb2.Void(error = "NOT_FOUND")

    chip = CHIP_MAPPING[cfg["addr"]]
    chip.output(cfg["ctl"], GPIO.HIGH)
    STATE_MAPPING[request.locator] = "OFF"
    return switchero_pb2.Void()


  def PowerStatus(self, request, context):
    print "Power STATUS: %s" % request.locator

    cfg = OUTLET_MAPPING.get(request.locator)
    if cfg is None:
      return switchero_pb2.PowerStatusResponse(error = "NOT_FOUND")

    chip = CHIP_MAPPING[cfg["addr"]]

    state = STATE_MAPPING[request.locator]
    fault = chip.input(cfg["flag"]) == GPIO.LOW

    return switchero_pb2.PowerStatusResponse(
      cap_measure = False,
      cap_fault = True,
      state = state,
      fault = fault
    )


server = grpc.server(futures.ThreadPoolExecutor(max_workers = 10))
switchero_pb2_grpc.add_SwitcheroServicer_to_server(Switchero(), server)
server.add_insecure_port("[::]:50051")
server.start()
try:
  while True:
    time.sleep(1)
except KeyboardInterrupt:
  server.stop(0)
