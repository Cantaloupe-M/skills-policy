#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f /root/compute_capacity_schedule_input.csv ]; then
  DATA_ROOT="/root"
  OUTPUT_FILE="/root/Nimbus_Capacity_Reconciliation_4-25.xlsx"
else
  DATA_ROOT="${TASK_DIR}/environment"
  OUTPUT_FILE="${TASK_DIR}/Nimbus_Capacity_Reconciliation_4-25.xlsx"
fi

if [ -d "${TASK_DIR}/node_modules" ]; then
  export NODE_PATH="${TASK_DIR}/node_modules:${NODE_PATH:-}"
fi

cat > /tmp/build_amortization_workbook.js <<'NODE_SCRIPT'
const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");

const dataRoot = process.argv[2];
const outputFile = process.argv[3];

function readCsv(filePath) {
  const wb = XLSX.readFile(filePath, { raw: true });
  const ws = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(ws, { raw: true, defval: 0 });
}

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function str(v) {
  if (v === null || v === undefined) return "";
  return String(v);
}

function setCell(ws, addr, value, formula = null) {
  if (formula) {
    ws[addr] = { t: "n", f: formula, v: num(value) };
    return;
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    ws[addr] = { t: "n", v: value };
    return;
  }

  ws[addr] = { t: "s", v: str(value) };
}

function setRef(ws, rows, cols) {
  ws["!ref"] = `A1:${XLSX.utils.encode_cell({ r: rows - 1, c: cols - 1 })}`;
}

function sumBy(rows, key) {
  return rows.reduce((acc, row) => acc + num(row[key]), 0);
}

function buildDetailSheet(sheetName, title, rows, gl) {
  const ws = {};

  setCell(ws, "A1", "Nimbus Compute");
  setCell(ws, "A2", title);
  setCell(ws, "A3", "Account Activity from Jan to April 2025");

  setCell(ws, "A4", "Vendor");
  setCell(ws, "B4", "Beginning Balance");
  setCell(ws, "C4", "Jan");
  setCell(ws, "D4", "Jan");
  setCell(ws, "E4", "Jan");
  setCell(ws, "F4", "Feb");
  setCell(ws, "G4", "Feb");
  setCell(ws, "H4", "Feb");
  setCell(ws, "I4", "Mar");
  setCell(ws, "J4", "Mar");
  setCell(ws, "K4", "Mar");
  setCell(ws, "L4", "Apr");
  setCell(ws, "M4", "Apr");
  setCell(ws, "N4", "Apr");
  setCell(ws, "O4", "Amortization");

  setCell(ws, "B5", 45658);
  setCell(ws, "C5", "Debit Adds");
  setCell(ws, "D5", "Credit w/o's");
  setCell(ws, "E5", "End Balance");
  setCell(ws, "F5", "Debit Adds");
  setCell(ws, "G5", "Credit w/o's");
  setCell(ws, "H5", "End Balance");
  setCell(ws, "I5", "Debit Adds");
  setCell(ws, "J5", "Credit w/o's");
  setCell(ws, "K5", "End Balance");
  setCell(ws, "L5", "Debit Adds");
  setCell(ws, "M5", "Credit w/o's");
  setCell(ws, "N5", "End Balance");
  setCell(ws, "O5", "Months");
  setCell(ws, "P5", "Comments");
  setCell(ws, "Q5", "Acct#");

  const startRow = 6;
  rows.forEach((row, idx) => {
    const r = startRow + idx;
    setCell(ws, `A${r}`, str(row.vendor));
    setCell(ws, `B${r}`, num(row.beginning_balance));
    setCell(ws, `C${r}`, num(row.jan_adds));
    setCell(ws, `D${r}`, num(row.jan_amortization));
    setCell(ws, `E${r}`, num(row.jan_ending_balance));
    setCell(ws, `F${r}`, num(row.feb_adds));
    setCell(ws, `G${r}`, num(row.feb_amortization));
    setCell(ws, `H${r}`, num(row.feb_ending_balance));
    setCell(ws, `I${r}`, num(row.mar_adds));
    setCell(ws, `J${r}`, num(row.mar_amortization));
    setCell(ws, `K${r}`, num(row.mar_ending_balance));
    setCell(ws, `L${r}`, num(row.apr_adds));
    setCell(ws, `M${r}`, num(row.apr_amortization));
    setCell(ws, `N${r}`, num(row.apr_ending_balance));
    setCell(ws, `O${r}`, num(row.amortization_months));
    setCell(ws, `P${r}`, str(row.comments));
    setCell(ws, `Q${r}`, num(row.account_number));
  });

  const endDataRow = startRow + rows.length - 1;
  const totalsRow = endDataRow + 1;
  const endingRow = totalsRow + 1;
  const varianceRow = endingRow + 1;
  const glRow = varianceRow + 1;

  const sumCols = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"];
  const sums = {};
  const keyByCol = {
    B: "beginning_balance",
    C: "jan_adds",
    D: "jan_amortization",
    E: "jan_ending_balance",
    F: "feb_adds",
    G: "feb_amortization",
    H: "feb_ending_balance",
    I: "mar_adds",
    J: "mar_amortization",
    K: "mar_ending_balance",
    L: "apr_adds",
    M: "apr_amortization",
    N: "apr_ending_balance",
  };

  for (const col of sumCols) {
    sums[col] = sumBy(rows, keyByCol[col]);
  }

  const totalAdds = sums.C + sums.F + sums.I + sums.L;
  const totalAmort = sums.D + sums.G + sums.J + sums.M;
  const calcEndingE = sums.B + sums.C - sums.D;
  const calcEndingH = sums.E + sums.F - sums.G;
  const calcEndingK = sums.H + sums.I - sums.J;
  const calcEndingN = sums.K + sums.L - sums.M;

  setCell(ws, `A${totalsRow}`, "Month Totals");
  for (const col of sumCols) {
    setCell(ws, `${col}${totalsRow}`, sums[col], `SUM(${col}${startRow}:${col}${endDataRow})`);
  }
  setCell(ws, `O${totalsRow}`, totalAdds, `C${totalsRow}+F${totalsRow}+I${totalsRow}+L${totalsRow}`);
  setCell(ws, `P${totalsRow}`, "2025 Expenses");

  setCell(ws, `A${endingRow}`, "Ending Balance");
  setCell(ws, `E${endingRow}`, calcEndingE, `B${totalsRow}+C${totalsRow}-D${totalsRow}`);
  setCell(ws, `H${endingRow}`, calcEndingH, `E${totalsRow}+F${totalsRow}-G${totalsRow}`);
  setCell(ws, `K${endingRow}`, calcEndingK, `H${totalsRow}+I${totalsRow}-J${totalsRow}`);
  setCell(ws, `N${endingRow}`, calcEndingN, `K${totalsRow}+L${totalsRow}-M${totalsRow}`);
  setCell(ws, `O${endingRow}`, totalAmort, `D${totalsRow}+G${totalsRow}+J${totalsRow}+M${totalsRow}`);
  setCell(ws, `P${endingRow}`, "2025 Amortizations");

  setCell(ws, `A${varianceRow}`, "Variance");
  setCell(ws, `O${varianceRow}`, gl.apr - (totalAdds - totalAmort), `O${glRow}-N${glRow}`);
  setCell(ws, `P${varianceRow}`, "Variance");

  setCell(ws, `A${glRow}`, "GL Balance");
  setCell(ws, `E${glRow}`, num(gl.jan));
  setCell(ws, `H${glRow}`, num(gl.feb));
  setCell(ws, `K${glRow}`, num(gl.mar));
  setCell(ws, `N${glRow}`, num(gl.apr));
  setCell(ws, `O${glRow}`, totalAdds - totalAmort, `O${totalsRow}-O${endingRow}`);
  setCell(ws, `P${glRow}`, "Ending Balance");

  setRef(ws, glRow, 17);

  return {
    ws,
    totalsRow,
    endingRow,
    glRow,
    totalAdds,
    totalAmort,
    endingBalance: totalAdds - totalAmort,
  };
}

