"""SFG Customer Orders: the simplest dashboard on top of the Sage 300 MCP.

Look up a customer's orders (and optionally quotes) in any company the signed-in user may open.
Read-only. Every MCP call carries the signed-in user's own token, so Sage's rights apply unchanged.
Governed by .claude/skills/sfg-vibe-coding/SKILL.md at the repository root.
"""
import os

from flask import Blueprint, Flask, make_response, redirect, render_template, request, url_for

import mcp_client as mcp

PREFIX = os.environ.get('APP_PREFIX', '/customer-orders').rstrip('/')
COOKIE = 'sage_token'
COOKIE_HOURS = 8
APP_NAME = 'Customer Orders'
HANDOVER_URL = 'https://github.com/BestPracticeAI/SFG_vibe_coding/blob/main/projects/customer-orders/README.md'
# Who to ask when Sage says no. The roles and their contact details live in the skill file (section 7).
HUMANS = {
    'access': 'the Sage administrator named in the skill file (access and cost rights)',
    'views': 'the Sage champion named in the skill file (new views), with the project owner notified',
}

# Demo material shown inline on the pages (the estate is a mock with fictional role stand-ins; the demo
# tokens are deterministic, see /home/ec2-user/mock-sage-300/sage_mcp/tokens.py). Remove on a real estate.
DEMO_TOKENS = [
    ('sage-mock-salesmanager', 'Inside sales manager', 'QUIK and USBTST open, costs visible; USBP refused'),
    ('sage-mock-controller', 'Controller, full rights', 'every built company open, costs visible'),
    ('sage-mock-intern', 'IE intern, inquiry only', 'QUIK open with cost columns masked; USBP refused'),
    ('sage-mock-stockroom', 'Inventory office, USBP only', 'USBP open; QUIK refused by Sage'),
    ('sage-mock-leftco', 'Former employee', 'refused at sign-in: account disabled'),
]
DEMO_CUSTOMERS = {'QUIK': ['05-13615', '13-18996', '16-21380'], 'USBP': ['CUT001'], 'USBTST': ['CUT001']}

bp = Blueprint('orders', __name__, url_prefix=PREFIX or None)


def _token():
    return (request.cookies.get(COOKIE) or '').strip()


def _secure():
    return request.is_secure or request.headers.get('X-Forwarded-Proto', '') == 'https'


def _set_cookie(resp, value, hours=COOKIE_HOURS):
    resp.set_cookie(COOKIE, value, max_age=hours * 3600 if value else 0, httponly=True, secure=_secure(),
                    samesite='Lax', path=PREFIX or '/')
    return resp


def _signout(message=None):
    resp = make_response(redirect(url_for('orders.index', m=message) if message else url_for('orders.index')))
    return _set_cookie(resp, '', 0)


@bp.get('/healthz')
def healthz():
    return 'ok\n', 200, {'Content-Type': 'text/plain'}


@bp.post('/signin')
def signin():
    token = (request.form.get('token') or '').strip()
    if not token:
        return redirect(url_for('orders.index', m='Paste your Sage access token.'))
    try:
        mcp.call_tool(token, 'whoami', {})
    except mcp.AuthError:
        return redirect(url_for('orders.index', m='That token was not accepted by the Sage MCP server.'))
    except mcp.Unavailable as e:
        return render_template('signin.html', message=str(e), app_name=APP_NAME, handover=HANDOVER_URL), 503
    except mcp.ToolError as e:
        return redirect(url_for('orders.index', m='Sage declined this token: %s' % e))
    return _set_cookie(make_response(redirect(url_for('orders.index'))), token)


@bp.post('/signout')
def signout():
    return _signout()


@bp.get('/')
def index():
    token = _token()
    if not token:
        return render_template('signin.html', message=request.args.get('m'), app_name=APP_NAME, handover=HANDOVER_URL)
    try:
        me = mcp.call_tool(token, 'whoami', {})
    except mcp.AuthError:
        return _signout('Your token is no longer accepted. Sign in again.')
    except (mcp.Unavailable, mcp.ToolError) as e:
        return render_template('index.html', me=None, companies=[], error=str(e), humans=HUMANS,
                               app_name=APP_NAME, handover=HANDOVER_URL, q={}), 503

    companies = [{'code': code, **info} for code, info in (me.get('companies') or {}).items()]
    open_codes = [c['code'] for c in companies if c.get('open')]
    q = {'company': (request.args.get('company') or '').strip().upper(),
         'customer': (request.args.get('customer') or '').strip().upper(),
         'quotes': request.args.get('quotes') == '1'}
    if not q['company'] and open_codes:
        q['company'] = open_codes[0]

    result, error = None, None
    if q['customer']:
        try:
            result = mcp.call_tool(token, 'customer_order_history',
                                   {'company': q['company'], 'customer': q['customer'], 'include_quotes': q['quotes']})
        except mcp.AuthError:
            return _signout('Your token is no longer accepted. Sign in again.')
        except (mcp.ToolError, mcp.Unavailable) as e:
            error = str(e)
    return render_template('index.html', me=me, companies=companies, q=q, result=result, error=error,
                           humans=HUMANS, app_name=APP_NAME, handover=HANDOVER_URL)


def create_app():
    app = Flask(__name__, static_url_path=(PREFIX or '') + '/static')
    app.register_blueprint(bp)

    @app.context_processor
    def _demo():
        return {'demo_tokens': DEMO_TOKENS, 'demo_customers': DEMO_CUSTOMERS}

    @app.template_filter('label')
    def label(col):
        return str(col).replace('_', ' ')

    @app.template_filter('cell')
    def cell(v):
        if v is None:
            return '—'
        if isinstance(v, float):
            return '{:,.2f}'.format(v)
        if isinstance(v, bool):
            return 'yes' if v else 'no'
        return v

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8102')), debug=False)
