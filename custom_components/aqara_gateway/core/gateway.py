""" Aqara Gateway """
# pylint: disable=broad-except
import logging
import socket
import time
import json
import re
from threading import Thread
from typing import Optional
from random import randint
from paho.mqtt.client import Client, MQTTMessage

from homeassistant.core import Event
from homeassistant.const import CONF_NAME, CONF_PASSWORD
from homeassistant.components.light import ATTR_HS_COLOR


from .shell import TelnetShell
from .utils import DEVICES, Utils, GLOBAL_PROP
from .const import CONF_MODEL, DOMAIN

_LOGGER = logging.getLogger(__name__)

MD5_MOSQUITTO_ARMV7L = '0422c48517dc464a2e986a1038dc448a'
MD5_MOSQUITTO_MIPSEL = 'e0ce4757cfcccb079d89134381fd11b0'

class Gateway(Thread):
    # pylint: disable=too-many-instance-attributes, unused-argument
    """ Aqara Gateway """

    def __init__(self, hass, host: str, config: dict, **options):
        """Initialize the Xiaomi/Aqara device."""
        super().__init__(daemon=True)
        self.hass = hass
        self.host = host
        self.options = options
        # if mqtt server connected
        self.enabled = False
        self.available = False

        self._mqttc = Client()
        self._mqttc.on_connect = self.on_connect
        self._mqttc.on_disconnect = self.on_disconnect
        self._mqttc.on_message = self.on_message

        self._debug = options.get('debug', '')  # for fast access
        self.parent_scan_interval = (-1 if options.get('parent') is None
                                     else options['parent'])
        self.default_devices = config['devices'] if config else None

        self.devices = {}
        self.updates = {}
        self.setups = {}
        self._device_state_attributes = {}
        self._info_ts = None
        self._gateway_did = ''
        self._model = self.options.get(CONF_MODEL, '')  # for fast access
        self.cloud = 'aiot'  # for fast access

    @property
    def device(self):
        """ get device """
        return self.devices[list(self.devices)[0]]
#        return self.devices['lumi.0']

    def add_update(self, did: str, handler):
        """Add handler to device update event."""
        self.updates.setdefault(did, []).append(handler)

    def remove_update(self, did: str, handler):
        """remove update"""
        self.updates.setdefault(did, []).remove(handler)

    def add_setup(self, domain: str, handler):
        """Add hass device setup funcion."""
        self.setups[domain] = handler

    def debug(self, message: str):
        """ deubug function """
        if 'true' in self._debug:
            _LOGGER.debug(f"{self.host}: {message}")

    def stop(self):
        """ stop function """
        self.enabled = False

    async def async_connect(self) -> str:
        """Connect to the host. Does not process messages yet."""
        result: int = None
        try:
            result = await self.hass.async_add_executor_job(
                self._mqttc.connect,
                self.host
            )
        except OSError as err:
            _LOGGER.error(
                f"Failed to connect to MQTT server {self.host} due to exception: {err}")

        if result is not None and result != 0:
            _LOGGER.error(
                f"Failed to connect to MQTT server: {self.host}"
            )

        self._mqttc.loop_start()
        self.enabled = True

    async def async_disconnect(self):
        """Stop the MQTT client."""
        self.available = False

        def stop():
            """Stop the MQTT client."""
            # Do not disconnect, we want the broker to always publish will
            self._mqttc.loop_stop()

        await self.hass.async_add_executor_job(stop)

    def run(self):
        """ Main thread loop. """
        telnetshell = False
        if "telnet" not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["telnet"] = []
        if "mqtt" not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["mqtt"] = []
        while not self.enabled and not self.available:
            if not self._check_port(23):
                if self.host in self.hass.data[DOMAIN]["telnet"]:
                    self.hass.data[DOMAIN]["telnet"].remove(self.host)
                time.sleep(30)
                continue

            telnetshell = True
            devices = self._prepare_gateway(get_devices=True)
            if isinstance(devices, list):
                self._gw_topic = "gw/{}/".format(devices[0]['mac'][2:].upper())
                self.setup_devices(devices)
                break

        if telnetshell:
            if self.host not in self.hass.data[DOMAIN]["telnet"]:
                self.hass.data[DOMAIN]["telnet"].append(self.host)

        while not self.available:
            if not self._mqtt_connect() or not self._prepare_gateway():
                if self.host in self.hass.data[DOMAIN]["mqtt"]:
                    self.hass.data[DOMAIN]["mqtt"].remove(self.host)
                time.sleep(60)
                continue

            self._mqttc.loop_start()
            self.available = True
