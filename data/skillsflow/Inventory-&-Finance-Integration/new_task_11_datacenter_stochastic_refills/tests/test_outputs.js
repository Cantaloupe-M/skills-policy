const fs = require("fs");
const path = require("path");
const assert = require("assert");
const XLSX = require("xlsx");
const CONFIG = {
  "variant": "stochastic",
  "sheets": {
    "current": "Current Fuel",
    "incoming": "Scheduled Refills",
    "ratio": "Policy Parameters"
  },
  "outputSheets": [
    "Site_Results",
    "Additional_Refills_Needed"
  ],
  "metadata": {
    "field": "Field",
    "value": "Value",
    "asOf": "AsOfDate",
    "horizon": "PlanningHorizonEnd",
    "remaining": "RemainingDaysInOctober"
  },
  "cells": {
    "asOf": "B1",
    "horizon": "D1",
    "unitsPerContainer": "A2",
    "serviceLevelZ": "B2"
  },
  "dataStartRow": 3,
  "columns": {
    "id": 0,
    "current": 1,
    "daily": 2,
    "stddev": 3,
    "incomingId": 0,
    "incomingDate": 1,
    "incomingQty": 3
  },
  "outputHeaders": [
    "Site_ID",
    "Current_Liters",
    "Expected_Daily_Burn_Liters",
    "Daily_Burn_StdDev",
    "Current_DOH",
    "Projected_Runout_Date",
    "Inbound_Liters_By_Oct31",
    "Delivered_DOH_To_Oct31",
    "Remaining_October_Burn_Liters",
    "Safety_Buffer_Liters",
    "Additional_Liters_Needed",
    "Tankers_Required_Rounded_Up",
    "Required_Refill_Date",
    "Rounding_Applied",
    "Earlier_Refill_Required",
    "Earliest_Scheduled_Refill_Date"
  ],
  "outputKeys": [
    "id",
    "current",
    "daily",
    "stddev",
    "currentDOH",
    "projected",
    "inbound",
    "delivered",
    "remaining",
    "safety",
    "additional",
    "containers",
    "required",
    "rounding",
    "earlier",
    "earliest"
  ],
  "additionalHeaders": [
    "Site_ID",
    "Required_Refill_Date",
    "Tankers_Required_Rounded_Up",
    "Additional_Liters_Needed",
    "Safety_Buffer_Liters",
    "Rounding_Applied",
    "Earlier_Refill_Required"
  ],
  "additionalKeys": [
    "id",
    "required",
    "containers",
    "additional",
    "safety",
    "rounding",
    "earlier"
  ]
};
const INPUT = "Backup_Fuel_and_Refills_Latest.xlsx";
const OUTPUT = "stochastic_refill_plan_october_2025.xlsx";
const EPS = 1e-9;
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function toNumber(v) {
  if (v === null || v === undefined || v === "") return 0;
  if (typeof v === "number") return Number.isFinite(v) ? v : 0;
  var n = Number(String(v).replace(/,/g, "").trim());
  return Number.isFinite(n) ? n : 0;
}

function toBool(v) {
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  var s = String(v || "").trim().toUpperCase();
  if (["TRUE", "T", "YES", "Y", "1"].includes(s)) return true;
  if (["FALSE", "F", "NO", "N", "0", ""].includes(s)) return false;
  return false;
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
  assert(current && incoming && ratio, "Missing one or more required sheets");

  var asOfDate = parseDate(current[CONFIG.cells.asOf] ? current[CONFIG.cells.asOf].v : null);
  var horizon = parseDate(current[CONFIG.cells.horizon] ? current[CONFIG.cells.horizon].v : null);
  assert(asOfDate && horizon, "Unable to parse AsOfDate or PlanningHorizonEnd");

  var unitRatio = toNumber(ratio[CONFIG.cells.unitsPerContainer] ? ratio[CONFIG.cells.unitsPerContainer].v : null);
  assert(unitRatio > 0, "Invalid conversion ratio");

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
      rounding: rounding,
      earlier: earlier,
      earliest: earliest ? toIsoDate(earliest) : "",
    };
  });

  return { asOfDate: toIsoDate(asOfDate), horizon: toIsoDate(horizon), remainingDays: remainingDays, rows: rows };
}

