"""Minimal client for the Sage 300 MCP server (Streamable HTTP, stateless, JSON replies).

One function: call_tool(token, name, arguments). The token is the signed-in user's own token and is
forwarded on every call, so the MCP server applies that user's SQL grants and Sage 300 security.
Nothing here can write: the server only exposes read tools, and this client only calls tools.
"""
import json
import os
import re
import urllib.error
import urllib.request

MCP_URL = os.environ.get('MCP_URL', 'http://127.0.0.1:8765/mcp')
TIMEOUT = float(os.environ.get('MCP_TIMEOUT', '20'))


class Error(Exception):
    """Base class for everything this module raises."""


class AuthError(Error):
    """The MCP server did not accept the token (missing, unknown, revoked or expired)."""


class ToolError(Error):
    """The tool ran and said no. The message is the server's own text, prefixed [sql] / [sage] / [gateway] / [auth]."""


class Unavailable(Error):
    """The MCP server could not be reached or sent something that is not a tool result."""


def call_tool(token, name, arguments=None, url=None):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                       'params': {'name': name, 'arguments': arguments or {}}}).encode()
    req = urllib.request.Request(url or MCP_URL, data=body, method='POST', headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'Authorization': 'Bearer ' + (token or '')})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AuthError('the Sage MCP server did not accept this token (HTTP %d)' % e.code)
        raise Unavailable('the Sage MCP server answered HTTP %d' % e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Unavailable('the Sage MCP server is not reachable (%s)' % getattr(e, 'reason', e))
    except ValueError:
        raise Unavailable('the Sage MCP server sent a reply that is not JSON')

    if 'error' in payload:
        err = payload['error'] or {}
        raise Unavailable('MCP error %s: %s' % (err.get('code'), err.get('message')))
    result = payload.get('result') or {}
    text = ' '.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text').strip()
    if result.get('isError'):
        text = re.sub(r'^Error executing tool \S+: ', '', text)   # keep the [sql]/[sage]/[gateway] message itself
        raise ToolError(text or 'the tool refused without giving a reason')
    structured = result.get('structuredContent')
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {'result'}:
            return structured['result']          # list-returning tools are wrapped as {"result": [...]}
        return structured
    try:
        return json.loads(text)
    except ValueError:
        return text
