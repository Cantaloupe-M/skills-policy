import csv
import json
from pathlib import Path


ANALYSIS_PATH = Path("/root/refill_analysis.json")
SUMMARY_PATH = Path("/root/refill_summary.md")
WHOLESALE_PATH = Path("/root/wholesale_price.csv")
VIAL_PATH = Path("/root/vial_price.csv")
REIMBURSEMENT_PATH = Path("/root/reimbursement.csv")

PATIENTS = 300
FILLS_90 = 4
FILLS_100 = 3
TABLETS_90 = 90
TABLETS_100 = 100
THRESHOLD = 16000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_inputs():
    wholesale = []
    with WHOLESALE_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wholesale.append(
                {
                    "medication": row["medication"],
                    "price_per_1000_tablets_usd": float(row["price_per_1000_tablets_usd"]),
                    "vial_size_drams": int(row["vial_size_drams"]),
                }
            )

    vial_prices = {}
    with VIAL_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vial_prices[int(row["vial_size_drams"])] = float(row["vial_price_usd"])

    reimbursements = {}
    with REIMBURSEMENT_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reimbursements[row["medication"]] = float(row["reimbursement_per_fill_300_patients_usd"])

    return wholesale, vial_prices, reimbursements


def expected_metrics():
    wholesale, vial_prices, reimbursements = load_inputs()
    expected = {}

    for row in wholesale:
        med = row["medication"]
        price_per_1000 = row["price_per_1000_tablets_usd"]
        vial_size = row["vial_size_drams"]
        vial_price = vial_prices[vial_size]
        reimbursement = reimbursements[med]

        annual_drug_cost_90 = price_per_1000 * (PATIENTS * TABLETS_90 * FILLS_90 / 1000.0)
        annual_drug_cost_100 = price_per_1000 * (PATIENTS * TABLETS_100 * FILLS_100 / 1000.0)
        annual_supply_cost_90 = vial_price * PATIENTS * FILLS_90
        annual_supply_cost_100 = vial_price * PATIENTS * FILLS_100
        annual_reimbursement_90 = reimbursement * FILLS_90
        annual_reimbursement_100 = reimbursement * FILLS_100
        annual_revenue_90 = annual_reimbursement_90 - annual_drug_cost_90 - annual_supply_cost_90
        annual_revenue_100 = annual_reimbursement_100 - annual_drug_cost_100 - annual_supply_cost_100
        annual_difference = annual_revenue_100 - annual_revenue_90

        expected[med] = {
            "medication": med,
            "price_per_1000_tablets_usd": round2(price_per_1000),
            "vial_size_drams": vial_size,
            "vial_price_usd": round2(vial_price),
            "reimbursement_per_fill_300_patients_usd": round2(reimbursement),
            "annual_drug_cost_90_day_usd": round2(annual_drug_cost_90),
            "annual_drug_cost_100_day_usd": round2(annual_drug_cost_100),
            "annual_supply_cost_90_day_usd": round2(annual_supply_cost_90),
            "annual_supply_cost_100_day_usd": round2(annual_supply_cost_100),
            "annual_reimbursement_90_day_usd": round2(annual_reimbursement_90),
            "annual_reimbursement_100_day_usd": round2(annual_reimbursement_100),
            "annual_revenue_90_day_usd": round2(annual_revenue_90),
            "annual_revenue_100_day_usd": round2(annual_revenue_100),
            "annual_revenue_difference_100_minus_90_usd": round2(annual_difference),
        }
    return expected


def load_output():
    assert ANALYSIS_PATH.exists(), f"Missing output file: {ANALYSIS_PATH}"
    with ANALYSIS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def test_required_output_files_exist():
    assert ANALYSIS_PATH.exists(), f"Missing {ANALYSIS_PATH}"
    assert SUMMARY_PATH.exists(), f"Missing {SUMMARY_PATH}"


def test_output_schema_and_assumptions():
    data = load_output()
    assert isinstance(data, dict)
    for key in ("assumptions", "medications", "totals", "recommendation"):
        assert key in data, f"Missing top-level key: {key}"

    assumptions = data["assumptions"]
    assert assumptions["patients_per_medication"] == PATIENTS
    assert assumptions["fills_per_year_90_day"] == FILLS_90
    assert assumptions["fills_per_year_100_day"] == FILLS_100
    assert assumptions["tablets_per_fill_90_day"] == TABLETS_90
    assert assumptions["tablets_per_fill_100_day"] == TABLETS_100
    assert assumptions["switch_threshold_usd"] == THRESHOLD


