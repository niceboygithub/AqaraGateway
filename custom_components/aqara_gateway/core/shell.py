""" Telnet Shell """
# pylint: disable=line-too-long
import time
import base64

from typing import Union
from telnetlib import Telnet

from .const import (
    SIGMASTAR_MODELS,
    MD5_MOSQUITTO_NEW_ARMV7L,
    MD5_MOSQUITTO_G2HPRO_ARMV7L,
    MD5_MOSQUITTO_MIPSEL
)

WGET = "(wget http://master.dl.sourceforge.net/project/aqarahub/{0}?viasf=1 " \
            "-O /data/bin/{1} && chmod +x /data/bin/{1})"

CHECK_SOCAT = "(md5sum /data/socat | grep 92b77e1a93c4f4377b4b751a5390d979)"
DOWNLOAD_SOCAT = "(wget -O /data/socat http://pkg.simple-ha.ru/mipsel/socat && chmod +x /data/socat)"
RUN_SOCAT_BT_IRDA = "/data/socat tcp-l:8888,reuseaddr,fork /dev/ttyS2"
RUN_SOCAT_ZIGBEE = "/data/socat tcp-l:8888,reuseaddr,fork /dev/ttyS1"


class TelnetShell(Telnet):
    """ Telnet Shell """
    _aqara_property = False
    _suffix = "# "
    # pylint: disable=unsubscriptable-object

    def __init__(self, host: str, password=""):
        """ init function """
        super().__init__(host, timeout=5)
        self._host = host
        self._password = password

    def login(self):
        """ login function """
        self.write(b"\n")
        self.read_until(b"login: ", timeout=10)

        self.run_command("admin")
        if self._password:
            self.read_until(b"Password: ", timeout=1)
            self.write(self._password.encode() + b"\n")
        self.run_command("stty -echo")
        self.write(b"\n")
        self.read_until(b" # ", timeout=2)

