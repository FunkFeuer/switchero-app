#!/usr/bin/python -u
OUTLET_MAPPING = {
  "krypta2:r1:1:1": { "ssh_connection": ("192.168.0.1", "ubnt", "ubnt"), "outlet": 1 },
  "krypta2:r1:1:2": { "ssh_connection": ("192.168.0.1", "ubnt", "ubnt"), "outlet": 2 },
  "krypta2:r1:1:3": { "ssh_connection": ("192.168.0.1", "ubnt", "ubnt"), "outlet": 3 },
  "krypta2:r1:1:4": { "ssh_connection": ("192.168.0.1", "ubnt", "ubnt"), "outlet": 4 },
  "krypta2:r1:1:5": { "ssh_connection": ("192.168.0.1", "ubnt", "ubnt"), "outlet": 5 },
  "krypta2:r1:1:6": { "ssh_connection": ("192.168.0.1", "ubnt", "ubnt"), "outlet": 6 }
}


from concurrent import futures
import time
import grpc
import switchero_pb2
import switchero_pb2_grpc
import paramiko


class Switchero(switchero_pb2_grpc.SwitcheroServicer):
  ssh_connections = {}

  def SSHCommand(self, cfg, cmd):
    ssh = self.ssh_connections.get(cfg)
    if ssh is None or ssh.get_transport() is None or ssh.get_transport().is_active() is False:
      ssh = paramiko.SSHClient()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect(cfg[0], username = cfg[1], password = cfg[2])
      ssh.get_transport().set_keepalive(60)
      self.ssh_connections[cfg] = ssh
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read()


  def PowerOn(self, request, context):
    print "Power ON: %s" % request.locator

    cfg = OUTLET_MAPPING.get(request.locator)
    if cfg is None:
      return switchero_pb2.Void(error = "NOT_FOUND")

    self.SSHCommand(cfg["ssh_connection"], "echo 1 > /proc/power/relay{0}".format(cfg["outlet"]))
    return switchero_pb2.Void()


  def PowerOff(self, request, context):
    print "Power OFF: %s" % request.locator

    cfg = OUTLET_MAPPING.get(request.locator)
    if cfg is None:
      return switchero_pb2.Void(error = "NOT_FOUND")

    self.SSHCommand(cfg["ssh_connection"], "echo 0 > /proc/power/relay{0}".format(cfg["outlet"]))
    return switchero_pb2.Void()


  def PowerStatus(self, request, context):
    print "Power STATUS: %s" % request.locator

    cfg = OUTLET_MAPPING.get(request.locator)
    if cfg is None:
      return switchero_pb2.PowerStatusResponse(error = "NOT_FOUND")

    result = self.SSHCommand(cfg["ssh_connection"], "cat /proc/power/relay{0} /proc/power/v_rms{0} /proc/power/i_rms{0} /proc/power/active_pwr{0} /proc/power/pf{0}".format(cfg["outlet"])).splitlines()
    return switchero_pb2.PowerStatusResponse(
      cap_measure = True,
      cap_fault = False,
      state = "ON" if result[0] == "1" else "OFF",
      volts = float(result[1]),
      amps = float(result[2]),
      watts = float(result[3]),
      pf = float(result[4])
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