#            self._mqttc.loop_forever()

        if self.available:
            if self.host not in self.hass.data[DOMAIN]["mqtt"]:
                self.hass.data[DOMAIN]["mqtt"].append(self.host)

    def _mqtt_connect(self) -> bool:
        try:
            self._mqttc.reconnect()
            return True
        except Exception:
            return False

    def _check_port(self, port: int):
        """Check if gateway port open."""
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            return skt.connect_ex((self.host, port)) == 0
        finally:
            skt.close()

    def _prepare_gateway(self, get_devices: bool = False):
        """Launching the required utilities on the hub, if they are not already
        running.
        """
        try:
            shell = TelnetShell(self.host,
                                self.options.get(CONF_PASSWORD, ''),
                                Utils.get_device_name(self._model))

            processes = shell.get_running_ps()
            public_mosquitto = shell.check_public_mosquitto()
            if not public_mosquitto:
                self.debug("mosquitto is not running as public!")

            if "/data/bin/mosquitto -d" not in processes:
                if "mosquitto" not in processes or not public_mosquitto:
                    shell.run_public_mosquitto()

            if get_devices:
                devices = self._get_devices(shell)
                shell.close()
                return devices
            return True

        except (ConnectionRefusedError, socket.timeout):
            return False

        except Exception as expt:
            self.debug("Can't read devices: {}".format(expt))
            return False

    def _get_devices(self, shell: TelnetShell):
        """Load devices info for Coordinator, Zigbee and Mesh."""
        devices = {}

        try:
            # 1. Read coordinator info
            value = {}

            zb_coordinator = shell.get_prop("sys.zb_coordinator")
            model = shell.get_prop("persist.sys.model")
            if len(zb_coordinator) >= 1:
                raw = shell.read_file(zb_coordinator, with_newline=False)
                did = shell.get_prop("persist.sys.did")
                model = shell.get_prop("ro.sys.model")
            elif 'lumi.gateway' in model or 'lumi.aircondition' in model:
                raw = shell.read_file('/data/zigbee/coordinator.info', with_newline=False)
                did = shell.get_prop("persist.sys.did")
                model = shell.get_prop("ro.sys.model")
            else:
                raw = str(shell.read_file('/mnt/config/miio/device.conf'))
                data = re.search(r"did=([0-9]+).+", raw)
                did = data.group(1) if data else ''
                data = re.search(r"model=([a-zA-Z0-9.-]+).+", raw)
                model = data.group(1) if data else ''
                raw = shell.read_file('/mnt/config/zigbee/coordinator.info', with_newline=False)
            value = json.loads(raw)
            devices = [{
                'coordinator': 'lumi.0',
                'did': did,
                'model': model,
                'mac': value['mac'],
                'manufacturer': value['manufacturer'],
                'channel': value['channel'],
                'cloudLink': value['cloudLink'],
                'debugStatus': value['debugStatus'],
                'type': 'gateway',
            }]
            self._model = model

            # zigbee devices
            zb_device = shell.get_prop("sys.zb_device")
            if len(zb_device) >= 1:
                raw = shell.read_file(zb_device, with_newline=False)
            else:
                raw = shell.read_file('{}/zigbee/device.info'.format(
                    Utils.get_info_store_path(self._model)), with_newline=False)

            value = json.loads(raw)
            dev_info = value.get("devInfo", 'null') or []
            self.cloud = shell.get_prop("persist.sys.cloud")

            for dev in dev_info:
                model = dev['model']
                desc = Utils.get_device(model, self.cloud)
                # skip unknown model
                if desc is None:
                    self.debug("{} has an unsupported model: {}".format(
                        dev['did'], model
                    ))
                    continue
                device = {
                    'coordinator': 'lumi.0',
                    'did': dev['did'],
                    'mac': dev['mac'],
                    'model': dev['model'],
                    'type': 'zigbee',
                    'zb_ver': dev.get('zb_ver', "1.2"),
                    'model_ver': dev['model_ver'],
                    'status': dev['status']
                }
                devices.append(device)
        except Exception as expt:
            self.debug("Can't get devices: {}".format(expt))

        return devices

    def setup_devices(self, devices: list):
        """Add devices to hass."""
        for device in devices:
            timeout = 300
            if device['type'] in ('gateway', 'zigbee'):
                desc = Utils.get_device(device['model'], self.cloud)
                if not desc:
                    self.debug("Unsupported model: {}".format(device))
                    continue

                device.update(desc)

                # update params from config
                default_config = (
                        self.default_devices.get(device['mac']) or
                        self.default_devices.get(device['did'])
                )

                if default_config:
                    device.update(default_config)

                self.devices[device['did']] = device

                for param in (device['params'] or device['mi_spec']):
                    domain = param[3]
                    if not domain:
                        continue

                    # wait domain init
                    while domain not in self.setups and timeout > 0:
                        time.sleep(1)
                        timeout = timeout - 1
                    attr = param[2]
                    if (attr in ('illuminance', 'light') and
                            device['type'] == 'gateway'):
                        self._gateway_did = device['did']

                    self.setups[domain](self, device, attr)

            if self.options.get('stats'):
                while 'sensor' not in self.setups:
                    time.sleep(1)
                self.setups['sensor'](self, device, device['type'])

    def add_stats(self, ieee: str, handler):
        """ add gateway stats """
        self._device_state_attributes[ieee] = handler

        if self.parent_scan_interval > 0:
            self._info_ts = time.time() + 5

    def remove_stats(self, ieee: str, handler):
        """ remove gateway stats """
        self._device_state_attributes.pop(ieee)

    def process_gateway_stats(self, payload: dict = None):
        """ process gateway status """
        # empty payload - update available state
        self.debug(f"gateway <= {payload or self.available}")

        if 'lumi.0' not in self._device_state_attributes:
            return

        if payload:
            data = {}
            for param in payload:
                if 'networkUp' in param:
                    # {"networkUp":false}
                    data = {
                        'network_pan_id': param['value'].get('networkPanId'),
                        'radio_tx_power': param['value'].get('radioTxPower'),
                        'radio_channel': param['value'].get('radioChannel'),
                    }
                elif 'free_mem' in param:
                    seconds = param['value']['run_time']
                    hours, mintues, seconds = seconds // 3600, seconds % 3600 // 60, seconds % 60
                    data = {
                        'free_mem': param['value']['free_mem'],
                        'load_avg': param['value']['load_avg'],
                        'rssi': -param['value']['rssi'],
                        'uptime': "{:02}:{:02}:{:02}".format(
                            hours, mintues, seconds),
                    }

                prop = None
                if 'res_name' in param:
                    if param['res_name'] in GLOBAL_PROP:
                        prop = GLOBAL_PROP[param['res_name']]
                        print(prop)
                if prop == 'report':
                    report_list = param['value'].split(',')
                    stat = {}
                    for item in report_list:
                        stat = iter(item.split(
                            ':', 1) if 'time' in item else item.lstrip(
                                ).strip().split(' '))
                        data.update(dict(zip(stat, stat)))
            shell = TelnetShell(self.host,
                                self.options.get(CONF_PASSWORD, ''),
                                Utils.get_device_name(self._model))
            raw = shell.read_file('{}/zigbee/networkBak.info'.format(
                    Utils.get_info_store_path(self._model)), with_newline=False)
            shell.close()
            if len(raw) >= 1:
                value = json.loads(raw)
                data.update(value)

        self._device_state_attributes['lumi.0'](data)

    def on_connect(self, client, userdata, flags, ret):
        # pylint: disable=unused-argument
        """ on connect to mqtt server """
        self._mqttc.subscribe("#")
        self.available = True
        if self.host not in self.hass.data[DOMAIN]["mqtt"]:
            self.hass.data[DOMAIN]["mqtt"].append(self.host)
