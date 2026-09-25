import json
import os
from pathlib import Path

GROUND_TRUTH = Path('/tests/expected_output.json')
OUTPUT_FILE = Path('/root/answers.json')

def load_json(path):
    with open(path) as f:
        return json.load(f)

def test_file_exists():
    assert OUTPUT_FILE.is_file()


def test_answers():
    gt = load_json(GROUND_TRUTH)
    answers = load_json(OUTPUT_FILE)
    for key in ['fund_query_current','quarter_current','fund_query_baseline','quarter_baseline']:
        assert answers[key] == gt[key]
    assert answers['top4_increased_cusips'] == gt['top4_increased_cusips']
    assert answers['top3_decreased_cusips'] == gt['top3_decreased_cusips']
    assert answers['new_positions_top2'] == gt['new_positions_top2']