#        self.run_command("export PS1='# '")

    def run_command(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        # pylint: disable=broad-except
        try:
            self.write(command.encode() + b"\n")
            suffix = "\r\n{}".format(self._suffix)
            raw = self.read_until(suffix.encode(), timeout=15)
        except Exception:
            raw = b''
        return raw if as_bytes else raw.decode()

    def check_bin(self, filename: str, md5: str, url=None) -> bool:
        """Check binary md5 and download it if needed."""
        # used * for development purposes
        if url:
            self.run_command(WGET.format(url, filename))
            return self.check_bin(filename, md5)
        elif md5 in self.run_command("md5sum /data/bin/{}".format(filename)):
            return True
        else:
            return False

    def run_basis_cli(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        command = "basis_cli " + command
        self.write(command.encode() + b"\n")
        self.read_until(self._suffix.encode())
        self.read_until(self._suffix.encode())

    def file_exist(self, filename: str) -> bool:
        """ check file exit """
        raw = self.run_command("ls -al {}".format(filename))
        if "No such" not in str(raw):
            return True
        return False

    def run_public_mosquitto(self, model):
        """ run mosquitto as public """
        if not self.file_exist("/data/bin/mosquitto"):
            command = "mkdir -p /data/bin"
            self.write(command.encode() + b"\n")
            if model in ('lumi.camera.agl001'):
                self.check_bin('mosquitto', MD5_MOSQUITTO_G2HPRO_ARMV7L , 'bin/armv7l/mosquitto_g2hpro')
            elif model in SIGMASTAR_MODELS:
                self.check_bin('mosquitto', MD5_MOSQUITTO_NEW_ARMV7L , 'bin/armv7l/mosquitto_new')
            else:
                self.check_bin('mosquitto', MD5_MOSQUITTO_MIPSEL, 'bin/mipsel/mosquitto')
        self.run_command("killall mosquitto")
        self.run_command("sleep .1")
        self.run_command("/data/bin/mosquitto -d")

    def check_public_mosquitto(self) -> bool:
        """ get processes list """
        raw = self.run_command("mosquitto")
        if 'Binding listener to interface ""' in raw:
            return True
        if 'Binding listener to interface ' not in raw:
            return True
        return False

    def get_running_ps(self, ps=None) -> str:
        """ get processes list """
        if isinstance(ps, str):
            return self.run_command(f"ps | grep {ps}")
        return self.run_command("ps")

    def read_file(self, filename: str, as_base64=False, with_newline=True):
        """ read file content """
        # pylint: disable=broad-except
        try:
            if as_base64:
                command = "cat {} | base64\n".format(filename)
                self.write(command.encode())
                raw = self.read_until(self._suffix.encode()).decode()
                if not with_newline:
                    raw = self.read_until(self._suffix.encode()).decode()
                return base64.b64decode(raw)
            command = "cat {}\n".format(filename)
            self.write(command.encode())
            ret = self.read_until(self._suffix.encode()).decode()
            if not with_newline:
                ret = self.read_until(self._suffix.encode()).decode()
            if ret.endswith(self._suffix):
                ret = "".join(ret.rsplit(self._suffix, 1))
            return ret.strip("\n")
        except Exception:
            return ''

    def get_prop(self, property_value: str):
        """ get property """
        # pylint: disable=broad-except
        try:
            if self._aqara_property:
                command = "agetprop {}\n\r".format(property_value)
            else:
                command = "getprop {}\n\r".format(property_value)
            ret = self.run_command(command)
            if ret.endswith(self._suffix):
                ret = "".join(ret.rsplit(self._suffix, 1))
            if ret.startswith(self._suffix):
                ret = ret.replace(self._suffix, "", 2)
            return ret.replace("\r", "").replace("\n", "")
        except Exception:
            return ''

    def set_prop(self, property_value: str, value: str):
        """ set property """
        if self._aqara_property:
            command = "asetprop {} {}\n".format(property_value, value)
        else:
            command = "setprop {} {}\n".format(property_value, value)
        self.write(command.encode() + b"\n")
        self.read_until(self._suffix.encode())
        self.read_until(self._suffix.encode())

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

    def get_token(self):
        """ get gateway token """
        filename = "/data/miio/device.token"
        if self.file_exist(filename):
            return self.read_file(filename).rstrip().encode().hex()
        return None

    def get_model(self):
        try:
            self.write(b"\n")
            suffix = ":"
            raw = self.read_until(suffix.encode(), timeout=15)
            _LOGGER.error(f"return {raw.decode()}")
        except Exception:
            raw = b''
        model = raw.decode()
        models = {
            "G2HPro": "g2h pro",
            "G3": "g3",
            "G2H": "g2h",
            "M2": "m2 2022",
            "M3": "m3",
            "M1S": "m1s gen2",
            "V1": "v1",
            "M200": "m200"
            "M100": "m100"
        }
        if len(model) >= 1:
            for key, value in models.items():
                if key in model:
                    return value
        return "m2 2022"

class TelnetShellG2H(TelnetShell):

    def login(self):
        """ login function """
        self._aqara_property = True

        self.write(b"\n")
        self.read_until(b"login: ", timeout=10)

        password = self._password
        if ((self._password is None) or
            (isinstance(self._password, str) and len(self._password) <= 1)
        ):
            password = '\n'

        self.write(b"root\n\r")
        if password:
            self.read_until(b"Password: ", timeout=3)
            #self.write(password.encode() + b"\n")
            self.run_command(password)

        self.run_command("stty -echo")
        self.read_until(self._suffix.encode(), timeout=10)
        self._suffix = "# "


class TelnetShellE1(TelnetShell):

    def login(self):
        """ login function """
        self._aqara_property = True

        self.write(b"\n")
        self.read_until(b"login: ", timeout=10)
        self.write(b"root\n\r")

        self.read_until(b"Password: ", timeout=10)
        self.write(b"\n\r")

        self.read_until(b"/ # ", timeout=10)
        self._suffix = "/ # "

        self.run_command("stty -echo")
        self.read_until(self._suffix.encode(), timeout=10)


class TelnetShellG3(TelnetShell):
    _suffix = "~ # "

    def login(self):
        """ login function """
        self._aqara_property = True

        self.write(b"\n")
        self.read_until(b"login: ", timeout=3)

        self.write(b"root\n\r")
        if self._password:
            self.read_until(b"Password: ", timeout=3)
            self.write(self._password.encode() + b"\n")

        self.run_command("cd /")
        self._suffix = "/ # "

        self.run_command("stty -echo")
        self.read_until(self._suffix.encode(), timeout=10)


class TelnetShellM2POE(TelnetShell):
    _suffix = "/ # "

    def login(self):
        """ login function """
        self._aqara_property = True

        self.write(b"\n")
        self.read_until(b"login: ", timeout=10)

        self.write(b"root\n\r")
        if self._password:
            self.read_until(b"Password: ", timeout=3)
            self.write(self._password.encode() + b"\n")

        self.read_until(b"/ # ", timeout=10)
        self.run_command("stty -echo")
        self.read_until(self._suffix.encode(), timeout=10)

