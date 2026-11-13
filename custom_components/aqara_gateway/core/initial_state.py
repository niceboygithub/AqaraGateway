"""Bounded fresh-state bootstrap for Zigbee lights and FP1; never writes controls."""
import asyncio
from collections import OrderedDict, deque
import copy
import json
import logging
import math
import random
import time

LIGHT = {'light', 'sub light', 'brightness', 'color_temp', 'rgb_color', 'hs_color'}
PRESENCE = {'occupancy', 'monitoring_mode', 'reverted_mode', 'approaching_distance'}
FP1 = {'lumi.motion.ac01', 'lumi.sensor_occupy.agl1'}
_LOGGER = logging.getLogger(__name__)


class InitialStateSync:
    def __init__(self, gateway, global_props):
        self.gateway = gateway
        self.global_props = global_props
        self.clock = time.monotonic
        self.raw = OrderedDict()
        self.cache = OrderedDict()
        # Small ordering metadata follows registered devices, not the value LRU.
        self.orders = {}
        self.requests = OrderedDict()
        self.tasks = {}
        self.requested = set()
        self.generation = 0
        self.mqtt_ready = False
        self.stopped = False
        self.session_started = 0
        self.sequence = random.randint(1, 65535)
        self.arrival = 0
        self.response_timeout = 2.0
        self.debounce = 0.1

    def properties(self, did):
        device = self.gateway.devices.get(did, {})
        if device.get('type') != 'zigbee':
            return {}
        rows = device.get('params') or device.get('mi_spec') or []
        allowed = LIGHT if any(len(p) >= 4 and p[3] == 'light' for p in rows) else PRESENCE if device.get('model') in FP1 else set()
        return {p[0]: p[2] for p in rows if len(p) >= 4 and isinstance(p[0], str) and p[0] and p[2] in allowed}

    def handlers(self, did):
        allowed = set(self.properties(did).values())
        return [h for h in self.gateway.updates.get(did, []) if getattr(getattr(h, '__self__', None), '_attr', None) in allowed]

    @staticmethod
    def decode(data):
        command = data.get('cmd')
        if command == 'heartbeat':
            frames = data.get('params', [])
            body = frames[0] if frames and isinstance(frames[0], dict) else {}
            return body.get('did'), 'res_list', body.get('res_list', []), command
        key = ('results' if 'results' in data else 'mi_spec') if command == 'read_rsp' else ('params' if 'params' in data else 'mi_spec')
        return data.get('did'), key, data.get(key, []), command

    @staticmethod
    def code(param):
        if 'res_name' in param:
            return str(param['res_name'])
        if 'siid' in param and 'piid' in param:
            return str(param['siid']) + '.' + str(param['piid'])
        return None

    @staticmethod
    def valid(value):
        return isinstance(value, (bool, int, float)) and math.isfinite(value) or isinstance(value, str) and len(value) <= 80 and value.lower() not in ('unknown', 'unavailable', 'nan')

    @classmethod
    def accepts(cls, attr, value):
        if not cls.valid(value):
            return False
        if attr in ('rgb_color', 'hs_color') and isinstance(value, str):
            return value.startswith('0x') and 0 < len(value[2:]) <= 8 and all(c in '0123456789abcdefABCDEF' for c in value[2:])
        if attr in LIGHT or attr == 'occupancy':
            return isinstance(value, (bool, int, float))
        return True

    def filter_incoming(self, data):
        if self.stopped:
            return None
        self.arrival += 1
        did, key, params, command = self.decode(data)
        if command not in ('report', 'heartbeat', 'read_rsp') or not isinstance(did, str) or did == 'lumi.0' or not isinstance(params, list):
            return data
        record = self.requests.get(data.get('id')) if command == 'read_rsp' else None
        if record and record[0] == did:
            if record[1] != self.generation or not self.mqtt_ready:
                return None
            props = self.properties(did)
            params = [p for p in params if isinstance(p, dict) and not p.get('error_code', 0) and self.code(p) in record[3] and self.accepts(props.get(self.code(p)), p.get('value')) and self._order(did, props.get(self.code(p))) <= record[4].get(props.get(self.code(p)), -1)]
            if not params:
                return None
            _LOGGER.info('Initial state read response: model=%s attributes=%d', self.gateway.devices.get(did, {}).get('model', 'unknown'), len(params))
            data = {**data, key: params}
        if not self.gateway.devices.get(did) or not self.gateway.updates.get(did):
            # Keep only primitive state fields. Events are discarded at hydration.
            safe = [{k: copy.deepcopy(v) for k, v in p.items() if k in ('res_name', 'siid', 'piid', 'value', 'error_code')} for p in params[:64] if isinstance(p, dict) and self.valid(p.get('value'))]
            if safe:
                self.raw.setdefault(did, deque(maxlen=16)).append((self.clock(), self.arrival, safe))
                self.raw.move_to_end(did)
                while len(self.raw) > 64:
                    self.raw.popitem(last=False)
        return data

    def _seen(self, did, attr):
        item = self.cache.get(did, {}).get(attr)
        return item[1] if item and item[0] == self.generation else -1

    def _order(self, did, attr):
        item = self.orders.get(did, {}).get(attr)
        return item[1] if item and item[0] == self.generation else -1

    def remember(self, did, payload, received=None, order=None):
        allowed = set(self.properties(did).values())
        stamp = self.clock() if received is None else received
        order = self.arrival if order is None else order
        for attr, value in payload.items():
            if attr in allowed and self.accepts(attr, value) and order >= self._order(did, attr):
                self.cache.setdefault(did, {})[attr] = (self.generation, stamp, copy.deepcopy(value), order)
                self.orders.setdefault(did, {})[attr] = (self.generation, order)
                self.cache.move_to_end(did)
        while len(self.cache) > 64:
            self.cache.popitem(last=False)

    def handler_added(self, did, handler):
        if self.stopped or handler not in self.handlers(did):
            return
        props = self.properties(did)
        for stamp, order, params in self.raw.pop(did, []):
            if self.clock() - stamp > 120:
                continue
            values = {}
            for param in params:
                attr = self.global_props.get(self.code(param), props.get(self.code(param)))
                if attr in props.values() and not param.get('error_code', 0):
                    values[attr] = param['value']
            self.remember(did, values, stamp, order)
        values = {attr: copy.deepcopy(item[2]) for attr, item in self.cache.get(did, {}).items() if item[0] == self.generation and self.clock() - item[1] <= 120}
        if values and getattr(handler.__self__, '_state', None) is None:
            handler(values)
            _LOGGER.info('Initial state replay: model=%s attributes=%d', self.gateway.devices.get(did, {}).get('model', 'unknown'), len(values))
        self.schedule(did)

    def handler_removed(self, did, handler):
        if not self.handlers(did):
            self.requested.discard(did)
            task = self.tasks.pop(did, None)
            if task:
                task.cancel()

    def connected(self):
        if self.stopped or self.mqtt_ready:
            return
        self.generation += 1
        self.session_started = self.clock()
        self.mqtt_ready = True
        self.requested.clear()
        for did in tuple(self.gateway.devices):
            self.schedule(did)

    def disconnected(self):
        self.generation += 1
        self.mqtt_ready = False
        for task in tuple(self.tasks.values()):
            task.cancel()
        self.tasks.clear()
        self.requested.clear()
        self.raw.clear()
        self.cache.clear()
        self.orders.clear()

    def stop(self):
        self.stopped = True
        self.disconnected()

    def schedule(self, did):
        if self.stopped or not self.mqtt_ready or not self.handlers(did) or did in self.requested:
            return
        self.requested.add(did)
        coroutine = self.read(did, self.generation)
        create_background_task = getattr(self.gateway._config_entry, 'async_create_background_task', None)
        if create_background_task is not None:
            task = create_background_task(self.gateway.hass, coroutine, 'Aqara initial state')
        else:
            task = self.gateway.hass.loop.create_task(coroutine)
        self.tasks[did] = task
        def done(finished):
            if self.tasks.get(did) is finished:
                self.tasks.pop(did, None)
            if not finished.cancelled():
                error = finished.exception()
                if error:
                    _LOGGER.error('Initial state task failed (%s)', type(error).__name__)
        task.add_done_callback(done)

    def current(self, did, generation):
        return not self.stopped and self.mqtt_ready and generation == self.generation and bool(self.handlers(did))

    async def read(self, did, generation):
        await asyncio.sleep(self.debounce)
        for _ in range(3):
            if not self.current(did, generation):
                return
            props = self.properties(did)
            missing = [code for code, attr in props.items() if self._seen(did, attr) < self.session_started]
            if not missing:
                return
            self.sequence = self.sequence % 65535 + 1
            while self.sequence in self.requests:
                self.sequence = self.sequence % 65535 + 1
            self.requests[self.sequence] = (did, generation, self.clock(), set(missing), {attr: self._order(did, attr) for attr in props.values()})
            while len(self.requests) > 128:
                self.requests.popitem(last=False)
            message = {'cmd': 'read', 'did': did, 'id': self.sequence}
            if self.gateway.devices[did].get('params'):
                message['params'] = [{'res_name': code} for code in missing]
            else:
                message['mi_spec'] = [{'siid': int(code.split('.')[0]), 'piid': int(code.split('.')[1])} for code in missing]
            try:
                await self.gateway.hass.async_add_executor_job(self.gateway._mqttc.publish, 'zigbee/recv', json.dumps(message, separators=(',', ':')), 0, False)
            except (OSError, ConnectionError, TimeoutError):
                pass  # A bounded retry must never invent a device state.
            if not self.current(did, generation):
                return
            await asyncio.sleep(self.response_timeout)
