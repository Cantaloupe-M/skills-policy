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
    assert answers['comparison_pairs'] == gt['comparison_pairs']
    assert answers['issuer_checks'] == gt['issuer_checks']
    assert answers['snapshot_check'] == gt['snapshot_check']
