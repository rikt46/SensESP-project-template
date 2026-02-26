"""Unit tests for the MicroPython prototype.

These tests run under CPython by mocking the small set of MicroPython
modules used by `micropython/main.py`. They exercise configuration loading,
Signal K payload formatting, websocket queue behaviour, and the websocket
manager's URL construction.
"""

import sys
import importlib
import asyncio
import json
import os


def setup_micropython_import(monkeypatch, tmp_path, extra_modules=None):
    # Ensure we're in a clean directory to control CONFIG_PATH usage
    monkeypatch.chdir(tmp_path)

    # Provide real asyncio as uasyncio for compatibility
    sys.modules.setdefault('uasyncio', asyncio)

    # Basic mocks for network and machine modules so import succeeds
    class WLAN:
        def __init__(self, iface):
            self._connected = False

        def active(self, v=None):
            return True

        def isconnected(self):
            return self._connected

        def connect(self, ssid, pw):
            self._connected = True

        def ifconfig(self):
            return ('192.0.2.1', '255.255.255.0', '192.0.2.254', '8.8.8.8')

    net = type('net', (), {'WLAN': WLAN, 'STA_IF': 0})
    sys.modules.setdefault('network', net)

    class Pin:
        IN = 0
        OUT = 1
        PULL_UP = 2

        def __init__(self, n, mode=None, pull=None):
            self._n = n
            self._v = 0

        def value(self, v=None):
            if v is None:
                return self._v
            self._v = v

    class ADC:
        ATTN_11DB = 0

        def __init__(self, pin):
            pass

        def atten(self, v):
            pass

        def read(self):
            return 2048

    mach = type('mach', (), {'Pin': Pin, 'ADC': ADC})
    sys.modules.setdefault('machine', mach)

    # Provide a simple requests/urequests module used by main.py
    posts = {}

    def post(url, data=None, headers=None):
        posts['last'] = {'url': url, 'data': data, 'headers': headers}
        class Resp:
            def close(self):
                pass

        return Resp()

    req = type('req', (), {'post': post})
    sys.modules.setdefault('urequests', req)

    # Provide a websocket client module placeholder
    # Provide light-weight websocket placeholders; tests can override
    # `uwebsockets.client` to supply a fake `connect` implementation.
    ws_client = type('ws', (), {})
    sys.modules.setdefault('uwebsockets.client', ws_client)
    sys.modules.setdefault('uwebsocket', ws_client)

    # Inject any extra modules provided by test
    if extra_modules:
        for name, mod in extra_modules.items():
            sys.modules[name] = mod

    return posts


def reload_main_module():
    if 'micropython.main' in sys.modules:
        del sys.modules['micropython.main']
    return importlib.import_module('micropython.main')


def test_load_config_creates_default(monkeypatch, tmp_path):
    posts = setup_micropython_import(monkeypatch, tmp_path)
    m = reload_main_module()
    cfg = m.load_config()
    assert 'wifi_ssid' in cfg
    # config.json should have been written
    assert os.path.exists('config.json')


def test_publish_signal_k_http(monkeypatch, tmp_path):
    posts = setup_micropython_import(monkeypatch, tmp_path)
    m = reload_main_module()
    cfg = {'sk_server': 'http://example.com', 'use_ws': False, 'publish_enabled': True}
    asyncio.run(m.publish_signal_k(cfg, 'sensors.test.value', 123))
    assert 'last' in posts
    payload = json.loads(posts['last']['data'])
    assert payload['context'] == 'vessels.self'
    assert payload['updates'][0]['values'][0]['value'] == 123


def test_publish_signal_k_ws_queue(monkeypatch, tmp_path):
    posts = setup_micropython_import(monkeypatch, tmp_path)
    m = reload_main_module()
    # Create a fake ws_queue with an async put method
    calls = {}

    class FakeQueue:
        def __init__(self):
            calls['put_called'] = False

        async def put(self, item):
            calls['put_called'] = True
            calls['item'] = item

    m.ws_queue = FakeQueue()
    cfg = {'sk_server': 'http://example.com', 'use_ws': True, 'publish_enabled': True}
    asyncio.run(m.publish_signal_k(cfg, 'sensors.test.value', 9.5))
    assert calls.get('put_called') is True
    assert calls.get('item') is not None


def test_ws_manager_attempts_connect(monkeypatch, tmp_path):
    # Ensure connect is called with expected ws URL
    called = {}

    def fake_connect(url):
        called['url'] = url
        raise Exception('connect-fail')

    extra = {'uwebsockets.client': type('mod', (), {'connect': fake_connect})}
    posts = setup_micropython_import(monkeypatch, tmp_path, extra_modules=extra)
    m = reload_main_module()
    cfg = {'sk_server': 'http://example.com', 'use_ws': True}
    # Run ws_manager with a short timeout; it should have attempted connect
    try:
        asyncio.run(asyncio.wait_for(m.ws_manager(cfg), timeout=0.3))
    except Exception:
        pass
    assert 'url' in called
    assert called['url'].startswith('ws://example.com')