#        self.process_gateway_stats()

    def on_disconnect(self, client, userdata, ret):
        # pylint: disable=unused-argument
        """ on disconnect to mqtt server """
        self._mqttc.disconnect()
        if self.host in self.hass.data[DOMAIN]["mqtt"]:
            self.hass.data[DOMAIN]["mqtt"].remove(self.host)
        self.available = False
#        self.process_gateway_stats()
        self.run()

    def on_message(self, client: Client, userdata, msg: MQTTMessage):
        # pylint: disable=unused-argument
        """ on getting messages from mqtt server """

        if 'mqtt' in self._debug:
            try:
                self.debug("MQTT on_message: {} {}".format(
                    msg.topic, msg.payload.decode()))
            except UnicodeDecodeError:
                self.debug("MQTT on_message: {}".format(msg.topic))
                self.debug(msg.payload)

        try:
            json.loads(msg.payload)
        except ValueError:
            self.debug("Decoding JSON failed")
            return

        if msg.topic == 'zigbee/send':
            payload = json.loads(msg.payload)
            self._process_message(payload)
        elif msg.topic == 'ioctl/send':
            payload = json.loads(msg.payload)
            self._process_message(payload)
        elif msg.topic == 'debug/host':
            payload = json.loads(msg.payload)
            self._process_message(payload)

    def _process_devices_info(self, prop, value):
        if prop == 'removed_did' and value:
            Utils.remove_device(self.hass, value)
            if isinstance(value, dict) and value['did'] in self.devices:
                self.devices.pop(value['did'], None)
            if isinstance(value, str) and value in self.devices:
                self.devices.pop(value, None)
            return

        if prop == 'paring' and value == 0:
            shell = TelnetShell(self.host,
                                self.options.get(CONF_PASSWORD, ''),
                                Utils.get_device_name(self._model))
            zb_device = shell.get_prop("sys.zb_device")
            if len(zb_device) >= 1:
                raw = shell.read_file(zb_device, with_newline=False)
            else:
                raw = shell.read_file('{}/zigbee/device.info'.format(
                    Utils.get_info_store_path(self._model)), with_newline=False)

            shell.close()
            value = json.loads(raw)
            dev_info = value.get("devInfo", 'null') or []
            for dev in dev_info:
                model = dev['model']
                desc = Utils.get_device(model, self.cloud)
                # skip unknown model
                if desc is None:
                    self.debug("{} has an unsupported modell: {}".format(
                        dev['did'], model
                    ))
                    continue

                if prop == 'paring':
                    if dev['did'] not in self.devices:
                        device = {
                            'coordinator': 'lumi.0',
                            'did': dev['did'],
                            'mac': dev['mac'],
                            'model': dev['model'],
                            'type': 'zigbee',
                            'zb_ver': dev.get('zb_ver', "1.2"),
                            'model_ver': dev['model_ver'],
                            'status': dev['status']
                        }
                        self.setup_devices([device])
                        break

    def _process_message(self, data: dict):
        # pylint: disable=too-many-branches, too-many-statements
        # pylint: disable=too-many-return-statements

        if data['cmd'] == 'heartbeat':
            # don't know if only one item
            if len(data['params']) < 1:
                return
            data = data['params'][0]
            pkey = 'res_list'
        elif data['cmd'] == 'report':
            pkey = 'params' if 'params' in data else 'mi_spec'
        elif data['cmd'] in ('write_rsp', 'read_rsp'):
            pkey = 'results' if 'results' in data else 'mi_spec'
        elif data['cmd'] == 'write_ack':
            return
        elif data['cmd'] == 'behaved':
            return
        else:
            _LOGGER.warning("Unsupported cmd: %s", data)
            return

        did = data['did']

        if did == 'lumi.0':
            device = self.devices.get(self._gateway_did, None)
            if pkey in ('results', 'params'):
                for param in data[pkey]:
                    if param.get('error_code', 0) != 0:
                        continue
                    prop = param.get('res_name', None)
                    if prop in GLOBAL_PROP:
                        prop = GLOBAL_PROP[prop]
                    elif device:
                        prop = next((
                            p[2] for p in (device['params'])
                            if p[0] == prop
                        ), prop)
                    if prop in ('removed_did', 'paring'):
                        self._process_devices_info(
                            prop, param.get('value', None))
