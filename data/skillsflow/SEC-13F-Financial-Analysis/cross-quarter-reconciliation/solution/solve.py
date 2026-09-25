from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')

def pair_payload(query):
    cur = tk.resolve_fund('2025-q3', query)
    base = tk.resolve_fund('2025-q2', query)
    comp = tk.compare_fund('2025-q3', cur['ACCESSION_NUMBER'], '2025-q2', base['ACCESSION_NUMBER'])
    return {
        'fund_query_current': query,
        'quarter_current': '2025-q3',
        'fund_query_baseline': query,
        'quarter_baseline': '2025-q2',
        'largest_buy_cusip': comp[comp['ABS_CHANGE'] > 0].head(1).iloc[0]['CUSIP'],
        'largest_sell_cusip': comp[comp['ABS_CHANGE'] < 0].sort_values(['ABS_CHANGE', 'CUSIP']).head(1).iloc[0]['CUSIP'],
    }

def issuer_payload(query):
    issuer = tk.resolve_issuer('2025-q2', query)
    rows = tk.top_holders('2025-q3', issuer['CUSIP'], 2)
    return {
        'issuer_query': query,
        'quarter': '2025-q3',
        'top2_manager_names': [row['manager_name'] for row in rows],
    }

snap_fund = tk.resolve_fund('2025-q3', 'scion asset management')
snap = tk.fund_snapshot('2025-q3', snap_fund['ACCESSION_NUMBER'])
write_json('/root/answers.json', {
    'comparison_pairs': [pair_payload('third point'), pair_payload('tiger global')],
    'issuer_checks': [issuer_payload('microsoft'), issuer_payload('meta platforms')],
    'snapshot_check': {
        'fund_query': 'scion asset management',
        'quarter': '2025-q3',
        'stock_holdings': snap['stock_holdings'],
    },
})
