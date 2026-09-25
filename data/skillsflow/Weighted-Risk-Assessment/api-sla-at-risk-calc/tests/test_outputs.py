import csv
import glob
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

from openpyxl import load_workbook

EXCEL_FILE = Path("/root/output/result.xlsx")
CSV_PATTERN = "/root/output/sheet.csv.*"
COLUMNS = ["H", "I", "J", "K", "L"]
TOLERANCE = 0.02
YELLOW_RGBS = {"00FFF2CC", "FFF2CC", "00FFF2CC"}

_recalculated_path = None


def _has_cached_values(path: Path) -> bool:
    """Check if the workbook has cached values for formula cells."""
    wb = load_workbook(path, data_only=True)
    ws = wb["Task"]
    for ref in ["H12", "H35", "H50"]:
        val = ws[ref].value
        if not isinstance(val, (int, float)):
            wb.close()
            return False
    wb.close()
    return True


def _recalculate_with_ssconvert(src: Path) -> Path:
    """Use ssconvert to recalculate formulas and write to a temp file."""
    tmp = Path(tempfile.mkdtemp()) / "recalculated.xlsx"
    subprocess.run(
        ["ssconvert", str(src), str(tmp), "--recalculate"],
        capture_output=True,
        check=True,
    )
    return tmp


def _get_reliable_workbook_path() -> Path:
    """Return path to workbook with cached values, recalculating if needed."""
    global _recalculated_path
    if _recalculated_path is not None and _recalculated_path.exists():
        return _recalculated_path
    if _has_cached_values(EXCEL_FILE):
        return EXCEL_FILE
    _recalculated_path = _recalculate_with_ssconvert(EXCEL_FILE)
    return _recalculated_path

EXPECTED_TOP = {"12": [418.2, 430.6, 443.9, 457.1, 470.8], "13": [362.1, 371.4, 380.6, 390.0, 399.7], "14": [335.0, 343.2, 351.0, 358.7, 366.0], "15": [281.0, 287.4, 294.0, 300.6, 307.1], "16": [390.5, 401.3, 412.1, 422.5, 432.8], "17": [248.2, 255.1, 262.5, 270.2, 278.3]}
EXPECTED_MID = {"19": [405.6, 419.4, 433.7, 448.4, 463.5], "20": [369.4, 378.0, 386.3, 394.1, 401.6], "21": [344.8, 351.6, 358.1, 364.3, 370.2], "22": [287.4, 293.2, 299.0, 304.8, 310.5], "23": [370.0, 382.0, 394.4, 407.0, 420.0], "24": [252.5, 259.9, 267.6, 275.8, 284.4]}
EXPECTED_BASE = {"26": [520.0, 536.0, 552.0, 568.0, 584.0], "27": [470.0, 484.0, 498.0, 512.0, 526.0], "28": [430.0, 443.0, 456.0, 469.0, 482.0], "29": [360.0, 371.0, 382.0, 393.0, 404.0], "30": [505.0, 521.0, 537.0, 553.0, 569.0], "31": [315.0, 325.0, 335.0, 345.0, 355.0]}
EXPECTED_NET = {"35": [2.4230769230769167, 2.0895522388059784, 1.8478260869565197, 1.5316901408450785, 1.250000000000002], "36": [-1.5531914893616925, -1.3636363636363682, -1.1445783132530096, -0.8007812500000044, -0.3612167300380293], "37": [-2.279069767441863, -1.8961625282167118, -1.557017543859654, -1.1940298507462734, -0.8713692946058067], "38": [-1.7777777777777715, -1.5633423180593025, -1.3089005235602094, -1.068702290076333, -0.8415841584158359], "39": [4.0594059405940595, 3.704414587332056, 3.2960893854748687, 2.802893309222423, 2.24956063268893], "40": [-1.3650793650793687, -1.4769230769230717, -1.5223880597014994, -1.6231884057971082, -1.71830985915492]}
EXPECTED_STATS = {"42": [-2.279069767441863, -1.8961625282167118, -1.557017543859654, -1.6231884057971082, -1.71830985915492], "43": [4.0594059405940595, 3.704414587332056, 3.2960893854748687, 2.802893309222423, 2.24956063268893], "44": [-1.4591354272205306, -1.42027972027972, -1.2267394184066096, -0.9347417700381687, -0.6014004442269326], "45": [-0.08210592266495327, -0.08434957678290327, -0.06482816132383067, -0.05868639109203629, -0.04881990158760999], "46": [-1.7216312056737517, -1.5417375077752449, -1.4690161756661768, -1.1626979605787884, -0.863923010558314], "47": [1.4760378510378453, 1.226255088195392, 1.099724986904137, 0.9485722931338079, 0.8471958174904941]}
EXPECTED_WEIGHTED = [0.2038461538461543, 0.18283582089552264, 0.1811594202898551, 0.16549295774647835, 0.15410958904109787]

_csv_cache = None


def workbook(data_only=True):
    path = _get_reliable_workbook_path() if data_only else EXCEL_FILE
    return load_workbook(path, data_only=data_only)