#                        self._handle_device_remove({})
                        return
                    payload = {}
                    if (prop in ('illuminance', 'light', 'added_device')
                            and self._gateway_did in self.updates):
                        payload[prop] = param.get('value')
                        for handler in self.updates[self._gateway_did]:
                            handler(payload)
                        return

            self.process_gateway_stats(data[pkey])

            return

        # skip without updates callback
        if did not in self.updates:
            return

        device = self.devices.get(did, None)
        if device is None:
            return
        time_stamp = time.time()

        payload = {}

        # convert codes to names
        for param in data[pkey]:
            if param.get('error_code', 0) != 0:
                continue

            if 'res_name' in param:
                prop = param['res_name']
            elif 'piid' in param:
                prop = f"{param['siid']}.{param['piid']}"
            elif 'eiid' in param:
                prop = f"{param['siid']}.{param['eiid']}"
            else:
                _LOGGER.warning("Unsupported param: %s", data)
                return

            if prop in GLOBAL_PROP:
                prop = GLOBAL_PROP[prop]
            else:
                prop = next((
                    p[2] for p in (device['params'] or device['mi_spec'])
                    if p[0] == prop
                ), prop)

            # https://github.com/Koenkk/zigbee2mqtt/issues/798
            # https://www.maero.dk/aqara-temperature-humidity-pressure-sensor-teardown/
            if (prop == 'temperature'):
                if -4000 < param['value'] < 12500:
                    payload[prop] = param['value'] / 100.0
            elif (prop == 'humidity'):
                if 0 <= param['value'] <= 10000:
                    payload[prop] = param['value'] / 100.0
            elif prop == 'pressure':
                payload[prop] = param['value'] / 100.0
            elif prop in ('battery', 'voltage'):
                # sometimes voltage and battery came in one payload
                if prop == 'voltage' and 'battery' in payload:
                    continue
                # not using coin cell battery
                if 'aqara.lock' in device['model']:
                    payload[prop] = param['value']
                else:
                    payload[prop] = (
                        param['value'] if param['value'] < 1000
                        else round((min(param['value'], 3200) - 2500) / 7)
                    )
            elif prop == 'alive' and param['value']['status'] == 'offline':
                if not self.options.get('noffline', False):
                    device['online'] = False
            elif prop == 'angle':
                # xiaomi cube 100 points = 360 degrees
                payload[prop] = param['value'] * 4
            elif prop == 'duration':
                # xiaomi cube
                payload[prop] = param['value'] / 1000.0
            elif prop in ('power'):
                payload[prop] = round(param['value'], 2)
            elif prop in ('consumption'):
                payload[prop] = round(param['value'], 2) / 1000.0
            elif 'value' in param:
                payload[prop] = param['value']
            elif 'arguments' in param:
                if prop == 'motion':
                    payload[prop] = 1
                else:
                    payload[prop] = param['arguments']

        self.debug("{} {} <= {} [{}]".format(
            device['did'], device['model'], payload, time_stamp
        ))

        for handler in self.updates[did]:
            handler(payload)

        if 'added_device' in payload:
            # {'did': 'lumi.fff', 'mac': 'fff', 'model': 'lumi.sen_ill.mgl01',
            # 'version': '21', 'zb_ver': '3.0'}
            device = payload['added_device']
            device['mac'] = '0x' + device['mac']
            device['type'] = 'zigbee'
            device['init'] = payload
            self.setup_devices([device])

    async def _handle_device_remove(self, payload: dict):
        """Remove device from Hass. """

        async def device_registry_updated(event: Event):
            if event.data['action'] != 'update':
                return

