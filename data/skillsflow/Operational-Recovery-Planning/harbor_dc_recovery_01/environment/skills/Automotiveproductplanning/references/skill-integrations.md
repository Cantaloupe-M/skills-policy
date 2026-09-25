# Skill Integrations Reference

How to connect Automotive Product Planning with other PAI skills for comprehensive strategy execution.

## HoshinKanri Integration

### Strategy Cascade

Product planning outputs feed into Hoshin Kanri X-Matrix:

```
PRODUCT PLAN → HOSHIN CASCADE

5-Year Product Strategy
        │
        ▼
Annual Breakthrough Objectives (X-Matrix North)
├─ "Launch [Model X] achieving [volume] units"
├─ "Complete [Platform] development to Gate 2"
├─ "Achieve [margin] on [product line]"
└─ "Enter [market] with homologated product"
        │
        ▼
Annual Improvement Priorities (X-Matrix West)
├─ Development efficiency
├─ Cost reduction targets
├─ Quality improvement
└─ Supplier development
        │
        ▼
Targets/KPIs (X-Matrix East)
├─ Programme milestones
├─ Financial metrics
├─ Quality metrics
└─ Market metrics
        │
        ▼
Departmental Responsibilities (X-Matrix South)
├─ Engineering
├─ Manufacturing
├─ Purchasing
├─ Sales/Marketing
└─ Finance
```

### Integration Commands

```bash
# After completing product plan, cascade to Hoshin:
/hoshinkanri "Cascade product strategy to annual objectives"

# Input: Product plan executive summary
# Output: Draft X-Matrix with product-driven objectives

# During annual planning:
/hoshinkanri "Review product plan alignment with current hoshin"

# Quarterly review:
/hoshinkanri "Update bowling chart for product programme milestones"
```

### Timing Alignment

| Product Planning Cycle | Hoshin Cycle | Integration Point |
|----------------------|--------------|-------------------|
| Strategic review (5yr) | Annual strategy session | Input to breakthrough objectives |
| Annual product update | Hoshin deployment | Align programme gates to hoshin targets |
| Quarterly programme review | Catchball sessions | Validate resource/priority alignment |
| Monthly milestone tracking | Bowling chart update | Programme status feeds KPIs |

---

## SupplyChain Integration

### From Product Plan to Supplier Strategy

```
PRODUCT PROGRAMME → SUPPLY CHAIN PLANNING

Programme Definition
├─ Bill of Materials structure
├─ Make/buy decisions
├─ Technology requirements
└─ Volume/timing plan
        │
        ▼
Sourcing Strategy
├─ Category strategies
├─ Supplier selection criteria
├─ Localisation requirements
└─ Risk mitigation approach
        │
        ▼
Supplier Development Plan
├─ New supplier qualifications
├─ Capability development
├─ Capacity investment
└─ PPAP planning
        │
        ▼
Cost Management
├─ Should-cost models
├─ PPV targets
├─ Value engineering
└─ Total cost analysis
```

### Integration Commands

```bash
# During programme planning:
/supplychain "Create sourcing strategy for [programme name]"

# Input: Programme specification, BOM structure
# Output: Category strategy matrix, supplier shortlist

# For new technology:
/supplychain "Evaluate supplier capability for [technology]"

# Cost analysis:
/supplychain "Should-cost analysis for [component]"

# Risk assessment:
/supplychain "Supply risk assessment for [programme]"
```

### Key Handoffs

| Product Planning Output | SupplyChain Input |
|------------------------|-------------------|
| Programme timing (SOP) | Supplier nomination deadline |
| Volume forecast | Capacity requirements |
| Technology specification | Capability assessment criteria |
| Target cost | Should-cost targets |
| Quality requirements | PPAP scope |

---

## AutomotiveManufacturing Integration

### From Product Plan to Launch Readiness

```
PRODUCT PROGRAMME → APQP/LAUNCH PLANNING

Programme Gate 2 (Design Freeze)
        │
        ▼
APQP Phase 1: Plan & Define
├─ Quality objectives
├─ Process flow concept
├─ Preliminary BOM
└─ Resource planning
        │
        ▼
APQP Phase 2: Product Design
├─ DFMEA
├─ Design verification plan
├─ Prototype build
└─ Supplier PPAP requirements
        │
        ▼
APQP Phase 3: Process Design
├─ PFMEA
├─ Control plan (pre-launch)
├─ Work instructions
└─ MSA planning
        │
        ▼
APQP Phase 4: Validation
├─ Production trial runs
├─ Measurement system validation
├─ Process capability studies
└─ PPAP submission
        │
        ▼
APQP Phase 5: Production
├─ Launch containment
├─ Continuous improvement
├─ Lessons learned
└─ Control plan (production)
```

### Integration Commands

```bash
# At programme approval:
/automotivemanufacturing "Create APQP timeline for [programme] SOP [date]"

# Input: Programme schedule, product specification
# Output: APQP phase plan with milestones

# During development:
/automotivemanufacturing "DFMEA template for [system/component]"

# Pre-production:
/automotivemanufacturing "Launch readiness checklist for [programme]"

# Quality planning:
/automotivemanufacturing "Control plan template for [process]"
```

