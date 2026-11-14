"""Real Gateway message/handler integration with synthetic read-only MQTT."""
import ast
import asyncio
import importlib.util
import json
import logging
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'custom_components/aqara_gateway/core/gateway.py'
HELPER = ROOT / 'custom_components/aqara_gateway/core/initial_state.py'

class Reporter:

    def __init__(self, attr='light'):
        self._attr = attr
        self._state = None
        self.rows = []

    def update(self, data):
        self.rows.append(dict(data))
        if self._attr in data:
            self._state = data[self._attr]

class InitialTests(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.jobs = []
        self.mqtt = []
        self.mode = 'reply'
        self.loop = asyncio.get_running_loop()
        self.thread = threading.get_ident()
        module = ast.parse(SOURCE.read_text(encoding='utf-8'))
        cls = next((n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'Gateway'))
        ns = dict(asyncio=asyncio, time=time, json=json, _LOGGER=logging.getLogger('fixture'), GLOBAL_PROP={}, VRF_MODELS=set(), DOMAIN='fixture', ATTR_HS_COLOR='hs_color', ATTR_RGB_COLOR='rgb_color', ATTR_BRIGHTNESS='brightness')
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SOURCE), 'exec', flags=__import__('__future__').annotations.compiler_flag), ns)
        self.namespace = ns
        self.g = ns['Gateway'].__new__(ns['Gateway'])
        g = self.g
        g.devices = {}
        g.updates = {}
        g.options = {}
        g.available = False
        g.enabled = False
        g._debug = ''
        g.host = 'synthetic.invalid'
        g.debug = lambda *args: None

        async def executor(fn, *args):
            return await asyncio.to_thread(fn, *args)

        def spawn(hass, coro, name):
            task = asyncio.create_task(coro)
            self.jobs.append(task)
            return task
        g.hass = SimpleNamespace(loop=self.loop, data={'fixture': {'mqtt': [], 'telnet': []}}, async_add_executor_job=executor)
        g._config_entry = SimpleNamespace(async_create_background_task=spawn)

        def publish(topic, payload, qos=0, retain=False):
            self.assertNotEqual(threading.get_ident(), self.thread, 'Publish must not block the HA loop')
            message = json.loads(payload)
            self.mqtt.append(message)
            self.assertEqual(topic, 'zigbee/recv')
            self.assertEqual(message['cmd'], 'read')
            self.assertFalse(retain)
            fields = message.get('params', message.get('mi_spec', []))
            self.assertTrue(all(('value' not in p for p in fields)))
            if self.mode in ('reply', 'error'):
                response = {'cmd': 'read_rsp', 'did': message['did'], 'id': message['id']}
                response['results' if 'params' in message else 'mi_spec'] = [{**p, 'value': self.values.get(p.get('res_name', str(p.get('siid')) + '.' + str(p.get('piid'))), 1), 'error_code': 1 if self.mode == 'error' else 0} for p in fields]
                self.loop.call_soon_threadsafe(g._process_message, response)
            return SimpleNamespace(rc=4 if self.mode == 'publish_error' else 0)
        g._mqttc = SimpleNamespace(publish=publish, subscribe=lambda *args: None)
        self.values = {}
        self.helper = None
        if HELPER.exists():
            spec = importlib.util.spec_from_file_location('initial_state_fixture', HELPER)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            self.helper = m.InitialStateSync(g, {})
            self.helper.response_timeout = 0.01
            self.helper.debounce = 0.001
        g._initial_state = self.helper

    async def test_request_ids_are_not_reused_across_reconnects_or_devices(self):
        self.helper.request_ids['lumi.one'] = (65535, 0)
        self.assertEqual(self.helper.next_request_id('lumi.one'), 65535)
        self.assertEqual(self.helper.next_request_id('lumi.one'), 1)
        self.helper.disconnected()
        self.assertEqual(self.helper.next_request_id('lumi.one'), 2)
        self.assertTrue(self.helper.was_requested('lumi.one', 65535))
        self.assertFalse(self.helper.was_requested('lumi.two', 65535))
        self.assertFalse(self.helper.was_requested('lumi.one', True))

    async def test_exhausted_request_ids_keep_report_only_updates(self):
        self.helper.request_ids['lumi.demo'] = (17, 65535)
        self.assertIsNone(self.helper.next_request_id('lumi.demo'))
        self.assertTrue(self.helper.was_requested('lumi.demo', 16))
        self.assertTrue(self.helper.was_requested('lumi.demo', 17))

    async def asyncTearDown(self):
        if self.helper:
            self.helper.stop()
        for task in self.jobs:
            task.cancel()
        await asyncio.gather(*self.jobs, return_exceptions=True)

    def device(self, did='lumi.demo', fp1=False, mi=False):
        params = [['3.51.85', None, 'occupancy', 'binary_sensor']] if fp1 else [['4.1.85', None, 'light', 'light'], ['14.1.85', None, 'brightness', None], ['14.2.85', None, 'color_temp', None], ['13.1.85', None, 'action', 'event']]
        item = dict(did=did, mac='0xfixture', type='zigbee', model='lumi.motion.ac01' if fp1 else 'lumi.light.fixture', params=[] if mi else params, mi_spec=[['2.11', None, 'light', 'light']] if mi else [])
        self.g.devices[did] = item
        return item

    def frame(self, did='lumi.demo', value=1, code='4.1.85', **extra):
        return {'cmd': 'report', 'did': did, 'params': [{'res_name': code, 'value': value}], **extra}

    async def settle(self):
        for _ in range(150):
            await asyncio.sleep(0.002)
            if self.jobs and all((t.done() for t in self.jobs)):
                break
        for t in self.jobs:
            if t.done() and (not t.cancelled()):
                t.result()

    async def wait_publish(self):
        for _ in range(200):
            if self.mqtt:
                return
            for task in self.jobs:
                if task.done() and (not task.cancelled()):
                    task.result()
            await asyncio.sleep(0.002)
        self.fail('No read request was published within the bounded test window')

    async def test_early_report_survives_before_device_and_handler(self):
        self.g._process_message(self.frame(value=0))
        self.device()
        r = Reporter()
        self.g.add_update('lumi.demo', r.update)
        self.assertEqual(r._state, 0, 'An actual early power report must initialize the late handler')

    async def test_initial_light_read_and_zero_value(self):
        self.device()
        self.values = {'4.1.85': 0}
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertEqual(r._state, 0)
        self.assertEqual(len(self.mqtt), 1)

    async def test_fp1_unoccupied_is_not_lost(self):
        self.device(fp1=True)
        self.values = {'3.51.85': 0}
        r = Reporter('occupancy')
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertEqual(r._state, 0)

    async def test_fp1_occupied(self):
        self.device(fp1=True)
        r = Reporter('occupancy')
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertEqual(r._state, 1)

    async def test_does_not_replay_action_events(self):
        msg = self.frame()
        msg['params'].append({'res_name': '13.1.85', 'value': 2})
        self.g._process_message(msg)
        self.device()
        light = Reporter()
        event = Reporter('action')
        self.g.add_update('lumi.demo', light.update)
        self.g.add_update('lumi.demo', event.update)
        self.assertEqual(light._state, 1)
        self.assertEqual(event.rows, [])
        self.g._process_message(self.frame(code='13.1.85', value=3))
        self.assertEqual(event._state, 3, 'Live events must remain functional')

    async def test_late_handler_gets_fresh_state(self):
        self.device()
        first = Reporter()
        self.g.add_update('lumi.demo', first.update)
        self.g._process_message(self.frame(value=1))
        later = Reporter()
        self.g.add_update('lumi.demo', later.update)
        self.assertEqual(later._state, 1)

    async def test_read_error_keeps_unknown(self):
        self.device()
        self.mode = 'error'
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertIsNone(r._state)
        self.assertEqual(len(self.mqtt), 3)

    async def test_no_response_is_bounded_and_keeps_unknown(self):
        self.device()
        self.mode = 'hold'
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertIsNone(r._state)
        self.assertEqual(len(self.mqtt), 3)

    async def test_stale_read_does_not_override_newer_report(self):
        self.helper.clock = lambda: 5.0
        self.device()
        self.mode = 'hold'
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.wait_publish()
        request = self.mqtt[0]
        self.g._process_message(self.frame(value=1))
        self.g._process_message({'cmd': 'read_rsp', 'did': 'lumi.demo', 'id': request['id'], 'results': [{'res_name': '4.1.85', 'value': 0}]})
        self.assertEqual(r._state, 1)

    async def test_cancel_prevents_late_read_update(self):
        self.device()
        self.mode = 'hold'
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.wait_publish()
        request = self.mqtt[0]
        self.helper.stop()
        self.g._process_message({'cmd': 'read_rsp', 'did': 'lumi.demo', 'id': request['id'], 'results': [{'res_name': '4.1.85', 'value': 1}]})
        await asyncio.sleep(0.02)
        self.assertIsNone(r._state)

    async def test_expired_early_value_is_not_replayed(self):
        now = [0.0]
        self.helper.clock = lambda: now[0]
        self.g._process_message(self.frame(value=1))
        now[0] = 121
        self.device()
        r = Reporter()
        self.g.add_update('lumi.demo', r.update)
        self.assertIsNone(r._state)

    async def test_other_devices_do_not_get_new_queries(self):
        self.g.devices['lumi.demo'] = dict(self.device(), model='lumi.sensor_magnet.fixture', params=[['3.1.85', None, 'contact', 'binary_sensor']])
        r = Reporter('contact')
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await asyncio.sleep(0.03)
        self.assertEqual(self.mqtt, [])

    async def test_mi_spec_multi_digit_property(self):
        self.device(mi=True)
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertEqual(self.mqtt[0]['mi_spec'], [{'siid': 2, 'piid': 11}])
        self.assertEqual(r._state, 1)

    async def test_reconnect_queries_again(self):
        self.device()
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        n = len(self.mqtt)
        self.helper.disconnected()
        self.helper.connected()
        await self.settle()
        self.assertGreater(len(self.mqtt), n)

    async def test_heartbeat_hydrates_late_occupancy(self):
        self.g._process_message({'cmd': 'heartbeat', 'params': [{'did': 'lumi.demo', 'res_list': [{'res_name': '3.51.85', 'value': 0}]}]})
        self.device(fp1=True)
        r = Reporter('occupancy')
        self.g.add_update('lumi.demo', r.update)
        self.assertEqual(r._state, 0)

    async def test_non_numeric_reply_does_not_invent_state(self):
        self.device()
        self.values = {'4.1.85': 'unknown'}
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertIsNone(r._state)

    async def test_last_handler_removal_cancels_pending_read(self):
        self.device()
        self.mode = 'hold'
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.wait_publish()
        self.g.remove_update('lumi.demo', r.update)
        count = len(self.mqtt)
        await asyncio.sleep(0.04)
        self.assertEqual(len(self.mqtt), count)

    async def test_two_handlers_share_one_read_batch(self):
        self.device()
        self.helper.connected()
        a = Reporter()
        b = Reporter('brightness')
        self.g.add_update('lumi.demo', a.update)
        self.g.add_update('lumi.demo', b.update)
        await self.settle()
        self.assertEqual(len(self.mqtt), 1)
        self.assertEqual(a._state, 1)
        self.assertEqual(b._state, 1)

    async def test_legacy_background_task_api_fallback(self):
        del self.g._config_entry.async_create_background_task
        self.device()
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertEqual(r._state, 1)

    async def test_real_constructor_installs_sync_component(self):
        self.namespace.update(InitialStateSync=type(self.helper), Client=lambda: SimpleNamespace(), CONF_HOST='host', CONF_MODEL='model')
        entry = SimpleNamespace(options={'host': 'synthetic.invalid', 'model': 'fixture'})
        obj = self.namespace['Gateway'](self.g.hass, entry, {'devices': {}})
        self.assertIs(obj._initial_state.gateway, obj)
        self.assertEqual(obj.devices, {})
        obj._initial_state.stop()

    async def test_mqtt_connect_callback_schedules_on_ha_loop(self):
        self.device()
        r = Reporter()
        self.g.add_update('lumi.demo', r.update)
        await asyncio.to_thread(self.g.on_connect, self.g._mqttc, None, None, 0)
        await self.settle()
        self.assertEqual(r._state, 1)

    async def test_publish_failure_is_bounded(self):
        self.mode = 'publish_error'
        self.device()
        r = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', r.update)
        await self.settle()
        self.assertEqual(len(self.mqtt), 3)
        self.assertIsNone(r._state)

    async def test_virtual_catalog_attribute_is_not_queried(self):
        device = self.device()
        device['params'].append([None, 'hs_color', 'hs_color', None])
        self.assertNotIn('None', self.helper.properties('lumi.demo'))

    async def test_freshness_survives_value_cache_eviction(self):
        self.device()
        self.helper.generation = 1
        self.helper.mqtt_ready = True
        self.helper.session_started = self.helper.clock()
        reporter = Reporter()
        self.g.add_update('lumi.demo', reporter.update)
        self.helper.requests[('lumi.demo', 10)] = ('lumi.demo', 1, self.helper.clock(), {'4.1.85'}, {'light': -1})
        self.g._process_message(self.frame(value=1))
        for index in range(64):
            did = 'lumi.other' + str(index)
            self.device(did=did)
            self.helper.arrival += 1
            self.helper.remember(did, {'light': 1})
        self.assertNotIn('lumi.demo', self.helper.cache)
        self.g._process_message({'cmd': 'read_rsp', 'did': 'lumi.demo', 'id': 10, 'results': [{'res_name': '4.1.85', 'value': 0}]})
        self.assertEqual(reporter._state, 1)

    async def test_disconnect_callback_runs_on_loop_without_restarting_after_stop(self):
        starts = []
        self.g.start = lambda: starts.append(threading.get_ident())
        await asyncio.to_thread(self.g.on_disconnect, self.g._mqttc, None, 1)
        await asyncio.sleep(.01)
        self.assertEqual(starts, [self.thread])
        self.g.stop()
        await asyncio.to_thread(self.g.on_disconnect, self.g._mqttc, None, 1)
        await asyncio.sleep(.01)
        self.assertEqual(starts, [self.thread])

    async def test_late_connect_callback_cannot_mark_stopped_gateway_available(self):
        self.g.stop()
        await asyncio.to_thread(self.g.on_connect, self.g._mqttc, None, None, 0)
        await asyncio.sleep(.01)
        self.assertFalse(self.g.available)
        self.assertEqual(self.mqtt, [])

    async def test_evicted_request_cannot_override_a_newer_report(self):
        self.device()
        self.mode = 'hold'
        reporter = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', reporter.update)
        await self.wait_publish()
        old = self.mqtt[0]
        self.g._process_message(self.frame(value=1))
        for index in range(128):
            key = ('lumi.other', index)
            self.helper.requests[key] = ('lumi.other', self.helper.generation, 0, {'4.1.85'}, {})
            if len(self.helper.requests) > 128:
                self.helper.requests.popitem(last=False)
        self.g._process_message({'cmd':'read_rsp','did':'lumi.demo','id':old['id'],'results':[{'res_name':'4.1.85','value':0}]})
        self.assertEqual(reporter._state, 1)

    async def test_evicted_old_session_reply_is_discarded(self):
        self.device()
        self.mode = 'hold'
        reporter = Reporter()
        self.helper.connected()
        self.g.add_update('lumi.demo', reporter.update)
        await self.wait_publish()
        old = self.mqtt[0]
        self.helper.requests.clear()
        self.helper.disconnected()
        self.helper.connected()
        self.g._process_message({'cmd':'read_rsp','did':'lumi.demo','id':old['id'],'results':[{'res_name':'4.1.85','value':0}]})
        self.assertIsNone(reporter._state)
if __name__ == '__main__':
    unittest.main()
