"""Tests for the Customer Orders dashboard.

Unit tests fake the MCP client. Integration tests talk to the real MCP server at MCP_URL and are skipped
when it is not running, so the suite passes on a laptop and proves the privilege model on the box.
"""
import os
import socket
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as appmod          # noqa: E402
import mcp_client as mcp      # noqa: E402

PREFIX = appmod.PREFIX
FAKE_WHOAMI = {'token_id': 't1', 'label': 'Test user', 'sql_login': 'sfg_readonly', 'sage_user': 'TESTUSR',
               'companies': {'QUIK': {'name': 'QuikServ', 'open': True, 'cost_visible': {'OE': True, 'IC': True}},
                             'USBP': {'name': 'US Bulletproofing', 'open': False, 'reason': '[sage] no authorization'}}}
FAKE_HISTORY = {'columns': ['order_number', 'type', 'status', 'order_date', 'invoiced_before_tax'],
                'rows': [['ORD1', 'Order', 'Complete', '2024-01-02', 1234.5], ['ORD2', 'Order', 'Incomplete', '2024-03-04', None]],
                'masked_columns': [], 'truncated': False,
                'summary': {'customer': 'CUT001', 'orders': 2, 'complete_orders': 1, 'invoiced_before_tax': 1234.5,
                            'invoiced_with_tax': 1300.0, 'first_order': '2024-01-02', 'last_order': '2024-03-04'}}


@pytest.fixture
def client():
    appmod.app.config['TESTING'] = True
    return appmod.app.test_client()


def fake(monkeypatch, handler):
    calls = []

    def call_tool(token, name, arguments=None, url=None):
        calls.append((token, name, arguments or {}))
        return handler(token, name, arguments or {})
    monkeypatch.setattr(mcp, 'call_tool', call_tool)
    return calls


def test_signed_out_shows_signin(client):
    r = client.get(PREFIX + '/')
    assert r.status_code == 200 and b'Sage access token' in r.data and b'name="customer"' not in r.data


def test_healthz(client):
    assert client.get(PREFIX + '/healthz').data == b'ok\n'


def test_signin_rejects_bad_token(client, monkeypatch):
    def handler(token, name, args):
        raise mcp.AuthError('no')
    fake(monkeypatch, handler)
    r = client.post(PREFIX + '/signin', data={'token': 'bad'}, follow_redirects=True)
    assert b'not accepted' in r.data and 'sage_token' not in (r.headers.get('Set-Cookie') or '')


def test_signin_sets_cookie_and_dashboard_uses_it(client, monkeypatch):
    def handler(token, name, args):
        assert token == 'good-token'
        return FAKE_WHOAMI if name == 'whoami' else FAKE_HISTORY
    calls = fake(monkeypatch, handler)
    r = client.post(PREFIX + '/signin', data={'token': 'good-token'})
    assert r.status_code == 302 and 'sage_token=good-token' in r.headers['Set-Cookie'] and 'HttpOnly' in r.headers['Set-Cookie']
    r = client.get(PREFIX + '/?company=QUIK&customer=cut001')
    html = r.data.decode()
    assert r.status_code == 200
    assert 'Test user' in html and 'QUIK · open · costs visible' in html and 'USBP · no access' in html
    assert 'ORD1' in html and '1,234.50' in html and '2 rows' in html
    assert calls[-1] == ('good-token', 'customer_order_history', {'company': 'QUIK', 'customer': 'CUT001', 'include_quotes': False})


def test_quotes_toggle_is_forwarded(client, monkeypatch):
    calls = fake(monkeypatch, lambda t, n, a: FAKE_WHOAMI if n == 'whoami' else FAKE_HISTORY)
    client.set_cookie('sage_token', 'tok', path=PREFIX or '/')
    client.get(PREFIX + '/?company=QUIK&customer=CUT001&quotes=1')
    assert calls[-1][2]['include_quotes'] is True


def test_refusal_is_shown_verbatim_with_who_to_ask(client, monkeypatch):
    def handler(token, name, args):
        if name == 'whoami':
            return FAKE_WHOAMI
        raise mcp.ToolError('[sage] user TESTUSR has no authorization in USBP')
    fake(monkeypatch, handler)
    client.set_cookie('sage_token', 'tok', path=PREFIX or '/')
    html = client.get(PREFIX + '/?company=USBP&customer=CUT001').data.decode()
    assert 'Sage said no.' in html and '[sage] user TESTUSR has no authorization in USBP' in html
    assert 'Sage administrator' in html and 'Sage champion' in html


