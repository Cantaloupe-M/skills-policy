from helper import FilingToolkit, write_json

tk = FilingToolkit('/root')
fund = tk.resolve_fund('2025-q3', 'elliott associates')
snap = tk.fund_snapshot('2025-q3', fund['ACCESSION_NUMBER'])
counts = snap['stock_rows'].copy()
counts['CLASS_NORM'] = counts['CLASS_NORM'].astype(str)
class_counts = counts.groupby('CLASS_NORM').size().reset_index(name='count').sort_values(['count', 'CLASS_NORM'], ascending=[False, True]).head(4)
write_json('/root/answers.json', {
    'fund_query': 'elliott associates',
    'quarter': '2025-q3',
    'aum_total': snap['aum'],
    'stock_row_count': int(snap['stock_rows'].shape[0]),
    'stock_cusip_count': int(snap['grouped'].shape[0]),
    'top_class_labels': class_counts['CLASS_NORM'].tolist(),
    'top_class_counts': class_counts['count'].astype(int).tolist(),
})
