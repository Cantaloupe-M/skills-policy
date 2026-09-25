import pytest
import openpyxl
import os

OUTPUT_FILE = '/root/Faculty_Termload_Compensation.xlsx'
SRC_FILE = '/root/faculty_termload_packet.xlsx'

class TestSheetStructure:
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_FILE), f"Output file not found: {OUTPUT_FILE}"

    def test_sheet_names(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        expected = ['Summary', 'Assumptions', 'Roster', 'Calculations --->',
                    'EE Calcs (Current)', 'EE Calcs (Yr+1)', 'EE Calcs (Yr+2)']
        assert wb.sheetnames == expected, f"Expected {expected}, got {wb.sheetnames}"

    def test_named_ranges_count(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        assert len(wb.defined_names) >= 50, f"Expected >= 50 named ranges, got {len(wb.defined_names)}"

    def test_summary_title(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb['Summary']
        assert ws['B1'].value == 'Lakeshore State University - Faculty Compensation'

    def test_summary_base_salary(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb['Summary']
        assert ws['C5'].value == 62000, f"Expected C5=62000, got {ws['C5'].value}"
        assert ws['D5'].value == '=C5*1.03', f"Expected D5='=C5*1.03', got {ws['D5'].value}"

    def test_summary_comp_rows(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb['Summary']
        assert ws['B26'].value is not None, "Summary row 26 should have component label"
        assert ws['B32'].value is not None, "Summary row 32 should have component label"
        assert ws['B33'].value is not None, "Summary row 33 should have total label"

    def test_ee_calcs_row_count(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb['EE Calcs (Current)']
        # 75 faculty rows + 1 totals row = 79
        data_rows = sum(1 for r in ws.iter_rows(min_row=4, max_row=200, min_col=2, max_col=2) if r[0].value is not None)
        assert data_rows >= 75, f"Expected >=75 data rows, got {data_rows}"

    def test_quarterly_totals_row(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb['EE Calcs (Current)']
        # Row 79 should have quarterly totals
        # Check H79 (first data column)
        h79 = ws.cell(row=79, column=8).value
        assert h79 is not None, "Row 79 (quarterly totals) should exist in EE Calcs"

    def test_roster_migrated(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb['Roster']
        # Should have at least 75 faculty entries
        count = sum(1 for r in ws.iter_rows(min_row=5, max_row=200, min_col=2, max_col=2) if r[0].value is not None)
        assert count >= 75, f"Expected >=75 roster entries, got {count}"

    def test_ee_calcs_yoy_service_progression(self):
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws1 = wb['EE Calcs (Current)']
        ws2 = wb['EE Calcs (Yr+1)']
        # Yrs of service should be +1 in Yr+1
        for r in range(4, 79):
            v1 = ws1.cell(row=r, column=5).value
            v2 = ws2.cell(row=r, column=5).value
            if v1 is not None and v2 is not None:
                assert v2 == v1 + 1, f"Row {r}: Yr+1 service should be +1 (got {v1}->{v2})"
                break  # Just check first valid row