def test_masked_columns_are_announced(client, monkeypatch):
    masked = dict(FAKE_HISTORY, masked_columns=['CostFC'])
    fake(monkeypatch, lambda t, n, a: FAKE_WHOAMI if n == 'whoami' else masked)
    client.set_cookie('sage_token', 'tok', path=PREFIX or '/')
    assert 'masked by Sage for your role: CostFC' in client.get(PREFIX + '/?customer=CUT001').data.decode()


def test_expired_token_signs_out(client, monkeypatch):
    def handler(token, name, args):
        raise mcp.AuthError('expired')
    fake(monkeypatch, handler)
    client.set_cookie('sage_token', 'old', path=PREFIX or '/')
    r = client.get(PREFIX + '/')
    assert r.status_code == 302 and 'sage_token=;' in r.headers['Set-Cookie']


def test_mcp_down_is_a_503_not_a_crash(client, monkeypatch):
    def handler(token, name, args):
        raise mcp.Unavailable('the Sage MCP server is not reachable')
    fake(monkeypatch, handler)
    client.set_cookie('sage_token', 'tok', path=PREFIX or '/')
    r = client.get(PREFIX + '/')
    assert r.status_code == 503 and b'not reachable' in r.data


# ----------------------------------------------------------------------------------------------- integration

def _mcp_up():
    u = urllib.parse.urlparse(mcp.MCP_URL)
    try:
        socket.create_connection((u.hostname, u.port or 80), timeout=1).close()
        return True
    except OSError:
        return False


live = pytest.mark.skipif(not _mcp_up(), reason='MCP server not reachable at ' + mcp.MCP_URL)


@live
def test_live_unknown_token_is_auth_error():
    with pytest.raises(mcp.AuthError):
        mcp.call_tool('sage-mock-nobody', 'whoami', {})


@live
def test_live_controller_sees_cut001_history():
    out = mcp.call_tool('sage-mock-controller', 'customer_order_history', {'company': 'USBP', 'customer': 'CUT001'})
    assert out['summary']['orders'] == 6 and out['summary']['invoiced_before_tax'] == 100516.36
    assert out['masked_columns'] == [] and len(out['rows']) == 6


@live
def test_live_stockroom_cannot_open_quik_but_can_open_usbp():
    with pytest.raises(mcp.ToolError) as e:
        mcp.call_tool('sage-mock-stockroom', 'customer_order_history', {'company': 'QUIK', 'customer': 'CUT001'})
    assert str(e.value).startswith('[sage]')
    me = mcp.call_tool('sage-mock-stockroom', 'whoami', {})
    assert me['companies']['QUIK']['open'] is False and me['companies']['USBP']['open'] is True


@live
def test_live_intern_has_no_cost_visibility():
    me = mcp.call_tool('sage-mock-intern', 'whoami', {})
    assert me['companies']['QUIK']['open'] is True and me['companies']['QUIK']['cost_visible']['OE'] is False


@live
def test_live_dashboard_end_to_end(client):
    r = client.post(PREFIX + '/signin', data={'token': 'sage-mock-controller'})
    assert r.status_code == 302
    html = client.get(PREFIX + '/?company=USBP&customer=CUT001').data.decode()
    assert 'orders for CUT001' in html and '100,516.36' in html and 'USBP · open' in html
    html = client.get(PREFIX + '/?company=USBP&customer=NOSUCH').data.decode()
    assert 'No orders for NOSUCH in USBP' in html


def test_demo_tokens_and_samples_are_inline(client, monkeypatch):
    r = client.get(PREFIX + '/')
    assert b'sage-mock-salesmanager' in r.data and b'05-13615' in r.data and b'CUT001' in r.data
    calls = fake(monkeypatch, lambda token, name, args: FAKE_WHOAMI if name == 'whoami' else FAKE_HISTORY)
    client.post(PREFIX + '/signin', data={'token': 'good-token'})
    r = client.get(PREFIX + '/')
    assert b'Try:' in r.data and b'05-13615' in r.data