#            registry = self.hass.data['device_registry']
#            hass_device = registry.async_get(event.data['device_id'])
            # check empty identifiers
#            if not hass_device or not hass_device.identifiers:
#                return

#            domain, mac = next(iter(hass_device.identifiers))

            # remove from Hass
#            registry.async_remove_device(hass_device.id)

        self.hass.bus.async_listen(
            'device_registry_updated', device_registry_updated)

    def send(self, device: dict, data: dict):
        """ send command """
        try:
            payload = {}
            if device['type'] == 'zigbee' or 'paring' in data:
                did = data.get('did', device['did'])
                data.pop('did', '')
                params = []

                # convert hass prop to lumi prop
                if device['mi_spec']:
                    payload = {'cmd': 'write', 'did': did, 'id': 5}
                    for key, val in data.items():
                        if key == 'switch':
                            val = bool(val)
                        key = next(
                            p[0] for p in device['mi_spec'] if p[2] == key)
                        params.append({
                            'siid': int(key[0]), 'piid': int(key[2]), 'value': val
                        })

                    payload['mi_spec'] = params
                else:
                    params = [{
                        'res_name': next(
                            p[0] for p in device['params'] if p[2] == key),
                        'value': val
                    } for key, val in data.items()]

                    payload = {
                        'cmd': 'write',
                        'did': did,
                        'id': randint(0, 65535),
                        'params': params,
                    }

                payload = json.dumps(payload, separators=(',', ':')).encode()
                self._mqttc.publish('zigbee/recv', payload)
            elif device['type'] == 'gateway':
                if ATTR_HS_COLOR in data:
                    hs_color = data.get(ATTR_HS_COLOR, 0)
                    brightness = (hs_color >> 24) & 0xFF
                    payload = {
                        'cmd': 'control',
                        'data': {
                            'blue': int((hs_color & 0xFF) * brightness / 100),
                            'breath': 500,
                            'green': int(
                                ((hs_color >> 8) & 0xFF) * brightness / 100),
                            'red': int(
                                ((hs_color >> 16) & 0xFF) * brightness / 100)},
                        'type': 'rgb',
                        'rev': 1,
                        'id': randint(0, 65535)
                    }
                else:
                    payload = {
                        'cmd': 'control',
                        'data': data,
                        'rev': 1,
                        'id': randint(0, 65535)
                    }
                payload = json.dumps(payload, separators=(',', ':')).encode()
                self._mqttc.publish('ioctl/recv', payload)
            return True
        except ConnectionError:
            return False


