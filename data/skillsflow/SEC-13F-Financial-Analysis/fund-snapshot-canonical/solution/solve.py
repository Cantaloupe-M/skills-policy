from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
fund = tk.resolve_fund('2025-q3', 'renaissance technologies')
snap = tk.fund_snapshot('2025-q3', fund['ACCESSION_NUMBER'])
top3 = snap['grouped'].sort_values(['VALUE', 'CUSIP'], ascending=[False, True]).head(3)['CUSIP'].tolist()
write_json('/root/answers.json', {
    'fund_query': 'renaissance technologies',
    'quarter': '2025-q3',
    'matched_manager': str(fund['FILINGMANAGER_NAME']),
    'accession_number': str(fund['ACCESSION_NUMBER']),
    'aum': snap['aum'],
    'stock_holdings': snap['stock_holdings'],
    'stock_aum': snap['stock_aum'],
    'top3_cusips_by_value': top3,
})
