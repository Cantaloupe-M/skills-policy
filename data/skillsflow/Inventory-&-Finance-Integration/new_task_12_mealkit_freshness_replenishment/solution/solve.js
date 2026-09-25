const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");
const CONFIG = {
  "variant": "shelf",
  "sheets": {
    "current": "Current Inventory",
    "incoming": "Incoming Deliveries",
    "ratio": "Shelf_Life"
  },
  "outputSheets": [
    "Freshness_Results",
    "Additional_Freshness_Needed"
  ],
  "metadata": {
    "field": "Field",
    "value": "Value",
    "asOf": "AsOfDate",
    "horizon": "PlanningHorizonEnd",
    "remaining": "RemainingDaysInNovember"
  },
  "cells": {
    "asOf": "B1",
    "horizon": "D1",
    "unitsPerContainer": "A2"
  },
  "dataStartRow": 3,
  "columns": {
    "id": 0,
    "current": 1,
    "daily": 2,
    "expiring": 3,
    "incomingId": 0,
    "incomingDate": 1,
    "incomingQty": 3
  },
  "outputHeaders": [
    "Meal_Kit_ID",
    "Current_Boxes",
    "Boxes_Expiring_By_Nov30",
    "Usable_Current_Boxes",
    "Daily_Order_Rate_Boxes",
    "Current_DOH",
    "Projected_OOS_Date",
    "Inbound_Boxes_By_Nov30",
    "Delivered_DOH_To_Nov30",
    "Remaining_November_Demand_Boxes",
    "Additional_Boxes_Needed",
    "Pallets_Required_Rounded_Up",
    "Required_Delivery_Date",
    "Rounding_Applied",
    "Earlier_Delivery_Required",
    "Earliest_Scheduled_Inbound_Date"
  ],
  "outputKeys": [
    "id",
    "current",
    "expiring",
    "usable",
    "daily",
    "currentDOH",
    "projected",
    "inbound",
    "delivered",
    "remaining",
    "additional",
    "containers",
    "required",
    "rounding",
    "earlier",
    "earliest"
  ],
  "additionalHeaders": [
    "Meal_Kit_ID",
    "Required_Delivery_Date",
    "Pallets_Required_Rounded_Up",
    "Additional_Boxes_Needed",
    "Rounding_Applied",
    "Earlier_Delivery_Required"
  ],
  "additionalKeys": [
    "id",
    "required",
    "containers",
    "additional",
    "rounding",
    "earlier"
  ]
};
const EPS = 1e-9;
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function toNumber(v) {
  if (v === null || v === undefined || v === "") return 0;
  if (typeof v === "number") return Number.isFinite(v) ? v : 0;
  var n = Number(String(v).replace(/,/g, "").trim());
  return Number.isFinite(n) ? n : 0;
}

function roundTo(v, d) {
  var f = Math.pow(10, d);
  return Math.round(v * f) / f;
}

function parseDate(v) {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number") {
    var p = XLSX.SSF.parse_date_code(v);
    if (!p) return null;
    return new Date(Date.UTC(p.y, p.m - 1, p.d));
  }
  if (v instanceof Date) {
    return new Date(Date.UTC(v.getFullYear(), v.getMonth(), v.getDate()));
  }
  var s = String(v).trim();
  var m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (m) return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) return new Date(Date.UTC(Number(m[3]), Number(m[1]) - 1, Number(m[2])));
  var f = new Date(s);
  if (!Number.isNaN(f.getTime())) {
    return new Date(Date.UTC(f.getUTCFullYear(), f.getUTCMonth(), f.getUTCDate()));
  }
  return null;
}

function toIsoDate(v) {
  var d = v instanceof Date ? v : parseDate(v);
  if (!d) return "";
  var y = d.getUTCFullYear();
  var m = String(d.getUTCMonth() + 1).padStart(2, "0");
  var dd = String(d.getUTCDate()).padStart(2, "0");
  return y + "-" + m + "-" + dd;
}

function addDays(d, days) {
  return new Date(d.getTime() + days * MS_PER_DAY);
}

function diffDays(a, b) {
  return Math.round((b.getTime() - a.getTime()) / MS_PER_DAY);
}

function key(v) {
  return String(v || "").trim().toUpperCase();
}

