from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
issuer = tk.resolve_issuer('2025-q2', 'palantir')
rows = tk.top_holders('2025-q3', issuer['CUSIP'], 5)
write_json('/root/answers.json', {
    'issuer_query': 'palantir',
    'quarter': '2025-q3',
    'cusip': issuer['CUSIP'],
    'top5_managers': [row['manager_name'] for row in rows],
    'top5_accessions': [row['accession_number'] for row in rows],
})
