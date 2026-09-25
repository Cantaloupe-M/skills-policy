import json
from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
alerts = json.load(open('/root/alerts_input.json'))['alerts'] if isinstance(json.load(open('/root/alerts_input.json')), dict) and 'alerts' in json.load(open('/root/alerts_input.json')) else json.load(open('/root/alerts_input.json'))['alerts']
seen = {'issuer_top_holders': set(), 'fund_change': set()}
out = {'issuer_top_holders': [], 'fund_change': []}
for alert in alerts:
    if alert.get('type') == 'issuer_top_holders':
        key = (alert['issuer_query'], alert['quarter'])
        if key in seen['issuer_top_holders']:
            continue
        seen['issuer_top_holders'].add(key)
        issuer = tk.resolve_issuer('2025-q2', alert['issuer_query'])
        rows = tk.top_holders('2025-q3', issuer['CUSIP'], 3)
        out['issuer_top_holders'].append({'issuer_query': alert['issuer_query'], 'quarter': alert['quarter'], 'manager_names': [r['manager_name'] for r in rows]})
    elif alert.get('type') == 'fund_change':
        key = (alert['fund_query_current'], alert['quarter_current'], alert['fund_query_baseline'], alert['quarter_baseline'])
        if key in seen['fund_change']:
            continue
        seen['fund_change'].add(key)
        cur = tk.resolve_fund(alert['quarter_current'], alert['fund_query_current'])
        base = tk.resolve_fund(alert['quarter_baseline'], alert['fund_query_baseline'])
        comp = tk.compare_fund(alert['quarter_current'], cur['ACCESSION_NUMBER'], alert['quarter_baseline'], base['ACCESSION_NUMBER'])
        out['fund_change'].append({'fund_query_current': alert['fund_query_current'], 'quarter_current': alert['quarter_current'], 'fund_query_baseline': alert['fund_query_baseline'], 'quarter_baseline': alert['quarter_baseline'], 'largest_buy_cusip': comp[comp['ABS_CHANGE'] > 0].head(1).iloc[0]['CUSIP']})
write_json('/root/answers.json', out)