function buildSummarySheet(expInfo, insInfo) {
  const ws = {};
  setCell(ws, "A1", "Nimbus Compute");
  setCell(ws, "A2", "Capacity Summary Overview");
  setCell(ws, "A3", "For the period: 1/1/2025 - 4/30/2025");

  setCell(ws, "A5", "Description");
  setCell(ws, "B5", "Amount");

  setCell(ws, "A6", "Prepaid Expenses (Acct 8100)");
  setCell(ws, "A7", "PPD Expenses - 2025 Total");
  setCell(ws, "B7", expInfo.totalAdds, `'Compute Pool #8100'!O${expInfo.totalsRow}`);
  setCell(ws, "A8", "PPD Expenses - Amortized in 2025");
  setCell(ws, "B8", expInfo.totalAmort, `'Compute Pool #8100'!O${expInfo.endingRow}`);
  setCell(ws, "A9", "PPD Expenses - GL Balance - 4/30/2025");
  setCell(ws, "B9", expInfo.endingBalance, `'Compute Pool #8100'!O${expInfo.glRow}`);

  setCell(ws, "A11", "Prepaid Insurance (Acct 8200)");
  setCell(ws, "A12", "PPD Insurance - 2025 Total");
  setCell(ws, "B12", insInfo.totalAdds, `'Storage Pool #8200'!O${insInfo.totalsRow}`);
  setCell(ws, "A13", "PPD Insurance - Amortized in 2025");
  setCell(ws, "B13", insInfo.totalAmort, `'Storage Pool #8200'!O${insInfo.endingRow}`);
  setCell(ws, "A14", "PPD Insurance - 2025 GL Balance - 4/30/2025");
  setCell(ws, "B14", insInfo.endingBalance, `'Storage Pool #8200'!O${insInfo.glRow}`);

  setCell(ws, "A16", "Total Prepaid Balance - 4/30/2025");
  setCell(ws, "B16", expInfo.endingBalance + insInfo.endingBalance, "B9+B14");

  setRef(ws, 20, 5);
  return ws;
}

const glPath = path.join(dataRoot, "capacity_ledger_balances.json");
const expPath = path.join(dataRoot, "compute_capacity_schedule_input.csv");
const insPath = path.join(dataRoot, "storage_capacity_schedule_input.csv");

const gl = JSON.parse(fs.readFileSync(glPath, "utf8"));
const expRows = readCsv(expPath);
const insRows = readCsv(insPath);

const expDetail = buildDetailSheet(
  "Compute Pool #8100",
  "Compute Capacity Pool #8100 as of 4/30/25",
  expRows,
  gl.compute_pool_8100
);

const insDetail = buildDetailSheet(
  "Storage Pool #8200",
  "Storage Capacity Pool #8200 as of 4/30/25",
  insRows,
  gl.storage_pool_8200
);

const summary = buildSummarySheet(expDetail, insDetail);

const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, summary, "Capacity Summary");
XLSX.utils.book_append_sheet(wb, expDetail.ws, "Compute Pool #8100");
XLSX.utils.book_append_sheet(wb, insDetail.ws, "Storage Pool #8200");

XLSX.writeFile(wb, outputFile);
console.log(`Wrote ${outputFile}`);
NODE_SCRIPT

node /tmp/build_amortization_workbook.js "${DATA_ROOT}" "${OUTPUT_FILE}"