def test_all_medications_present_and_unique():
    data = load_output()
    meds = data["medications"]
    assert isinstance(meds, list), "medications must be a list"
    assert len(meds) == 10, f"Expected 10 medications, got {len(meds)}"

    names = [m["medication"] for m in meds]
    assert len(set(names)) == 10, "Medication names must be unique"

    expected_names = set(expected_metrics().keys())
    assert set(names) == expected_names


def test_per_medication_calculations():
    data = load_output()
    actual = {row["medication"]: row for row in data["medications"]}
    expected = expected_metrics()

    required_fields = [
        "medication",
        "price_per_1000_tablets_usd",
        "vial_size_drams",
        "vial_price_usd",
        "reimbursement_per_fill_300_patients_usd",
        "annual_drug_cost_90_day_usd",
        "annual_drug_cost_100_day_usd",
        "annual_supply_cost_90_day_usd",
        "annual_supply_cost_100_day_usd",
        "annual_reimbursement_90_day_usd",
        "annual_reimbursement_100_day_usd",
        "annual_revenue_90_day_usd",
        "annual_revenue_100_day_usd",
        "annual_revenue_difference_100_minus_90_usd",
    ]

    for med, exp in expected.items():
        assert med in actual, f"Missing medication in output: {med}"
        row = actual[med]

        for field in required_fields:
            assert field in row, f"{med}: missing field {field}"

        assert row["vial_size_drams"] == exp["vial_size_drams"]

        numeric_fields = [f for f in required_fields if f not in ("medication", "vial_size_drams")]
        for field in numeric_fields:
            assert close(row[field], exp[field]), (
                f"{med} {field} mismatch: actual={row[field]} expected={exp[field]}"
            )


def test_totals_consistent_with_rows():
    data = load_output()
    meds = data["medications"]
    totals = data["totals"]

    sum_90 = round2(sum(m["annual_revenue_90_day_usd"] for m in meds))
    sum_100 = round2(sum(m["annual_revenue_100_day_usd"] for m in meds))
    sum_diff = round2(sum(m["annual_revenue_difference_100_minus_90_usd"] for m in meds))
    abs_diff = round2(abs(sum_diff))

    assert close(totals["total_annual_revenue_90_day_usd"], sum_90)
    assert close(totals["total_annual_revenue_100_day_usd"], sum_100)
    assert close(totals["total_annual_revenue_difference_100_minus_90_usd"], sum_diff)
    assert close(totals["absolute_total_revenue_difference_usd"], abs_diff)


def test_decision_rule_applied_correctly():
    data = load_output()
    totals = data["totals"]
    recommendation = data["recommendation"]

    absolute_diff = totals["absolute_total_revenue_difference_usd"]
    expected_decision = "switch_to_100_day" if absolute_diff < THRESHOLD else "keep_90_day"

    assert recommendation["decision"] in {"switch_to_100_day", "keep_90_day"}
    assert recommendation["decision"] == expected_decision
    assert isinstance(recommendation["justification"], str)
    assert recommendation["justification"].strip(), "justification cannot be empty"


def test_summary_contains_key_outputs():
    data = load_output()
    summary = SUMMARY_PATH.read_text(encoding="utf-8")
    lines = [line for line in summary.strip().splitlines() if line.strip()]

    assert 4 <= len(lines) <= 8, "Summary must be 4 to 8 non-empty lines"
    assert "Decision:" in summary
    decision = data["recommendation"]["decision"]
    normalized = decision.replace('_', ' ').lower()
    assert (decision in summary) or (normalized in summary.lower()), f"Decision '{decision}' (or '{normalized}') not found in summary"

    totals = data["totals"]
    for value in (
        totals["total_annual_revenue_90_day_usd"],
        totals["total_annual_revenue_100_day_usd"],
        totals["absolute_total_revenue_difference_usd"],
    ):
        formatted = f"{value:,.2f}"
        assert formatted in summary, f"Summary missing value {formatted}"