def prepare_aqaragateway(shell, model):
    """ Prepare supported Aqara Gateway """
    command = "mkdir -p /data/scripts"
    shell.write(command.encode() + b"\n")
    time.sleep(1)
    if model in ('lumi.gateway.aqcn02', 'lumi.camera.gwpagl01'):
        command = "echo -e '#!/bin/sh\r\n\r\nfw_manager.sh -r\r\n" \
            "/bin/riu_w 101e 53 3012\r\ntelnetd' > /data/scripts/post_init.sh"
    else:
        command = "echo -e '#!/bin/sh\r\n\r\nfw_manager.sh -r\r\n" \
            "echo enable > /sys/class/tty/tty/enable\r\ntelnetd' "\
                "> /data/scripts/post_init.sh"
    shell.run_command(command)
    command = "chmod a+x /data/scripts/post_init.sh"
    shell.run_command(command)
    command = "mkdir -p /data/bin"
    shell.write(command.encode() + b"\n")
    time.sleep(1)
    if model in ('lumi.gateway.aqcn02', 'lumi.camera.gwpagl01'):
        shell.check_bin('mosquitto', MD5_MOSQUITTO_ARMV7L , 'bin/armv7l/mosquitto')
        if model in ('lumi.gateway.aqcn02'):
            command = "chattr +i /data/scripts"
            shell.run_command(command)
    else:
        shell.check_bin('mosquitto', MD5_MOSQUITTO_MIPSEL, 'bin/mipsel/mosquitto')


def is_aqaragateway(host: str,
                    password: str,
                    device_name: str) -> Optional[dict]:
    """return name if is supported gateway"""
    result = {}
    result['status'] = 'error'
    token = None

    if host:
        try:
            socket.inet_aton(host)
            if device_name and 'g2h' in device_name:
                shell = TelnetShell(host, password, device_name)
                raw = str(shell.read_file('/etc/build.prop'))
                data = re.search(r"ro\.sys\.name=([a-zA-Z0-9.-]+).+", raw)
                name = data.group(1) if data else ''
                data = re.search(r"ro\.sys\.model=([a-zA-Z0-9.-]+).+", raw)
                model = data.group(1) if data else ''
                raw = str(shell.read_file('/mnt/config/miio/device.conf'))
                data = re.search(r"mac=([a-zA-Z0-9:]+).+", raw)
                mac = data.group(1) if data else ''
            else:
                shell = TelnetShell(host, password, device_name)
                model = shell.get_prop("persist.sys.model")
                name = shell.get_prop("ro.sys.name")
                mac = shell.get_prop("persist.sys.miio_mac")
                token = shell.get_token()

        except (ConnectionError, EOFError, socket.error):
            result['status'] = "connection_error"
            return result

        if model in DEVICES[0]:
            result[CONF_NAME] = "{}-{}".format(
                name, mac[-5:].upper().replace(":", ""))
            result['model'] = model
            result['status'] = 'ok'
            result['token'] = token

            if model in ('lumi.gateway.acn01', 'lumi.aircondition.acn05',
                         'lumi.gateway.sacn01', 'lumi.gateway.iragl5',
                          'lumi.gateway.iragl7', 'lumi.gateway.iragl01',
                          'lumi.gateway.aqcn02'
                          ):
                prepare_aqaragateway(shell, model)
        if shell:
            shell.close()

    return result
