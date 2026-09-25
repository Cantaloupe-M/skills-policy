from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
queries = ['amazon', 'palantir']
out = []
for fund_query in ['bridgewater associates', 'third point']:
    fund = tk.resolve_fund('2025-q3', fund_query)
    entry = {'fund_query': fund_query, 'quarter': '2025-q3', 'issuer_queries': []}
    for issuer_query in queries:
        issuer = tk.resolve_issuer('2025-q2', issuer_query)
        value = float(tk.info('2025-q3')[(tk.info('2025-q3')['ACCESSION_NUMBER'] == fund['ACCESSION_NUMBER']) & (tk.info('2025-q3')['CUSIP'] == issuer['CUSIP'])]['VALUE'].sum())
        entry['issuer_queries'].append({'issuer_query': issuer_query, 'cusip': issuer['CUSIP'], 'value': value})
    out.append(entry)
write_json('/root/answers.json', {'manager_issuer_grid': out})
