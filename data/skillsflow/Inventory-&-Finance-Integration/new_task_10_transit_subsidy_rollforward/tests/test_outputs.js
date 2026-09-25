const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");

function fail(message) {
  console.error(`FAIL: ${message}`);
  process.exit(1);
}

function ok(message) {
  console.log(`PASS: ${message}`);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function text(v) {
  if (v === null || v === undefined) return "";
  return String(v).trim();
}

function near(a, b, tolerance = 0.01) {
  return Math.abs(num(a) - num(b)) <= tolerance;
}

function normalizeFormula(formula) {
  return String(formula || "")
    .replace(/\$/g, "")
    .replace(/\s+/g, "")
    .toUpperCase();
}

function cell(ws, addr) {
  return ws[addr] || {};
}

function value(ws, addr) {
  return cell(ws, addr).v;
}

function formula(ws, addr) {
  return cell(ws, addr).f || "";
}

function readCsv(filePath) {
  const wb = XLSX.readFile(filePath, { raw: true });
  const ws = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(ws, { raw: true, defval: 0 });
}

const localTaskDir = path.resolve(__dirname, "..");
const runningInHarbor = fs.existsSync("/root/bus_pass_schedule_input.csv");

const dataRoot = runningInHarbor ? "/root" : path.join(localTaskDir, "environment");
const outputFile = runningInHarbor
  ? "/root/MetroLink_Pass_Liability_4-25.xlsx"
  : path.join(localTaskDir, "MetroLink_Pass_Liability_4-25.xlsx");

assert(fs.existsSync(outputFile), `Workbook not found: ${outputFile}`);
ok("Output workbook exists");

const workbook = XLSX.readFile(outputFile, { cellFormula: true, raw: true });
const expectedSheets = ["Transit Summary", "Bus Program #4310", "Rail Program #4320"];
assert(
  JSON.stringify(workbook.SheetNames) === JSON.stringify(expectedSheets),
  `Sheet names/order must be exactly ${expectedSheets.join(", ")}`
);
ok("Sheet names and order are correct");

const expenseRows = readCsv(path.join(dataRoot, "bus_pass_schedule_input.csv"));
const insuranceRows = readCsv(path.join(dataRoot, "rail_pass_schedule_input.csv"));
const gl = JSON.parse(fs.readFileSync(path.join(dataRoot, "fare_liability_balances.json"), "utf8"));

function validateDetailSheet(sheetName, rows, glValues, titleContains) {
  const ws = workbook.Sheets[sheetName];
  assert(ws, `${sheetName} sheet missing`);

  assert(text(value(ws, "A1")) === "MetroLink Transit Authority", `${sheetName}!A1 must be MetroLink Transit Authority`);
  assert(
    text(value(ws, "A2")).includes(titleContains),
    `${sheetName}!A2 must include "${titleContains}"`
  );

  const startRow = 6;
  const endRow = startRow + rows.length - 1;
  const totalsRow = endRow + 1;
  const endingRow = totalsRow + 1;
  const varianceRow = endingRow + 1;
  const glRow = varianceRow + 1;

  const mappings = [
    ["A", "vendor", "text"],
    ["B", "beginning_balance", "num"],
    ["C", "jan_adds", "num"],
    ["D", "jan_amortization", "num"],
    ["E", "jan_ending_balance", "num"],
    ["F", "feb_adds", "num"],
    ["G", "feb_amortization", "num"],
    ["H", "feb_ending_balance", "num"],
    ["I", "mar_adds", "num"],
    ["J", "mar_amortization", "num"],
    ["K", "mar_ending_balance", "num"],
    ["L", "apr_adds", "num"],
    ["M", "apr_amortization", "num"],
    ["N", "apr_ending_balance", "num"],
    ["O", "amortization_months", "num"],
    ["P", "comments", "text"],
    ["Q", "account_number", "num"],
  ];

  for (let i = 0; i < rows.length; i += 1) {
    const rowNumber = startRow + i;
    const source = rows[i];
    for (const [col, key, kind] of mappings) {
      const actual = value(ws, `${col}${rowNumber}`);
      const expected = source[key];
      if (kind === "text") {
        assert(
          text(actual) === text(expected),
          `${sheetName}!${col}${rowNumber} expected "${text(expected)}" got "${text(actual)}"`
        );
      } else {
        assert(
          near(actual, expected),
          `${sheetName}!${col}${rowNumber} expected ${num(expected)} got ${num(actual)}`
        );
      }
    }
  }
  ok(`${sheetName} row-level data matches normalized input`);

  const expectedTotalsFormulas = {
    B: `SUM(B${startRow}:B${endRow})`,
    C: `SUM(C${startRow}:C${endRow})`,
    D: `SUM(D${startRow}:D${endRow})`,
    E: `SUM(E${startRow}:E${endRow})`,
    F: `SUM(F${startRow}:F${endRow})`,
    G: `SUM(G${startRow}:G${endRow})`,
    H: `SUM(H${startRow}:H${endRow})`,
    I: `SUM(I${startRow}:I${endRow})`,
    J: `SUM(J${startRow}:J${endRow})`,
    K: `SUM(K${startRow}:K${endRow})`,
    L: `SUM(L${startRow}:L${endRow})`,
    M: `SUM(M${startRow}:M${endRow})`,
    N: `SUM(N${startRow}:N${endRow})`,
    O: `C${totalsRow}+F${totalsRow}+I${totalsRow}+L${totalsRow}`,
  };

  assert(
    text(value(ws, `A${totalsRow}`)).toLowerCase() === "month totals",
    `${sheetName}!A${totalsRow} must be "Month Totals"`
  );

  for (const [col, f] of Object.entries(expectedTotalsFormulas)) {
    assert(
      normalizeFormula(formula(ws, `${col}${totalsRow}`)) === normalizeFormula(f),
      `${sheetName}!${col}${totalsRow} formula mismatch`
    );
  }

  assert(
    text(value(ws, `A${endingRow}`)).toLowerCase() === "ending balance",
    `${sheetName}!A${endingRow} must be "Ending Balance"`
  );
  assert(
    normalizeFormula(formula(ws, `E${endingRow}`)) ===
      normalizeFormula(`B${totalsRow}+C${totalsRow}-D${totalsRow}`),
    `${sheetName}!E${endingRow} formula mismatch`
  );
  assert(
    normalizeFormula(formula(ws, `H${endingRow}`)) ===
      normalizeFormula(`E${totalsRow}+F${totalsRow}-G${totalsRow}`),
    `${sheetName}!H${endingRow} formula mismatch`
  );
  assert(
    normalizeFormula(formula(ws, `K${endingRow}`)) ===
      normalizeFormula(`H${totalsRow}+I${totalsRow}-J${totalsRow}`),
    `${sheetName}!K${endingRow} formula mismatch`
  );
  assert(
    normalizeFormula(formula(ws, `N${endingRow}`)) ===
      normalizeFormula(`K${totalsRow}+L${totalsRow}-M${totalsRow}`),
    `${sheetName}!N${endingRow} formula mismatch`
  );
  assert(
    normalizeFormula(formula(ws, `O${endingRow}`)) ===
      normalizeFormula(`D${totalsRow}+G${totalsRow}+J${totalsRow}+M${totalsRow}`),
    `${sheetName}!O${endingRow} formula mismatch`
  );

  assert(
    text(value(ws, `A${varianceRow}`)).toLowerCase() === "variance",
    `${sheetName}!A${varianceRow} must be "Variance"`
  );
  assert(
    normalizeFormula(formula(ws, `O${varianceRow}`)) ===
      normalizeFormula(`O${glRow}-N${glRow}`),
    `${sheetName}!O${varianceRow} formula mismatch`
  );

  assert(
    text(value(ws, `A${glRow}`)).toLowerCase() === "gl balance",
    `${sheetName}!A${glRow} must be "GL Balance"`
  );
  assert(near(value(ws, `E${glRow}`), glValues.jan), `${sheetName}!E${glRow} GL Jan mismatch`);
  assert(near(value(ws, `H${glRow}`), glValues.feb), `${sheetName}!H${glRow} GL Feb mismatch`);
  assert(near(value(ws, `K${glRow}`), glValues.mar), `${sheetName}!K${glRow} GL Mar mismatch`);
  assert(near(value(ws, `N${glRow}`), glValues.apr), `${sheetName}!N${glRow} GL Apr mismatch`);
  assert(
    normalizeFormula(formula(ws, `O${glRow}`)) === normalizeFormula(`O${totalsRow}-O${endingRow}`),
    `${sheetName}!O${glRow} formula mismatch`
  );

  ok(`${sheetName} control rows and GL linkage are correct`);

  return { totalsRow, endingRow, glRow };
}

const expRowsInfo = validateDetailSheet(
  "Bus Program #4310",
  expenseRows,
  gl.bus_program_4310,
  "4310"
);

const insRowsInfo = validateDetailSheet(
  "Rail Program #4320",
  insuranceRows,
  gl.rail_program_4320,
  "4320"
);

const summary = workbook.Sheets["Transit Summary"];
assert(summary, "Transit Summary sheet missing");

assert(text(value(summary, "A1")) === "MetroLink Transit Authority", "Transit Summary!A1 must be MetroLink Transit Authority");
assert(
  text(value(summary, "A2")).toLowerCase().includes("summary"),
  "Transit Summary!A2 must include Summary"
);
assert(
  text(value(summary, "A3")).includes("4/30/2025"),
  "Transit Summary!A3 must include period through 4/30/2025"
);

assert(text(value(summary, "A5")) === "Description", "Transit Summary!A5 must be Description");
assert(text(value(summary, "B5")) === "Amount", "Transit Summary!B5 must be Amount");

assert(
  normalizeFormula(formula(summary, "B7")) ===
    normalizeFormula(`'Bus Program #4310'!O${expRowsInfo.totalsRow}`),
  "Transit Summary!B7 formula mismatch"
);
assert(
  normalizeFormula(formula(summary, "B8")) ===
    normalizeFormula(`'Bus Program #4310'!O${expRowsInfo.endingRow}`),
  "Transit Summary!B8 formula mismatch"
);
assert(
  normalizeFormula(formula(summary, "B9")) ===
    normalizeFormula(`'Bus Program #4310'!O${expRowsInfo.glRow}`),
  "Transit Summary!B9 formula mismatch"
);
assert(
  normalizeFormula(formula(summary, "B12")) ===
    normalizeFormula(`'Rail Program #4320'!O${insRowsInfo.totalsRow}`),
  "Transit Summary!B12 formula mismatch"
);
assert(
  normalizeFormula(formula(summary, "B13")) ===
    normalizeFormula(`'Rail Program #4320'!O${insRowsInfo.endingRow}`),
  "Transit Summary!B13 formula mismatch"
);
assert(
  normalizeFormula(formula(summary, "B14")) ===
    normalizeFormula(`'Rail Program #4320'!O${insRowsInfo.glRow}`),
  "Transit Summary!B14 formula mismatch"
);
assert(
  normalizeFormula(formula(summary, "B16")) === normalizeFormula("B9+B14"),
  "Transit Summary!B16 formula must be B9+B14"
);
ok("Summary sheet formulas correctly linked to detailed tabs");

console.log("All tests passed.");
