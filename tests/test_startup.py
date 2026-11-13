"""Run actual Gateway methods with synthetic network clients; no HA or devices."""
import ast
import asyncio
import logging
from pathlib import Path
import socket
import threading
import time
from types import SimpleNamespace
import unittest
SOURCE = Path(__file__).resolve().parents[1] / 'custom_components/aqara_gateway/core/gateway.py'

class StartupTests(unittest.IsolatedAsyncioTestCase):

    def engine(self):
        module = ast.parse(SOURCE.read_text(encoding='utf-8'))
        cls = next((n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'Gateway'))
        cls.body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ('async_run', '_async_run_startup', 'async_connect', '_async_connect_startup', 'stop', 'async_disconnect', '_check_port', '_mqtt_connect')]
        self.pauses = []

        async def sleep(seconds):
            self.pauses.append(seconds)
            await asyncio.sleep(0)
        self.ns = dict(asyncio=SimpleNamespace(sleep=sleep, Lock=asyncio.Lock), socket=socket, DOMAIN='fixture', _LOGGER=logging.getLogger('fixture'))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SOURCE), 'exec'), self.ns)
        obj = self.ns['Gateway']()
        self.main_thread = threading.get_ident()
        self.calls = []
        self.devices = [{'mac': '0x1234', 'model': 'synthetic', 'extra': 'retained'}]
        self.setup_rows = []

        async def executor(fn, *args):
            return await asyncio.to_thread(fn, *args)
        obj.hass = SimpleNamespace(data={'fixture': {}}, async_add_executor_job=executor)
        obj.enabled = obj.available = False
        obj.main_task = None
        obj._initial_state = SimpleNamespace(stop=lambda: None, disconnected=lambda: None)
        obj.devices = {}
        obj.host = 'synthetic.invalid'

        def io(name, result):

            def run(*args, **kwargs):
                self.assertNotEqual(threading.get_ident(), self.main_thread, name + ' blocked the event loop')
                self.calls.append(name)
                return result
            return run
        obj._check_port = io('probe', True)
        obj._prepare_gateway = io('prepare', self.devices)
        obj._mqttc = SimpleNamespace(connect=io('connect', 0), loop_stop=io('stop', None), loop_start=io('start', None), reconnect=io('reconnect', None))

        async def setup(rows):
            self.assertEqual(threading.get_ident(), self.main_thread)
            self.setup_rows.append(rows)
            obj.devices.update({str(i): row for i, row in enumerate(rows)})
        obj.async_setup_devices = setup
        return obj

    async def test_network_io_off_loop_and_device_setup_on_loop(self):
        obj = self.engine()
        await obj.async_run()
        self.assertEqual(self.calls, ['probe', 'prepare', 'stop', 'reconnect', 'start'])
        self.assertEqual(self.setup_rows, [self.devices])
        self.assertEqual(obj._gw_topic, 'gw/1234/')
        self.assertTrue(obj.available)
        self.assertEqual(obj.hass.data['fixture'], {'telnet': [obj.host], 'mqtt': [obj.host]})

    async def test_slow_telnet_keeps_event_loop_responsive(self):
        obj = self.engine()
        original = obj._prepare_gateway

        def slow(*args):
            time.sleep(0.08)
            return original(*args)
        obj._prepare_gateway = slow
        task = asyncio.create_task(obj.async_run())
        ticks = 0
        while not task.done():
            await asyncio.sleep(0.005)
            ticks += 1
        await task
        self.assertGreater(ticks, 4)

    async def test_mqtt_enabled_early_does_not_skip_discovery_retry(self):
        obj = self.engine()
        probes = []

        def probe(port):
            self.assertNotEqual(threading.get_ident(), self.main_thread)
            obj.enabled = True
            probes.append(port)
            return len(probes) > 1
        obj._check_port = probe
        await obj.async_run()
        self.assertEqual(probes, [23, 23])
        self.assertEqual(self.setup_rows, [self.devices])
        self.assertEqual(self.pauses, [30])

    async def test_invalid_device_read_retries_without_dropping_devices(self):
        obj = self.engine()
        reads = []

        def prepare(get_devices=False):
            self.assertNotEqual(threading.get_ident(), self.main_thread)
            reads.append(get_devices)
            return False if len(reads) == 1 else self.devices
        obj._prepare_gateway = prepare
        await obj.async_run()
        self.assertEqual(reads, [True, True])
        self.assertEqual(self.setup_rows, [self.devices])
        self.assertEqual(self.pauses, [30])

    async def test_mqtt_failure_keeps_prepare_and_retry_behavior(self):
        obj = self.engine()
        attempts = []

        def reconnect():
            self.assertNotEqual(threading.get_ident(), self.main_thread)
            attempts.append(1)
            if len(attempts) == 1:
                raise OSError('synthetic unavailable')
        obj._mqttc.reconnect = reconnect
        original = obj._prepare_gateway
        obj._prepare_gateway = lambda get_devices=False: original(get_devices) if get_devices else False
        await obj.async_run()
        self.assertEqual(len(attempts), 2)
        self.assertEqual(self.pauses, [30])
        self.assertEqual(self.setup_rows, [self.devices])

    async def test_cancellation_does_not_publish_late_device_setup(self):
        obj = self.engine()
        started = threading.Event()

        def prepare(*args):
            started.set()
            time.sleep(0.08)
            return self.devices
        obj._prepare_gateway = prepare
        task = asyncio.create_task(obj.async_run())
        for _ in range(100):
            if started.is_set() or task.done():
                break
            await asyncio.sleep(0.002)
        self.assertTrue(started.is_set())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.1)
        self.assertEqual(self.setup_rows, [])

    async def test_port_probe_has_timeout_and_always_closes(self):
        obj = self.engine()
        calls = []

        class Sock:

            def settimeout(self, value):
                calls.append(('timeout', value))

            def connect_ex(self, address):
                calls.append(('connect', address))
                raise OSError('synthetic network failure')

            def close(self):
                calls.append(('close',))
        self.ns['socket'] = SimpleNamespace(socket=lambda *args: Sock(), AF_INET=socket.AF_INET, SOCK_STREAM=socket.SOCK_STREAM)
        result = self.ns['Gateway']._check_port(obj, 23)
        self.assertFalse(result)
        self.assertEqual(calls, [('timeout', 5), ('connect', (obj.host, 23)), ('close',)])

    async def test_reconnect_keeps_existing_devices_without_telnet_rediscovery(self):
        obj = self.engine()
        obj.devices = {'existing': {'model': 'retained'}}
        before = obj.devices.copy()
        await obj.async_run()
        self.assertEqual(obj.devices, before)
        self.assertEqual(self.setup_rows, [])
        self.assertEqual(self.calls, ['stop', 'reconnect', 'start'])

    async def test_overlapping_startups_do_not_duplicate_discovery(self):
        obj = self.engine()
        await asyncio.gather(obj.async_run(), obj.async_run())
        self.assertEqual(self.setup_rows, [self.devices])
        self.assertEqual(self.calls.count('prepare'), 1)

    async def test_initial_mqtt_connect_and_discovery_do_not_race(self):
        obj = self.engine()
        await asyncio.gather(obj.async_connect(), obj.async_run())
        self.assertTrue(obj.enabled)
        self.assertTrue(obj.available)
        self.assertEqual(self.setup_rows, [self.devices])
        self.assertLess(self.calls.index('connect'), self.calls.index('probe'))
        self.assertLess(self.calls.index('start'), self.calls.index('probe'))

    async def test_unload_during_reconnect_does_not_restart_mqtt(self):
        obj = self.engine()
        obj.devices = {'existing': {'model': 'retained'}}
        entered = threading.Event()
        release = threading.Event()
        def reconnect():
            entered.set()
            release.wait(1)
        obj._mqttc.reconnect = reconnect
        task = asyncio.create_task(obj.async_run())
        for _ in range(100):
            if entered.is_set():
                break
            await asyncio.sleep(.002)
        self.assertTrue(entered.is_set())
        obj.stop()
        shutdown = asyncio.create_task(obj.async_disconnect())
        await asyncio.sleep(.01)
        release.set()
        await asyncio.gather(task, shutdown)
        self.assertFalse(obj.available)
        self.assertFalse(obj.enabled)
        self.assertNotIn('start', self.calls)

    async def test_stop_during_discovery_does_not_create_devices(self):
        obj = self.engine()
        entered = threading.Event()
        release = threading.Event()
        def prepare(*args):
            entered.set()
            release.wait(1)
            return self.devices
        obj._prepare_gateway = prepare
        task = asyncio.create_task(obj.async_run())
        for _ in range(100):
            if entered.is_set():
                break
            await asyncio.sleep(.002)
        self.assertTrue(entered.is_set())
        obj.stop()
        shutdown = asyncio.create_task(obj.async_disconnect())
        await asyncio.sleep(.01)
        release.set()
        await asyncio.gather(task, shutdown)
        self.assertEqual(self.setup_rows, [])
        self.assertFalse(obj.available)
if __name__ == '__main__':
    unittest.main()
