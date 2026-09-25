---
name: bc-calculated-fields-manufacturing
description: "Use when: calculated fields are needed in Manufacturing reports (production order totals, capacity/material consumption, cost rollups) with AL data contract and no layout edits."
---

# BC Manufacturing Calculated Fields

## Scope
- Production order cost/quantity totals and operation/material rollups.

## Inputs and Sources
- Production order lines, capacity entries, item/value entries, related buffers.

## Pattern
1. Expose label/amount/currency columns.
2. Compute in the parent dataitem that matches report output level.
3. Keep AL values raw; format in RDLC.

## Hard Rules
- No AL visual formatting.
- No layout file editing in this workflow.
