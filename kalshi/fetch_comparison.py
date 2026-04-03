"""Fetch Kalshi portfolio data for both accounts and produce comparison report."""
import sys, os, json, csv, time, base64
from datetime import datetime, timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import urllib.request, urllib.error

BASE_URL = 'https://api.elections.kalshi.com/trade-api/v2'

def load_key(path):
    with open(os.path.expanduser(path), 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def sign(private_key, method, path):
    ts = str(int(time.time() * 1000))
    msg = ts + method + path
    sig = private_key.sign(
        msg.encode('utf-8'),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )
    return ts, base64.b64encode(sig).decode('utf-8')

def request(api_key, private_key, method, endpoint):
    # Sign without query params
    path_no_qs = '/trade-api/v2' + endpoint.split('?')[0]
    ts, sig = sign(private_key, method, path_no_qs)
    url = BASE_URL + endpoint
    req = urllib.request.Request(url, method=method)
    req.add_header('KALSHI-ACCESS-KEY', api_key)
    req.add_header('KALSHI-ACCESS-SIGNATURE', sig)
    req.add_header('KALSHI-ACCESS-TIMESTAMP', ts)
    req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {'error': True, 'status': e.code, 'message': body}

# Account configs
accounts = {
    'baseline': {
        'api_key': 'bab58272-3610-43d8-a0cd-af6227d616c1',
        'key_path': '~/.kalshi/private_key.pem',
        'label': 'Baseline (Claude Intuition)',
        'starting_capital': 200.0,
    },
    'quant': {
        'api_key': 'd984b9cf-6567-424c-9b80-fa3e00de1813',
        'key_path': '~/.kalshi/private_key_quant.pem',
        'label': 'Quant Firm (Systematic)',
        'starting_capital': 200.0,
    },
}

results = {}
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

for name, acct in accounts.items():
    print(f"\n=== Fetching {acct['label']} ===")
    pk = load_key(acct['key_path'])
    api_key = acct['api_key']

    bal = request(api_key, pk, 'GET', '/portfolio/balance')
    pos = request(api_key, pk, 'GET', '/portfolio/positions')
    fills = request(api_key, pk, 'GET', '/portfolio/fills?limit=200')
    settlements = request(api_key, pk, 'GET', '/portfolio/settlements?limit=200')

    balance = float(bal.get('balance', 0)) / 100.0
    portfolio_value = float(bal.get('portfolio_value', 0)) / 100.0

    # Parse positions (new dollar format)
    active_positions = []
    for p in pos.get('market_positions', []):
        pos_qty = float(p.get('position_fp', p.get('position', 0)))
        exposure = float(p.get('market_exposure_dollars', p.get('market_exposure', 0) / 100.0))
        if pos_qty != 0 or exposure > 0:
            active_positions.append({
                'ticker': p.get('ticker', '?'),
                'position': pos_qty,
                'exposure': exposure,
                'realized_pnl': float(p.get('realized_pnl_dollars', 0)),
                'total_traded': float(p.get('total_traded_dollars', 0)),
                'fees': float(p.get('fees_paid_dollars', 0)),
                'resting_orders': p.get('resting_orders_count', 0),
            })

    # Parse event positions for realized P&L
    total_realized_pnl = 0
    total_fees = 0
    total_cost = 0
    wins = 0
    losses = 0
    for ep in pos.get('event_positions', []):
        rpnl = float(ep.get('realized_pnl_dollars', 0))
        total_realized_pnl += rpnl
        total_fees += float(ep.get('fees_paid_dollars', 0))
        total_cost += float(ep.get('total_cost_dollars', 0))

    # Count wins/losses from settlements
    for s in settlements.get('settlements', []):
        rev = float(s.get('revenue', 0)) / 100.0
        if rev > 0:
            wins += 1
        elif rev < 0:
            losses += 1

    total_value = balance + portfolio_value
    roi = ((total_value - acct['starting_capital']) / acct['starting_capital']) * 100
    drawdown = min(0, total_value - acct['starting_capital'])

    # Sort positions by exposure (biggest first)
    active_positions.sort(key=lambda x: abs(x['exposure']), reverse=True)

    results[name] = {
        'label': acct['label'],
        'balance': balance,
        'portfolio_value': portfolio_value,
        'total_value': total_value,
        'starting_capital': acct['starting_capital'],
        'roi': roi,
        'active_positions': active_positions,
        'num_active': len(active_positions),
        'realized_pnl': total_realized_pnl,
        'total_fees': total_fees,
        'total_cost': total_cost,
        'wins': wins,
        'losses': losses,
        'num_fills': len(fills.get('fills', [])),
        'num_settlements': len(settlements.get('settlements', [])),
        'drawdown': drawdown,
    }

    print(f"  Balance: ${balance:.2f}, Portfolio: ${portfolio_value:.2f}, Total: ${total_value:.2f}")
    print(f"  Active positions: {len(active_positions)}, Realized P&L: ${total_realized_pnl:.2f}, Fees: ${total_fees:.2f}")

    # Save snapshot CSV
    csv_path = f'/home/shaokai/Documents/projects/omar-data/kalshi/{name}_snapshot.csv'
    file_exists = os.path.exists(csv_path)
    with open(csv_path, 'a', newline='') as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(['timestamp', 'balance', 'portfolio_value', 'total_value', 'roi_pct', 'num_positions', 'realized_pnl', 'fees', 'fills', 'settlements'])
        w.writerow([now, f'{balance:.2f}', f'{portfolio_value:.2f}', f'{total_value:.2f}', f'{roi:.2f}',
                     len(active_positions), f'{total_realized_pnl:.2f}', f'{total_fees:.2f}',
                     len(fills.get('fills', [])), len(settlements.get('settlements', []))])

# Build report
b = results['baseline']
q = results['quant']

def pos_lines(positions, max_show=5):
    if not positions:
        return "  _No open positions_"
    lines = []
    for p in positions[:max_show]:
        side = "YES" if p['position'] > 0 else "NO"
        pnl_str = f", P&L ${p['realized_pnl']:.2f}" if p['realized_pnl'] != 0 else ""
        lines.append(f"  • `{p['ticker']}`: {abs(p['position']):.0f} {side} (${p['exposure']:.2f} exposed{pnl_str})")
    if len(positions) > max_show:
        lines.append(f"  _...and {len(positions) - max_show} more_")
    return "\n".join(lines)

leader = 'Baseline' if b['total_value'] > q['total_value'] else 'Quant Firm' if q['total_value'] > b['total_value'] else 'Tied'
gap = abs(b['total_value'] - q['total_value'])

report = f"""📊 *Kalshi Head-to-Head Report* — {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*{b['label']}*
  💰 Cash: ${b['balance']:.2f} | Portfolio: ${b['portfolio_value']:.2f}
  💵 *Total Value: ${b['total_value']:.2f}*
  📊 *ROI: {b['roi']:+.1f}%* (from ${b['starting_capital']:.0f})
  📋 Realized P&L: ${b['realized_pnl']:.2f} | Fees: ${b['total_fees']:.2f}
  🎯 Positions: {b['num_active']} open | {b['num_fills']} fills | {b['num_settlements']} settlements
*Top positions:*
{pos_lines(b['active_positions'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*{q['label']}*
  💰 Cash: ${q['balance']:.2f} | Portfolio: ${q['portfolio_value']:.2f}
  💵 *Total Value: ${q['total_value']:.2f}*
  📊 *ROI: {q['roi']:+.1f}%* (from ${q['starting_capital']:.0f})
  📋 Realized P&L: ${q['realized_pnl']:.2f} | Fees: ${q['total_fees']:.2f}
  🎯 Positions: {q['num_active']} open | {q['num_fills']} fills | {q['num_settlements']} settlements
*Top positions:*
{pos_lines(q['active_positions'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*⚔️ HEAD-TO-HEAD COMPARISON*
  🏆 Leader: *{leader}* by ${gap:.2f}
  Baseline: {b['roi']:+.1f}% ROI vs Quant: {q['roi']:+.1f}% ROI
  Baseline: {b['num_active']} positions vs Quant: {q['num_active']} positions
  Baseline: ${b['total_fees']:.2f} fees vs Quant: ${q['total_fees']:.2f} fees"""

if b['drawdown'] < 0 or q['drawdown'] < 0:
    report += f"\n  Drawdown: Baseline ${b['drawdown']:.2f} | Quant ${q['drawdown']:.2f}"

print("\n" + report)

# Save report
with open('/home/shaokai/Documents/projects/omar-data/kalshi/comparison_report.txt', 'w') as f:
    f.write(report)

# Output JSON for sending
print("\n__REPORT__")
print(report)