function computeRows(wb) {
  var current = wb.Sheets[CONFIG.sheets.current];
  var incoming = wb.Sheets[CONFIG.sheets.incoming];
  var ratio = wb.Sheets[CONFIG.sheets.ratio];
  if (!current || !incoming || !ratio) throw new Error("Missing one or more required sheets");

  var asOfDate = parseDate(current[CONFIG.cells.asOf] ? current[CONFIG.cells.asOf].v : null);
  var horizon = parseDate(current[CONFIG.cells.horizon] ? current[CONFIG.cells.horizon].v : null);
  if (!asOfDate || !horizon) throw new Error("Unable to parse AsOfDate or PlanningHorizonEnd");

  var unitRatio = toNumber(ratio[CONFIG.cells.unitsPerContainer] ? ratio[CONFIG.cells.unitsPerContainer].v : null);
  if (unitRatio <= 0) throw new Error("Invalid conversion ratio");

  var z = 0;
  if (CONFIG.variant === "stochastic") {
    z = toNumber(ratio[CONFIG.cells.serviceLevelZ] ? ratio[CONFIG.cells.serviceLevelZ].v : null);
  }

  var currentRows = XLSX.utils.sheet_to_json(current, { header: 1, raw: true, defval: null });
  var incomingRows = XLSX.utils.sheet_to_json(incoming, { header: 1, raw: true, defval: null });

  var base = [];
  for (var i = CONFIG.dataStartRow; i < currentRows.length; i += 1) {
    var r = currentRows[i] || [];
    var id = key(r[CONFIG.columns.id]);
    if (!id) continue;
    base.push({
      id: id,
      current: toNumber(r[CONFIG.columns.current]),
      daily: toNumber(r[CONFIG.columns.daily]),
      stddev: CONFIG.variant === "stochastic" ? toNumber(r[CONFIG.columns.stddev]) : 0,
      expiring: CONFIG.variant === "shelf" ? toNumber(r[CONFIG.columns.expiring]) : 0,
    });
  }

  var inboundById = {};
  for (var j = 1; j < incomingRows.length; j += 1) {
    var ir = incomingRows[j] || [];
    var iid = key(ir[CONFIG.columns.incomingId]);
    if (!iid) continue;
    var dt = parseDate(ir[CONFIG.columns.incomingDate]);
    if (!dt) continue;
    var qty = toNumber(ir[CONFIG.columns.incomingQty]);
    if (!inboundById[iid]) inboundById[iid] = [];
    inboundById[iid].push({ dt: dt, qty: qty });
  }

  Object.keys(inboundById).forEach(function (id) {
    inboundById[id].sort(function (a, b) {
      return a.dt.getTime() - b.dt.getTime();
    });
  });

  var remainingDays = diffDays(asOfDate, horizon);
  var rows = base.map(function (row) {
    var arr = inboundById[row.id] || [];
    var earliest = arr.length ? arr[0].dt : null;
    var inbound = arr.filter(function (x) { return x.dt.getTime() <= horizon.getTime(); })
      .reduce(function (s, x) { return s + x.qty; }, 0);

    var usable = CONFIG.variant === "shelf" ? Math.max(0, row.current - row.expiring) : row.current;
    var doh = row.daily > 0 ? usable / row.daily : null;
    var projected = row.daily > 0 ? addDays(asOfDate, Math.floor(doh + EPS)) : null;
    var delivered = row.daily > 0 ? (usable + inbound) / row.daily : null;
    var remaining = row.daily * remainingDays;
    var safety = CONFIG.variant === "stochastic" ? z * row.stddev * Math.sqrt(Math.max(0, remainingDays)) : 0;
    var additional = row.daily > 0 ? Math.max(0, remaining + safety - usable - inbound) : 0;
    var containers = additional > 0 ? Math.ceil((additional - EPS) / unitRatio) : 0;

    var required = null;
    if (containers > 0) {
      if (earliest && projected && earliest.getTime() <= projected.getTime()) required = addDays(asOfDate, Math.floor(delivered + EPS));
      else required = projected;
    }

    var implied = containers * unitRatio;
    var rounding = containers > 0 && Math.abs(implied - additional) > EPS;
    var earlier = containers > 0 && (!earliest || (required && required.getTime() < earliest.getTime()));

    return {
      id: row.id,
      current: row.current,
      daily: row.daily,
      stddev: CONFIG.variant === "stochastic" ? row.stddev : "",
      expiring: CONFIG.variant === "shelf" ? row.expiring : "",
      usable: CONFIG.variant === "shelf" ? usable : "",
      currentDOH: row.daily > 0 ? roundTo(doh, 4) : "",
      projected: row.daily > 0 ? toIsoDate(projected) : "",
      inbound: inbound,
      delivered: row.daily > 0 ? roundTo(delivered, 4) : "",
      remaining: roundTo(remaining, 4),
      safety: CONFIG.variant === "stochastic" ? roundTo(safety, 4) : "",
      additional: roundTo(additional, 4),
      containers: containers,
      required: required ? toIsoDate(required) : "",
      rounding: Boolean(rounding),
      earlier: Boolean(earlier),
      earliest: earliest ? toIsoDate(earliest) : "",
    };
  });

  return { asOfDate: toIsoDate(asOfDate), horizon: toIsoDate(horizon), remainingDays: remainingDays, rows: rows };
}

function main() {
  var input = process.argv[2];
  var output = process.argv[3];
  if (!input || !output) throw new Error("Usage: node solve.js <input> <output>");
  if (!fs.existsSync(input)) throw new Error("Input workbook not found: " + input);

  var wb = XLSX.readFile(input, { raw: true, cellDates: true });
  var res = computeRows(wb);

  var aoa1 = [
    [CONFIG.metadata.field, CONFIG.metadata.value],
    [CONFIG.metadata.asOf, res.asOfDate],
    [CONFIG.metadata.horizon, res.horizon],
    [CONFIG.metadata.remaining, res.remainingDays],
    [],
    CONFIG.outputHeaders,
  ];
  res.rows.forEach(function (r) {
    aoa1.push(CONFIG.outputKeys.map(function (k) { return r[k]; }));
  });

  var aoa2 = [CONFIG.additionalHeaders];
  res.rows.forEach(function (r) {
    if (r.containers > 0) aoa2.push(CONFIG.additionalKeys.map(function (k) { return r[k]; }));
  });

  var out = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(out, XLSX.utils.aoa_to_sheet(aoa1), CONFIG.outputSheets[0]);
  XLSX.utils.book_append_sheet(out, XLSX.utils.aoa_to_sheet(aoa2), CONFIG.outputSheets[1]);

  var outDir = path.dirname(output);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  XLSX.writeFile(out, output);
  console.log("Wrote " + output);
}

main();
