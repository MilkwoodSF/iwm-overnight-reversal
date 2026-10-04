"""IWM Overnight Reversal V1. Dry-run by default; paper orders require two gates."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from iwm_signal import THRESHOLD, load_config
from order_identity import order_id
from position_sizing import calculate_shares
from session_deadlines import moc_allowed
from telegram_notifier import send_message

ET = ZoneInfo('America/New_York')
PAPER = 'https://paper-api.alpaca.markets'
DATA = 'https://data.alpaca.markets'
STATE = Path('/root/.local/share/iwm-overnight-reversal/service_state.json')


def api(base, endpoint, headers, method='GET', payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + endpoint, data=data, headers={
        **headers, **({'Content-Type': 'application/json'} if data else {})
    }, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def find_order(cid, headers):
    path = '/v2/orders:by_client_order_id?' + urllib.parse.urlencode({'client_order_id': cid})
    try:
        return api(PAPER, path, headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def calendar(headers, start, end):
    path = '/v2/calendar?' + urllib.parse.urlencode({'start': start.isoformat(), 'end': end.isoformat()})
    return sorted(api(PAPER, path, headers), key=lambda s: s['date'])


def load_state():
    if not STATE.exists():
        return {'notified': [], 'alerts': []}
    state = json.loads(STATE.read_text())
    if not isinstance(state.get('notified'), list) or not isinstance(state.get('alerts'), list):
        raise RuntimeError('Invalid persistent notification state')
    return state


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = STATE.with_suffix('.tmp')
    with temp.open('w') as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump(state, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(STATE)


def notify_once(state, category, key, message, enabled):
    if key in state[category]:
        return
    if not enabled:
        print('DRY RUN NOTIFICATION:', message)
        return
    if not send_message(message):
        raise RuntimeError('Telegram delivery failed; notification remains pending')
    state[category].append(key)
    save_state(state)


def trading_headers(config):
    return {'APCA-API-KEY-ID': config['APCA_API_KEY_ID'],
            'APCA-API-SECRET-KEY': config['APCA_API_SECRET_KEY']}


def is_whole_positive(value):
    n = Decimal(str(value))
    return n > 0 and n == n.to_integral_value()


def reconcile_fills(headers, state, enabled):
    orders = api(PAPER, '/v2/orders?status=all&limit=500&direction=desc', headers)
    relevant = [o for o in orders if o.get('symbol') == 'IWM' and
                o.get('client_order_id', '').startswith('IWM-V1-') and
                o.get('status') == 'filled']
    for o in sorted(relevant, key=lambda x: x.get('filled_at') or ''):
        key = 'fill:' + o['id']
        if key in state['notified']:
            continue
        side = o['side'].upper()
        qty = o.get('filled_qty')
        price = o.get('filled_avg_price')
        account = api(PAPER, '/v2/account', headers)
        msg = (f'IWM {side} FILLED | {qty} shares @ ${price} | '
               f'Equity ${account["equity"]} | Cash ${account["cash"]} | '
               f'Buying power ${account["buying_power"]}')
        if side == 'SELL':
            sell_date = date.fromisoformat(o['client_order_id'][-8:-4] + '-' +
                                           o['client_order_id'][-4:-2] + '-' +
                                           o['client_order_id'][-2:])
            sessions = calendar(headers, sell_date - timedelta(days=12), sell_date)
            previous = [date.fromisoformat(s['date']) for s in sessions if s['date'] < sell_date.isoformat()]
            if previous:
                buy = find_order(order_id('BUY_MOC', previous[-1]), headers)
                if buy and buy.get('filled_avg_price') and price:
                    pnl = (Decimal(str(price)) - Decimal(str(buy['filled_avg_price']))) * Decimal(str(qty))
                    pct = (Decimal(str(price)) / Decimal(str(buy['filled_avg_price'])) - 1) * 100
                    msg += f' | Overnight P&L ${pnl:.2f} ({pct:+.3f}%)'
        notify_once(state, 'notified', key, msg, enabled)


def run(headers, state, enabled):
    now = datetime.now(ET)
    today = now.date()
    sessions = calendar(headers, today - timedelta(days=20), today + timedelta(days=10))
    account = api(PAPER, '/v2/account', headers)
    positions = api(PAPER, '/v2/positions', headers)
    open_orders = api(PAPER, '/v2/orders?status=open&limit=500', headers)
    held = [p for p in positions if p['symbol'] == 'IWM']
    outstanding = [o for o in open_orders if o['symbol'] == 'IWM']
    print('MODE:', 'PAPER SUBMISSION ENABLED' if enabled else 'DRY RUN')
    print('ET NOW:', now.isoformat())
    reconcile_fills(headers, state, enabled)

    if held:
        if account.get('trading_blocked') or account.get('account_blocked'):
            raise RuntimeError('Alpaca account blocked with open IWM position')
        if len(held) != 1 or not is_whole_positive(held[0]['qty']):
            raise RuntimeError('Unexpected IWM position quantity')
        all_orders = api(PAPER, '/v2/orders?status=all&limit=500&direction=desc', headers)
        buys = [o for o in all_orders if o.get('client_order_id', '').startswith('IWM-V1-BUY_MOC-')
                and o.get('symbol') == 'IWM' and Decimal(str(o.get('filled_qty') or '0')) > 0]
        if not buys:
            raise RuntimeError('IWM position has no identifiable strategy buy: manual review')
        buys.sort(key=lambda o: o.get('created_at') or '', reverse=True)
        buy = buys[0]
        buy_date = date.fromisoformat(buy['client_order_id'][-8:-4] + '-' +
                                     buy['client_order_id'][-4:-2] + '-' + buy['client_order_id'][-2:])
        future = [date.fromisoformat(s['date']) for s in sessions if s['date'] > buy_date.isoformat()]
        if not future:
            raise RuntimeError('Exit trading session unavailable')
        exit_date = future[0]
        cid = order_id('SELL_MOO', exit_date)
        existing = find_order(cid, headers)
        print('HELD:', held[0]['qty'], 'BUY:', buy_date, 'EXPECTED EXIT:', exit_date)
        if existing:
            status = existing['status']
            print('EXIT ORDER EXISTS:', status, cid)
            if status in ('rejected', 'canceled', 'expired'):
                raise RuntimeError(
                    'EXIT ORDER FAILED: open position requires manual recovery'
                )
            if status == 'filled':
                raise RuntimeError(
                    'SELL FILLED BUT POSITION STILL OPEN: reconciliation required'
                )
            if status == 'partially_filled':
                raise RuntimeError(
                    'PARTIAL SELL FILL: position reconciliation required'
                )
            if status not in (
                'new', 'accepted', 'pending_new',
                'accepted_for_bidding', 'pending_replace'
            ):
                raise RuntimeError(
                    'UNEXPECTED SELL STATUS: ' + str(status)
                )
            return
        if outstanding:
            raise RuntimeError('IWM position with outstanding order: manual reconciliation')
        if buy.get('status') != 'filled' or not buy.get('filled_at'):
            raise RuntimeError('Unresolved buy/partial fill: manual recovery required')
        fill_day = datetime.fromisoformat(buy['filled_at'].replace('Z', '+00:00')).astimezone(ET).date()
        if fill_day != buy_date or Decimal(str(buy['filled_qty'])) != Decimal(str(held[0]['qty'])):
            raise RuntimeError('Buy fill date or quantity does not match position')
        if today != exit_date:
            if today > exit_date:
                raise RuntimeError('MISSED MOO EXIT: manual recovery required')
            print('EXIT: awaiting next trading session')
            return
        if not time(4, 0) <= now.time() < time(9, 20):
            raise RuntimeError('MISSED/INVALID MOO WINDOW: manual recovery required')
        payload = {'symbol': 'IWM', 'qty': str(int(Decimal(str(held[0]['qty'])))),
                   'side': 'sell', 'type': 'market', 'time_in_force': 'opg',
                   'client_order_id': cid}
        if enabled:
            result = api(PAPER, '/v2/orders', headers, 'POST', payload)
            print('SELL ORDER SUBMITTED:', result['id'], result['status'])
        else:
            print('DRY RUN SELL:', payload)
        return

    if outstanding:
        print('ENTRY BLOCKED: existing outstanding IWM order')
        return
    if account.get('trading_blocked') or account.get('account_blocked'):
        raise RuntimeError('Alpaca account blocked')
    current = next((s for s in sessions if s['date'] == today.isoformat()), None)
    if current is None or not moc_allowed(current, now):
        print('ENTRY BLOCKED: outside permitted MOC window')
        return
    cid = order_id('BUY_MOC', today)
    if find_order(cid, headers) is not None:
        print('ENTRY BLOCKED: identifier already used')
        return
    previous = [s['date'] for s in sessions if s['date'] < today.isoformat()]
    if len(previous) < 2:
        raise RuntimeError('Insufficient preceding calendar sessions')
    expected = previous[-2:]
    path = '/v2/stocks/bars?' + urllib.parse.urlencode({
        'symbols': 'IWM', 'timeframe': '1Day', 'start': (today - timedelta(days=15)).isoformat(),
        'end': today.isoformat(), 'limit': 20, 'adjustment': 'raw', 'feed': 'sip'})
    bars = api(DATA, path, headers)['bars']['IWM']
    by_day = {b['t'][:10]: b for b in bars if b['t'][:10] < today.isoformat()}
    if any(d not in by_day for d in expected):
        raise RuntimeError('Missing required completed session bar')
    previous_close, latest_close = (Decimal(str(by_day[d]['c'])) for d in expected)
    prior_return = latest_close / previous_close - 1
    print('SIGNAL DATES:', expected, 'RETURN:', f'{prior_return:.6%}', 'THRESHOLD:', THRESHOLD)
    if prior_return > Decimal(str(THRESHOLD)):
        print('SIGNAL: NO TRADE')
        return
    sizing = calculate_shares(account['cash'], account['equity'], latest_close)
    if sizing['shares'] < 1:
        raise RuntimeError('Insufficient cash for whole-share purchase')
    payload = {'symbol': 'IWM', 'qty': str(sizing['shares']), 'side': 'buy',
               'type': 'market', 'time_in_force': 'cls', 'client_order_id': cid}
    if enabled:
        result = api(PAPER, '/v2/orders', headers, 'POST', payload)
        print('BUY ORDER SUBMITTED:', result['id'], result['status'])
    else:
        print('DRY RUN BUY:', payload, 'MAX BUDGET:', sizing['budget'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper-submit', action='store_true', help='Requires private env opt-in as second gate')
    args = parser.parse_args()
    config = load_config()
    enabled = args.paper_submit and config.get('IWM_PAPER_EXECUTION_ENABLED') == 'YES'
    if args.paper_submit and not enabled:
        sys.exit('BLOCKED: private IWM_PAPER_EXECUTION_ENABLED=YES is required')
    state = load_state()
    headers = trading_headers(config)
    try:
        run(headers, state, enabled)
    except Exception as exc:
        print('SERVICE EXCEPTION:', type(exc).__name__, str(exc))
        if enabled:
            key = 'exception:' + datetime.now(ET).date().isoformat() + ':' + str(exc)
            try:
                notify_once(state, 'alerts', key, 'IWM PAPER SERVICE EXCEPTION: ' + str(exc), True)
            except Exception as alert_exc:
                print('ALERT DELIVERY FAILED:', type(alert_exc).__name__)
        sys.exit(1)
    finally:
        print('ORDER SUBMISSION:', 'ENABLED BY TWO GATES' if enabled else 'DISABLED')


if __name__ == '__main__':
    main()
