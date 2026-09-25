import json
from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
report = json.load(open('/root/brief_template.json'))
report['report_date'] = '2025-q3'
for item in report['sections'][0]['items']:
    fund = tk.resolve_fund('2025-q3', item['fund_query'])
    snap = tk.fund_snapshot('2025-q3', fund['ACCESSION_NUMBER'])
    item['aum'] = snap['aum']
    item['stock_holdings'] = int(snap['stock_rows'].shape[0])
for item in report['sections'][1]['items']:
    issuer = tk.resolve_issuer('2025-q2', item['issuer_query'])
    item['top_manager'] = tk.top_holders('2025-q3', issuer['CUSIP'], 1)[0]['manager_name']
for item in report['sections'][2]['items']:
    cur = tk.resolve_fund('2025-q3', item['fund_query'])
    base = tk.resolve_fund('2025-q2', item['fund_query'])
    comp = tk.compare_fund('2025-q3', cur['ACCESSION_NUMBER'], '2025-q2', base['ACCESSION_NUMBER'])
    item['largest_buy_cusip'] = comp[comp['ABS_CHANGE'] > 0].head(1).iloc[0]['CUSIP']
    item['largest_sell_cusip'] = comp[comp['ABS_CHANGE'] < 0].sort_values(['ABS_CHANGE', 'CUSIP']).head(1).iloc[0]['CUSIP']
write_json('/root/answers.json', report)
