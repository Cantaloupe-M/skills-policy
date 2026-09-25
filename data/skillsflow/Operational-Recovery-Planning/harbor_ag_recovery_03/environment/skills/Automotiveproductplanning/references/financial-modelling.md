# Financial Modelling Reference

Board-ready financial analysis templates for vehicle programme investment decisions.

## Programme Economics Framework

### Cost Categories

```
PROGRAMME INVESTMENT BREAKDOWN

1. DEVELOPMENT COSTS (capitalised)
   ├─ Engineering & design
   │  ├─ Internal engineering hours × rate
   │  ├─ External engineering contracts
   │  ├─ CAD/CAE software & compute
   │  └─ Prototype materials
   │
   ├─ Prototype & testing
   │  ├─ Prototype build costs (typically 5-20 vehicles)
   │  ├─ Durability testing
   │  ├─ Crash testing
   │  └─ Powertrain validation
   │
   └─ Programme management
      ├─ Internal PM allocation
      └─ Supplier development

2. TOOLING & EQUIPMENT (capitalised)
   ├─ Body tooling
   │  ├─ Stamping dies (if applicable)
   │  ├─ Composite moulds
   │  └─ Jigs & fixtures
   │
   ├─ Assembly equipment
   │  ├─ Production fixtures
   │  ├─ Test equipment
   │  └─ Line modifications
   │
   └─ Supplier tooling
      ├─ Paid tooling at suppliers
      └─ Amortised tooling in piece price

3. CERTIFICATION & COMPLIANCE
   ├─ Type approval fees
   ├─ Emissions testing & certification
   ├─ Safety testing & certification
   ├─ Homologation by market
   └─ Legal & regulatory support

4. LAUNCH COSTS (expensed)
   ├─ Marketing & launch events
   ├─ Sales training
   ├─ Dealer/distribution setup
   ├─ Service documentation
   └─ Initial parts inventory
```

### Low-Volume Benchmarks

| Cost Element | Mass Market | Low Volume (1-5k/yr) | Ultra-Low (<500/yr) |
|--------------|-------------|---------------------|---------------------|
| Development | £500m-2bn | £10-50m | £2-15m |
| Body tooling | £100-500m | £2-15m | £0.5-3m |
| Certification | £5-20m | £0.5-3m | £0.2-1m |
| **Total investment** | **£1-3bn** | **£15-70m** | **£3-20m** |
| Per-unit amortisation | £500-1,500 | £3,000-15,000 | £10,000-50,000 |

---

## NPV & IRR Calculations

### Programme NPV Model

```
PROGRAMME: [Name]
─────────────────────────────────────────────────────────────────

ASSUMPTIONS
├─ Discount rate (WACC): ______%
├─ Production life: ______ years
├─ Annual volume: ______ units
├─ Average selling price: £______
├─ Variable cost per unit: £______
├─ Contribution per unit: £______

INVESTMENT SCHEDULE (£m)
                        Y-2     Y-1     Y0      Y1      Y2      Total
Development             X       X       —       —       —       X
Tooling                 —       X       X       —       —       X
Certification           —       —       X       —       —       X
Launch                  —       —       X       —       —       X
─────────────────────────────────────────────────────────────────
Total investment        X       X       X       —       —       XX

CASH FLOW PROJECTION (£m)
                        Y1      Y2      Y3      Y4      Y5      Y6
Volume (units)          X       X       X       X       X       X
Revenue                 X       X       X       X       X       X
Variable costs          (X)     (X)     (X)     (X)     (X)     (X)
Contribution            X       X       X       X       X       X
Fixed production costs  (X)     (X)     (X)     (X)     (X)     (X)
EBITDA                  X       X       X       X       X       X

VALUATION
NPV @ ______% discount: £______ million
IRR: ______%
Payback period: ______ years
Break-even volume: ______ units (cumulative)
```

### IRR Decision Framework

| IRR Range | Typical Decision | Rationale |
|-----------|-----------------|-----------|
| <10% | Reject | Below cost of capital |
| 10-15% | Marginal | Consider strategic value |
| 15-25% | Attractive | Standard programme threshold |
| 25-40% | Very attractive | Prioritise investment |
| >40% | Exceptional | Accelerate if possible |

**Adjust thresholds based on:**
- Company cost of capital
- Strategic importance of programme
- Risk profile of the investment
- Portfolio balance requirements

---

## Sensitivity Analysis

### Key Variable Sensitivity

```
SENSITIVITY MATRIX: Programme [Name]
Base case IRR: ______%

                        -20%    -10%    Base    +10%    +20%
─────────────────────────────────────────────────────────────────
Volume                  X%      X%      X%      X%      X%
Price                   X%      X%      X%      X%      X%
Variable cost           X%      X%      X%      X%      X%
Development cost        X%      X%      X%      X%      X%

BREAK-EVEN SENSITIVITY
What volume makes IRR = [hurdle rate]%?  ______ units/year
What price makes IRR = [hurdle rate]%?   £______
```

### Scenario Analysis

```
SCENARIO COMPARISON

                        Pessimistic  Base Case   Optimistic
─────────────────────────────────────────────────────────────────
ASSUMPTIONS
Volume                  -20%         —           +15%
Price                   -10%         —           +5%
Variable cost           +15%         —           -5%
Development cost        +25%         —           -10%

OUTCOMES
NPV                     £____m       £____m      £____m
IRR                     ____%        ____%       ____%
Payback                 ____yrs      ____yrs     ____yrs

Probability weighting   ____%        ____%       ____%
Weighted NPV            £____m
```