function expectedAoa(inputFile) {
  var wb = XLSX.readFile(inputFile, { raw: true, cellDates: true });
  var res = computeRows(wb);
  var s1 = [
    [CONFIG.metadata.field, CONFIG.metadata.value],
    [CONFIG.metadata.asOf, res.asOfDate],
    [CONFIG.metadata.horizon, res.horizon],
    [CONFIG.metadata.remaining, res.remainingDays],
    [],
    CONFIG.outputHeaders,
  ];
  res.rows.forEach(function (r) {
    s1.push(CONFIG.outputKeys.map(function (k) { return r[k]; }));
  });

  var s2 = [CONFIG.additionalHeaders];
  res.rows.forEach(function (r) {
    if (r.containers > 0) s2.push(CONFIG.additionalKeys.map(function (k) { return r[k]; }));
  });
  return { s1: s1, s2: s2 };
}

function approx(a, b, tol, msg) {
  assert(Math.abs(Number(a) - Number(b)) <= tol, msg + " (actual=" + a + ", expected=" + b + ")");
}

function compareCell(actual, expected, msg) {
  if (typeof expected === "boolean") {
    assert.strictEqual(toBool(actual), expected, msg);
  } else if (typeof expected === "number") {
    approx(toNumber(actual), expected, 1e-4, msg);
  } else if (expected === "") {
    assert(actual === null || actual === undefined || actual === "", msg);
  } else if (/^\d{4}-\d{2}-\d{2}$/.test(expected)) {
    assert.strictEqual(toIsoDate(actual), expected, msg);
  } else {
    var a = actual === null || actual === undefined ? "" : String(actual);
    assert.strictEqual(a, String(expected), msg);
  }
}

function compareAoa(actual, expected, label) {
  assert.strictEqual(actual.length, expected.length, label + " row count mismatch");
  for (var r = 0; r < expected.length; r += 1) {
    var erow = (expected[r] || []).slice();
    var arow = (actual[r] || []).slice();
    while (erow.length > 0 && (erow[erow.length - 1] === "" || erow[erow.length - 1] === null || erow[erow.length - 1] === undefined)) erow.pop();
    while (arow.length > 0 && (arow[arow.length - 1] === "" || arow[arow.length - 1] === null || arow[arow.length - 1] === undefined)) arow.pop();
    assert.strictEqual(arow.length, erow.length, label + " row " + (r + 1) + " column count mismatch");
    for (var c = 0; c < erow.length; c += 1) {
      compareCell(arow[c], erow[c], label + " R" + (r + 1) + "C" + (c + 1) + " mismatch");
    }
  }
}

function main() {
  var taskDir = path.resolve(__dirname, "..");
  var inHarness = fs.existsSync("/root/" + INPUT) && fs.existsSync("/tests");
  var inputFile = inHarness ? "/root/" + INPUT : path.join(taskDir, "environment", INPUT);
  var outputFile = inHarness ? "/root/" + OUTPUT : path.join(taskDir, OUTPUT);

  assert(fs.existsSync(inputFile), "Input file not found: " + inputFile);
  assert(fs.existsSync(outputFile), "Output file not found: " + outputFile);

  var exp = expectedAoa(inputFile);

  var wb = XLSX.readFile(outputFile, { raw: true, cellDates: true });
  assert.deepStrictEqual(wb.SheetNames, CONFIG.outputSheets, "Workbook must contain exactly two sheets in required order");

  var act1 = XLSX.utils.sheet_to_json(wb.Sheets[CONFIG.outputSheets[0]], { header: 1, raw: true, defval: "" });
  var act2 = XLSX.utils.sheet_to_json(wb.Sheets[CONFIG.outputSheets[1]], { header: 1, raw: true, defval: "" });

  compareAoa(act1, exp.s1, CONFIG.outputSheets[0]);
  compareAoa(act2, exp.s2, CONFIG.outputSheets[1]);

  console.log("All checks passed for " + OUTPUT);
}

main();
