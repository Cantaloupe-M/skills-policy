---
name: bc-calculated-fields-bc-areas
description: "Use when: you need to choose and apply calculated-field patterns by Business Central functional area across the full solution (Sales, Purchasing, Finance, Inventory, Service, Projects, Warehouse, Manufacturing)."
---

# BC Calculated Fields by Area (Catalog)

## Purpose
Route calculated-field implementations to the correct functional-area skill while keeping one consistent data contract:
- fixed label
- numeric result
- optional currency code

## Global Rules
- AL computes business data only.
- No final visual formatting in AL.
- No RDLC/layout edits in this workflow.

## Area Routing
- Sales: use `bc-calculated-fields-sales`
- Purchasing: use `bc-calculated-fields-purchasing`
- Finance: use `bc-calculated-fields-finance`
- Inventory: use `bc-calculated-fields-inventory`
- Service: use `bc-calculated-fields-service`
- Projects (Jobs): use `bc-calculated-fields-projects`
- Warehouse: use `bc-calculated-fields-warehouse`
- Manufacturing: use `bc-calculated-fields-manufacturing`

## Core Dependency
Always align with `bc-report-calculated-fields-core` for baseline contract and validation checklist.