---

## Portfolio Analysis

### Aggregate Investment Profile

```
5-YEAR PORTFOLIO INVESTMENT (£m)
                        Y1      Y2      Y3      Y4      Y5      Total
─────────────────────────────────────────────────────────────────
Programme A             X       X       —       —       —       X
Programme B             —       X       X       X       —       X
Programme C             —       —       X       X       X       X
Platform investment     X       X       X       —       —       X
Other capex             X       X       X       X       X       X
─────────────────────────────────────────────────────────────────
Total investment        X       X       X       X       X       XX

FUNDING SOURCES (£m)
Operating cash flow     X       X       X       X       X       X
Debt drawdown           X       X       —       —       —       X
(Debt repayment)        —       —       (X)     (X)     (X)     (X)
─────────────────────────────────────────────────────────────────
Net funding position    —       —       —       —       —       —

Peak funding requirement: £____m in Y____
```

### Portfolio NPV Summary

```
PORTFOLIO VALUE CREATION

Programme               Investment   NPV         IRR     Strategic Score
─────────────────────────────────────────────────────────────────
[Programme A]           £____m       £____m      ____%   [1-5]
[Programme B]           £____m       £____m      ____%   [1-5]
[Programme C]           £____m       £____m      ____%   [1-5]
─────────────────────────────────────────────────────────────────
Portfolio total         £____m       £____m      ____%

Portfolio IRR calculation:
- Aggregate all cash flows
- Calculate single IRR across portfolio
```

---

## Category-Specific Considerations

### Restomod/Continuation Economics

```
RESTOMOD PROGRAMME ECONOMICS

Typical characteristics:
- Volume: 10-150 units total
- Price: £300k-2m per unit
- Development: £1-5m
- Tooling: £0.5-2m (often soft tooling)
- Margin: 25-45% (premium for heritage)

Key success factors:
- Heritage asset value (brand IP, design rights)
- Donor vehicle availability/cost
- Authenticity vs modernisation balance
- Legal/trademark protection

Example P&L:
  Revenue per unit:           £500,000
  Donor vehicle:             (£100,000)
  Parts & materials:         (£150,000)
  Labour (assembly):         (£50,000)
  Contribution:               £200,000  (40%)

  Programme investment:       £2,000,000
  Break-even volume:          10 units
```

### Bespoke/Commission Economics

```
BESPOKE PROGRAMME ECONOMICS

Typical characteristics:
- Volume: 1-10 units
- Price: £500k-5m+ per unit
- Development: Customer-funded or absorbed
- Tooling: Minimal (hand-built)
- Margin: 30-50% (labour-intensive)

Pricing model:
  Base vehicle (if applicable):    £______
  Engineering/design:              £______ (typically time-based)
  Bespoke content:                 £______ (materials + markup)
  Programme management:            £______ (% of total)
  Margin:                          £______ (target %)
  ─────────────────────────────────
  Customer price:                  £______

Capacity constraint:
  Engineering hours available:     ______ /year
  Average project hours:           ______
  Maximum projects:                ______/year
```

### Motorsport Programme Economics

```
MOTORSPORT PROGRAMME ROI

Investment categories:
  - Racing team operation:         £______/year
  - Vehicle development:           £______/programme
  - Homologation (if applicable):  £______

Return mechanisms:
  - Customer car sales:            £______ revenue
  - Parts & service:               £______ revenue
  - Sponsorship:                   £______ revenue
  - Brand value (attributed):      £______ (estimated)

Technology transfer value:
  - Accelerated production development: £______ (saved cost)
  - Marketing/PR value:                 £______ (equivalent spend)

Break-even analysis:
  Direct ROI (cash):               ______%
  Including brand value:           ______%
```

---

## Excel Export Format

For financial tables, use pipe-separated format for easy spreadsheet import:

```
| Programme | Y1 | Y2 | Y3 | Y4 | Y5 | Total |
|-----------|------|------|------|------|------|-------|
| Development | 3.0 | 5.0 | 2.0 | 0.0 | 0.0 | 10.0 |
| Tooling | 0.0 | 2.0 | 4.0 | 0.0 | 0.0 | 6.0 |
| Certification | 0.0 | 0.0 | 0.5 | 0.3 | 0.0 | 0.8 |
| Total | 3.0 | 7.0 | 6.5 | 0.3 | 0.0 | 16.8 |
```

**Copy to Excel:**
1. Copy table including headers
2. Paste into Excel
3. Data → Text to Columns → Delimited → Pipe character
4. Format as table

---

## Decision Gate Financial Criteria

### Gate 0: Strategic Intent
- Preliminary investment estimate: ±50%
- Market size validation
- Initial margin target feasibility

### Gate 1: Concept Approval
- Investment estimate: ±30%
- Preliminary NPV/IRR
- Funding approach identified

### Gate 2: Design Freeze
- Investment estimate: ±20%
- Detailed NPV/IRR
- Sensitivity analysis complete
- Board approval for tooling

### Gate 3: Tooling Commitment
- Investment estimate: ±10%
- Final business case
- Funding committed
- Full board/shareholder approval

### Gate 4: Launch Readiness
- Final cost reconciliation
- Launch budget confirmed
- Volume ramp plan
