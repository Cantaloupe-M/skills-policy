from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
cur = tk.resolve_fund('2025-q3', 'bridgewater associates')
base = tk.resolve_fund('2025-q2', 'bridgewater associates')
comp = tk.compare_fund('2025-q3', cur['ACCESSION_NUMBER'], '2025-q2', base['ACCESSION_NUMBER'])
write_json('/root/answers.json', {
    'fund_query_current': 'bridgewater associates',
    'quarter_current': '2025-q3',
    'fund_query_baseline': 'bridgewater associates',
    'quarter_baseline': '2025-q2',
    'top4_increased_cusips': comp[comp['ABS_CHANGE'] > 0].head(4)['CUSIP'].tolist(),
    'top3_decreased_cusips': comp[comp['ABS_CHANGE'] < 0].sort_values(['ABS_CHANGE', 'CUSIP']).head(3)['CUSIP'].tolist(),
    'new_positions_top2': comp[(comp['VALUE_BASE'] == 0) & (comp['VALUE_CUR'] > 0)].head(2)['CUSIP'].tolist(),
})
