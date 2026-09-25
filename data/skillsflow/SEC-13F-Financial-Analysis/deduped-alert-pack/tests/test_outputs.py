import json
from pathlib import Path
GROUND_TRUTH = Path('/tests/expected_output.json')
OUTPUT_FILE = Path('/root/answers.json')

def load_json(path):
    with open(path) as f:
        return json.load(f)

def test_file_exists():
    assert OUTPUT_FILE.is_file()


def test_answers():
    assert load_json(OUTPUT_FILE) == load_json(GROUND_TRUTH)
