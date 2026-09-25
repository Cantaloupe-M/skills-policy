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
    assert answers['issuer_query'] == gt['issuer_query']
    assert answers['quarter'] == gt['quarter']
    assert answers['cusip'] == gt['cusip']
    assert answers['top5_managers'] == gt['top5_managers']
    assert answers['top5_accessions'] == gt['top5_accessions']