### Timeline Integration

```
PRODUCT DEVELOPMENT ─────────────────────────────────────────────►

Gate 0    Gate 1    Gate 2    Gate 3    Gate 4    SOP
  │         │         │         │         │        │
  ▼         ▼         ▼         ▼         ▼        ▼
[Concept] [Design]  [Freeze]  [Tool]   [Valid]  [Launch]

APQP ────────────────────────────────────────────────────────────►

        Phase 1   Phase 2        Phase 3   Phase 4    Phase 5
          │         │              │         │          │
          ▼         ▼              ▼         ▼          ▼
       [Plan]   [Product]      [Process] [Valid]  [Production]
                 Design         Design
```

---

## Research Integration

### Competitive Intelligence

```bash
# Market analysis:
/research "comprehensive" "competitive landscape [segment] sportscar market 2026"

# Technology trends:
/research "standard" "[powertrain type] technology trends luxury vehicles"

# Regulatory monitoring:
/research "quick" "[regulation] implementation timeline [market]"

# Competitor watch:
/research "standard" "[competitor] new model announcements product plan"
```

### Research Outputs to Product Planning

| Research Query | Product Planning Use |
|---------------|---------------------|
| Competitive positioning | White space analysis, pricing strategy |
| Technology trends | Powertrain/feature roadmap decisions |
| Regulatory updates | Compliance timeline validation |
| Market forecasts | Volume assumptions, segment sizing |
| Supplier landscape | Partnership opportunity identification |

---

## BusinessStrategy Integration

### Financial Deep-Dive

When product planning requires detailed financial analysis beyond standard templates:

```bash
# Detailed financial modelling:
/businessstrategy "Programme NPV analysis with Monte Carlo simulation for [programme]"

# Valuation impact:
/businessstrategy "Impact of product plan on company valuation"

# Funding strategy:
/businessstrategy "Funding options analysis for [investment amount] over [period]"

# Scenario planning:
/businessstrategy "Scenario analysis: [economic downturn / competitor entry / regulatory acceleration]"
```

### Inputs from BusinessStrategy

| BusinessStrategy Output | Product Planning Use |
|------------------------|---------------------|
| Company valuation model | Programme prioritisation |
| Cash flow projections | Investment timing constraints |
| Risk appetite assessment | Programme IRR thresholds |
| Funding capacity | Portfolio scope limitation |

---

## Integrated Workflow Example

### New Programme Initiation

```
1. PRODUCT PLANNING: Discovery & concept
   └─ Output: Programme brief, preliminary business case

2. RESEARCH: Competitive & market validation
   └─ /research "comprehensive" "[segment] competitive analysis"
   └─ Output: Market validation, competitive positioning

3. SUPPLYCHAIN: Sourcing feasibility
   └─ /supplychain "Preliminary sourcing assessment for [programme]"
   └─ Output: Make/buy recommendations, supplier landscape

4. PRODUCT PLANNING: Refine business case
   └─ Update with sourcing inputs
   └─ Output: Gate 1 business case

5. BUSINESSSTRATEGY: Financial validation (if required)
   └─ /businessstrategy "Detailed NPV/IRR analysis [programme]"
   └─ Output: Board-ready financial case

6. HOSHINKANRI: Strategic alignment
   └─ /hoshinkanri "Validate [programme] alignment with strategy"
   └─ Output: Confirmation of strategic fit

7. AUTOMOTIVEMANUFACTURING: Launch planning
   └─ /automotivemanufacturing "APQP plan for [programme] SOP [date]"
   └─ Output: Manufacturing readiness roadmap
```

---

## Cross-Skill Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMOTIVE PRODUCT PLANNING                   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Strategy │  │ Roadmap  │  │Financial │  │ Risk     │       │
│  │ Intent   │  │ Timeline │  │ Model    │  │ Register │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │             │               │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        ▼             │             │             │
┌───────────────┐     │             │             │
│  HOSHINKANRI  │     │             │             │
│               │     │             │             │
│ • Objectives  │◄────┘             │             │
│ • X-Matrix    │                   │             │
│ • Catchball   │                   │             │
└───────────────┘                   │             │
                                    │             │
        ┌───────────────────────────┘             │
        │                                         │
        ▼                                         │
┌───────────────┐     ┌───────────────┐          │
│  SUPPLYCHAIN  │     │BUSINESS       │          │
│               │     │STRATEGY       │◄─────────┤
│ • Sourcing    │     │               │          │
│ • Suppliers   │     │ • Valuation   │          │
│ • Cost        │     │ • Funding     │          │
└───────┬───────┘     └───────────────┘          │
        │                                         │
        │             ┌───────────────┐          │
        │             │   RESEARCH    │          │
        │             │               │◄─────────┘
        │             │ • Competitors │
        │             │ • Markets     │
        │             │ • Technology  │
        ▼             └───────────────┘
┌───────────────┐
│AUTOMOTIVE     │
│MANUFACTURING  │
│               │
│ • APQP        │
│ • Quality     │
│ • Launch      │
└───────────────┘
```