def task_sheet(wb):
    return wb["Task"]


def find_task_csv():
    files = sorted(glob.glob(CSV_PATTERN))
    if not files:
        return None
    wb = workbook(data_only=False)
    idx = wb.sheetnames.index("Task")
    wb.close()
    candidate = f"/root/output/sheet.csv.{idx}"
    return candidate if Path(candidate).exists() else files[0]


def load_csv():
    global _csv_cache
    if _csv_cache is not None:
        return _csv_cache
    _csv_cache = {}
    csv_file = find_task_csv()
    if csv_file is None:
        return _csv_cache
    with open(csv_file, encoding="utf-8", errors="ignore") as handle:
        reader = csv.reader(handle)
        for row_idx, row in enumerate(reader, start=1):
            for col_idx, value in enumerate(row, start=1):
                ref = f"{chr(ord('A') + col_idx - 1)}{row_idx}"
                if value in (None, ""):
                    _csv_cache[ref] = None
                    continue
                try:
                    _csv_cache[ref] = float(value)
                except ValueError:
                    _csv_cache[ref] = value
    return _csv_cache


def value(ws, ref):
    direct = ws[ref].value
    if isinstance(direct, (int, float)):
        return float(direct)
    cached = load_csv().get(ref)
    if isinstance(cached, (int, float)):
        return float(cached)
    return direct


def assert_matrix(ws, expected_map, label):
    errors = []
    for row, expected_values in expected_map.items():
        for idx, col in enumerate(COLUMNS):
            ref = f"{col}{row}"
            actual = value(ws, ref)
            expected = expected_values[idx]
            if not isinstance(actual, (int, float)) or abs(actual - expected) > TOLERANCE:
                errors.append(f"{ref}: expected {expected}, got {actual}")
    assert not errors, f"{label} mismatches:\n" + "\n".join(errors)


def test_file_and_sheet_structure():
    assert EXCEL_FILE.exists(), f"Missing output workbook: {EXCEL_FILE}"
    wb = workbook()
    assert wb.sheetnames == ["Task", "Data"]
    ws = task_sheet(wb)
    assert ws["A1"].value is not None
    wb.close()


def test_lookup_blocks():
    wb = workbook()
    ws = task_sheet(wb)
    assert_matrix(ws, EXPECTED_TOP, "top block")
    assert_matrix(ws, EXPECTED_MID, "middle block")
    assert_matrix(ws, EXPECTED_BASE, "base block")
    wb.close()


def test_derived_values_and_stats():
    wb = workbook()
    ws = task_sheet(wb)
    assert_matrix(ws, EXPECTED_NET, "net metric")
    assert_matrix(ws, EXPECTED_STATS, "statistics")
    weighted_errors = []
    for idx, col in enumerate(COLUMNS):
        ref = f"{col}50"
        actual = value(ws, ref)
        expected = EXPECTED_WEIGHTED[idx]
        if not isinstance(actual, (int, float)) or abs(actual - expected) > TOLERANCE:
            weighted_errors.append(f"{ref}: expected {expected}, got {actual}")
    wb.close()
    assert not weighted_errors, "weighted mean mismatches:\n" + "\n".join(weighted_errors)


def test_formulas_present_in_editable_ranges():
    wb = workbook(data_only=False)
    ws = task_sheet(wb)
    missing = []
    for row in list(range(12, 18)) + list(range(19, 25)) + list(range(26, 32)) + list(range(35, 41)) + [42, 43, 44, 45, 46, 47, 50]:
        for col in COLUMNS:
            ref = f"{col}{row}"
            cell_value = ws[ref].value
            if not (isinstance(cell_value, str) and cell_value.startswith("=")):
                missing.append(f"{ref}: {cell_value}")
    for col in COLUMNS:
        formula = ws[f"{col}50"].value
        if "SUMPRODUCT" not in str(formula).upper():
            missing.append(f"{col}50 missing SUMPRODUCT: {formula}")
    wb.close()
    assert not missing, "Missing formulas:\n" + "\n".join(missing)


def test_template_formatting_preserved():
    wb = workbook(data_only=False)
    ws = task_sheet(wb)
    for ref in ["H12", "L31", "H35", "L47", "H50"]:
        fill = ws[ref].fill
        rgb = getattr(fill.fgColor, "rgb", None)
        assert fill.patternType == "solid", f"{ref} lost yellow fill"
        assert rgb in YELLOW_RGBS, f"{ref} fill changed: {rgb}"
    wb.close()


def test_no_excel_errors_or_macros():
    errors = []
    csv_values = load_csv()
    for ref, value_ in csv_values.items():
        if isinstance(value_, str) and any(token in value_ for token in ["#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NULL!", "#NUM!", "#N/A"]):
            errors.append(f"{ref}: {value_}")
    with zipfile.ZipFile(EXCEL_FILE, "r") as archive:
        macros = [name for name in archive.namelist() if "vbaProject" in name or name.endswith(".bin")]
    if macros:
        errors.append(f"Macros found: {macros}")
    assert not errors, "Validation errors:\n" + "\n".join(errors)
