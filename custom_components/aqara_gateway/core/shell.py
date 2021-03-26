""" Telnet Shell """
# pylint: disable=line-too-long
import time
import base64

from typing import Union
from telnetlib import Telnet


CHECK_SOCAT = "(md5sum /data/socat | grep 92b77e1a93c4f4377b4b751a5390d979)"
DOWNLOAD_SOCAT = "(wget -O /data/socat http://pkg.simple-ha.ru/mipsel/socat && chmod +x /data/socat)"
RUN_SOCAT_BT_IRDA = "/data/socat tcp-l:8888,reuseaddr,fork /dev/ttyS2"
RUN_SOCAT_ZIGBEE = "/data/socat tcp-l:8888,reuseaddr,fork /dev/ttyS1"

HA_MASTER2MQTT = "(ha_master -H -r /lib/libha_ir_m2.so -a /lib/libha_auto.so -g /lib/libha_energy.so | awk '/%s/{print $0;fflush()}' | mosquitto_pub -t log/ha_master -l &)"
HA_BLE2MQTT = "(ha_ble | awk '{print $0;fflush();}' | mosquitto_pub -t log/ha_ble -l &)"


class TelnetShell(Telnet):
    """ Telnet Shell """
    _aqara_property = False
    # pylint: disable=unsubscriptable-object

    def __init__(self, host: str, password=None, device_name=None):
        super().__init__(host, timeout=5)
        self.read_until(b"login: ", timeout=10)
        login_name = 'root' if (
            device_name and 'g2h' in device_name) else 'admin'
        if password:
            command = '{}\r\n'.format(login_name)
            self.write(command.encode())
            self.read_until(b"Password: ", timeout=10)
            self.run_command(password)
        else:
            self.run_command(login_name)
        if self.file_exist("/tmp/out/agetprop"):
            self._aqara_property = True

    def run_command(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        # pylint: disable=broad-except
        try:
            self.write(command.encode() + b"\r\n")
            raw = self.read_until(b"\r\n# ", timeout=30)
        except Exception:
            raw = b''
        return raw if as_bytes else raw.decode()

    def run_basis_cli(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        command = "basis_cli " + command
        self.run_command(command, as_bytes)
        self.read_until(b"#", timeout=1)
        self.read_until(b"#", timeout=1)

    def file_exist(self, filename: str) -> bool:
        """ check file exit """
        raw = self.run_command("ls -al {}".format(filename))
        time.sleep(.1)
        if "No such" not in raw:
            return True
        return False

    def run_public_mosquitto(self):
        """ run mosquitto as public """
        if self.file_exist("/data/bin/mosquitto"):
            self.run_command("killall mosquitto")
            time.sleep(.5)
            self.run_command("/data/bin/mosquitto -d")
            time.sleep(.5)

    def check_public_mosquitto(self) -> bool:
        """ get processes list """
        raw = self.run_command("mosquitto")
        if "Binding listener to interface" in raw:
            return False
        return True

    def get_running_ps(self) -> str:
        """ get processes list """
        return self.run_command("ps")

    def redirect_ha_master2mqtt(self, pattern: str):
        """ redirect ha_master logs to mqtt """
        self.run_command("killall ha_master")
        time.sleep(.1)
        self.run_command(HA_MASTER2MQTT % pattern)

    def redirect_ha_ble2mqtt(self):
        """ redirect ha_ble logs to mqtt """
        self.run_command("killall ha_ble")
        time.sleep(.1)
        self.run_command(HA_BLE2MQTT)

    def read_file(self, filename: str, as_base64=False):
        """ read file content """
        # pylint: disable=broad-except
        try:
            if as_base64:
                command = "cat {} | base64\n".format(filename)
                self.write(command.encode())
                self.read_until(b"\n")
                raw = self.read_until(b"# ")
                return base64.b64decode(raw)
            command = "cat {}\n".format(filename)
            self.write(command.encode())
            self.read_until(b"\n")
            return self.read_until(b"# ")[:-2]
        except Exception:
            return b''

    def get_prop(self, property_value: str):
        """ get property """
        # pylint: disable=broad-except
        try:
            if self._aqara_property:
                command = "agetprop {}\n".format(property_value)
            else:
                command = "getprop {}\n".format(property_value)
            self.write(command.encode())
            self.read_until(b"\r")
            return str(self.read_until(
                b"# ")[:-2], encoding="utf-8").strip().rstrip()
        except Exception:
            return ''

    def set_prop(self, property_value: str, value: str):
        """ set property """
        if self._aqara_property:
            command = "asetprop {} {}\n".format(property_value, value)
        else:
            command = "setprop {} {}\n".format(property_value, value)
        self.run_command(command)

    def get_version(self):
        """ get gateway version """
        return self.get_prop("ro.sys.fw_ver")

    def set_audio_volume(self, value):
        """ set gateway audio volume """
        if value > 100:
            value = 100
        command = "-sys -v {}".format(value)
        raw = self.run_basis_cli(command)
        return raw[raw.find(">>>") + 4:]
