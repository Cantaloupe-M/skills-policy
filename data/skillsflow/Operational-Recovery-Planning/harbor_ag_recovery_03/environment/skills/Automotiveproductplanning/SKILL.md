---
name: Automotiveproductplanning
description: Strategic 5-10 year product planning for low-volume sportscar and specialist vehicle manufacturers. Covers new production vehicles, restomods/continuation cars, bespoke commissions, and motorsport programmes. Board-ready financial analysis with NPV/IRR. Integrates with HoshinKanri, SupplyChain, and AutomotiveManufacturing skills. USE WHEN creating product roadmaps, model lifecycle planning, platform strategy, powertrain transitions, competitive positioning, or OEM partnership evaluation.
---

# Automotive Product Planning Skill

Strategic product planning for low-volume sportscar and specialist vehicle manufacturers (typically <10,000 units annually). Synthesises market intelligence, regulatory requirements, technology readiness, partnership opportunities, and financial constraints into actionable product roadmaps.

## Skill Integration

This skill integrates with:

| Skill | Integration Point |
|-------|------------------|
| **HoshinKanri** | Cascade product strategy to annual breakthrough objectives |
| **SupplyChain** | Link product plans to supplier development and sourcing strategy |
| **AutomotiveManufacturing** | Connect to APQP, launch readiness, and quality planning |
| **Research** | Real-time competitive intelligence gathering |
| **BusinessStrategy** | Deep financial analysis when required |

When working on product planning, proactively suggest relevant skill integrations.

## Role Context

This skill operates as a **Product Planning Director** combining:
- Commercial strategy (market positioning, pricing, competitive analysis)
- Engineering feasibility (platform sharing, powertrain options, development capacity)
- Financial modelling (NPV, IRR, tooling amortisation, margin targets)
- Regulatory compliance (emissions, safety, type approval timelines)
- Partnership strategy (JVs, licensing, contract manufacturing)
- Technology roadmapping (powertrain transitions, motorsport tech transfer)

## Product Categories Covered

### 1. Production Vehicles
Standard new vehicle programmes with series production intent.

### 2. Restomods & Continuation Cars
Classic vehicle reimagining with modern technology. Includes:
- Continuation builds (authorised reproductions of heritage models)
- Restomod programmes (classic bodies with modern mechanicals)
- Heritage editions (limited runs celebrating brand history)

### 3. Bespoke & Commission Vehicles
Ultra-low volume custom builds:
- One-off commissions
- Small-batch special editions
- Customer-specified variants

### 4. Motorsport & Track Vehicles
Racing programmes and track-day products:
- Homologation specials
- GT racing programmes
- Track-only variants
- Customer racing programmes

## Core Workflow

### Phase 1: Discovery

Run `references/discovery-template.md` to gather company profile and strategic intent.

**Key Discovery Areas:**
- Current portfolio and volumes
- Manufacturing capabilities and constraints
- Engineering resources (in-house vs outsourced)
- Capital availability and funding sources
- Brand positioning and heritage assets
- Geographic market priorities
- Technology partnerships and IP

### Phase 2: Horizon Recommendation

Based on discovery, recommend planning horizon:

| Factor | Suggests Shorter (5yr) | Suggests Longer (10yr) |
|--------|----------------------|----------------------|
| Investment scale | <£50m total | >£100m platform investments |
| Platform lifecycle | Incremental updates | New architecture required |
| Powertrain transition | Single technology | Multi-stage ICE→Hybrid→BEV |
| Regulatory pressure | Stable requirements | Major regime change (Euro 7, ICE bans) |
| Market maturity | Established segments | Emerging categories (restomod, track-day) |

**Default recommendation**: Start with 5-year detailed plan, overlay 10-year strategic vision for major technology bets.

### Phase 3: Analysis

Apply frameworks from `references/analysis-frameworks.md`:

1. **Regulatory Timeline Analysis** — Map compliance deadlines against product cycles
2. **Competitive Landscape Mapping** — Position against direct and adjacent competitors
3. **Platform Economics Assessment** — Evaluate sharing opportunities and constraints
4. **Technology Readiness Evaluation** — Assess all powertrain paths
5. **Partnership Opportunity Scan** — Identify collaboration potential

For competitive intelligence, invoke **Research skill**:
```
/research "competitive landscape [segment] sportscar market [year]"
```

### Phase 4: Roadmap Construction

Build roadmap using `references/roadmap-template.md`:

**Production Vehicles:**
1. Anchor Products — Core volume models that fund development
2. Hero Products — Halo cars that define brand positioning
3. Variant Cascade — Derivatives, special editions, market-specific versions
4. Platform Investments — Major architecture decisions and timing
5. Powertrain Strategy — Technology transition path

**Adjacent Categories:**
6. Restomod/Continuation — Heritage-based programmes
7. Bespoke Pipeline — Commission vehicle capacity
8. Motorsport Calendar — Racing programme alignment

### Phase 5: Financial Validation

Apply `references/financial-modelling.md` for board-ready analysis:

- NPV and IRR calculations per programme
- Sensitivity analysis (volume, price, cost)
- Cash flow timing against investment gates
- Peak funding requirements
- Break-even analysis by programme

**Decision criteria:**
- Minimum programme IRR: [Company-specific threshold]
- Maximum payback period: [Company-specific threshold]
- Portfolio NPV positive within planning horizon

### Phase 6: Partnership Assessment

Apply `references/partnership-strategy.md`:

- Platform sharing opportunities
- Powertrain licensing (in or out)
- Contract manufacturing evaluation
- JV structures for market access or technology
- IP licensing (heritage, design language)

### Phase 7: Risk Assessment

Identify and mitigate key risks:
- Regulatory changes that could strand investments
- Supply chain dependencies (batteries, semiconductors)
- Competitive moves disrupting positioning
- Technology bets that may not mature
- Partnership execution risks

### Phase 8: Cascade to Execution

Link to operational planning:

**HoshinKanri Integration:**
```
Product strategy objectives → Annual breakthrough objectives → Departmental targets
```

**SupplyChain Integration:**
```
New programme sourcing → Supplier development plan → PPAP timeline
```

**AutomotiveManufacturing Integration:**
```
SOP timing → APQP phases → Launch readiness gates
```

## Output Formats

See `references/output-examples.md` for templates.

**Executive Summary** — Single-page strategic overview (board/investors)
**Detailed Roadmap** — Year-by-year timing with decision gates
**Programme Cards** — Deep-dive per vehicle programme
**Investment Schedule** — Capex/opex with NPV/IRR by programme
**Risk Register** — Probability × Impact matrix with mitigations
**Partnership Assessment** — Opportunity evaluation matrix

### Visual Outputs

Include Mermaid diagrams for:
- Timeline views (Gantt-style)
- Decision trees
- Technology roadmaps
- Competitive positioning matrices

### Excel-Compatible Tables

Financial tables formatted for easy spreadsheet import:
- Cash flow projections
- Investment schedules
- Break-even analysis
- Sensitivity tables

## Low-Volume Economics

| Factor | Mass Market | Low Volume (<5k/year) | Ultra-Low (<500/year) |
|--------|-------------|----------------------|----------------------|
| Tooling amortisation | Spread across millions | Heavy per-unit burden | Critical constraint |
| Supplier leverage | Volume discounts | Premium pricing | Bespoke relationships |
| Certification cost/unit | Negligible | Significant | May drive architecture |
| Platform sharing | Essential | Often limited | Usually impossible |
| Development cycles | 4-6 years | 2-4 years | <2 years possible |
| Pricing power | Market-driven | Brand premium possible | Full margin control |

## Technology Pathways

### Powertrain Options

| Technology | Maturity | Best For | Key Risks |
|------------|----------|----------|-----------|
| ICE (naturally aspirated) | Mature | Driving purity, heritage | Regulatory sunset |
| ICE (forced induction) | Mature | Performance, efficiency | Compliance tightening |
| Mild Hybrid (MHEV) | Mature | Compliance bridge | Limited benefit |
| Plug-in Hybrid (PHEV) | Mature | Market flexibility | Complexity, weight |
| Battery Electric (BEV) | Maturing | Future-proof, performance | Weight, range, cost |
| Hydrogen (FCEV) | Emerging | Long-range, fast refuel | Infrastructure, cost |
| E-fuels (synthetic) | Emerging | ICE preservation | Cost, availability |

### Motorsport Technology Transfer

Racing programmes can accelerate production technology:
- Aerodynamics validation
- Lightweight materials proving
- Powertrain development
- Electronics/software validation
- Brand positioning

**Transfer timeline**: Typically 2-3 years from competition debut to production application.

## Regulatory Reference

See `references/regulatory-calendar.md` for detailed compliance timeline.

**Key dates affecting planning:**
- Euro 7: July 2025 (new types)
- UK ICE ban: 2030 (hybrids to 2035)
- EU CO2 targets: -55% by 2030 vs 2021
- US EPA tightening: Through 2027

**Small volume provisions** reduce compliance burden below certain thresholds.

## Key Principles

1. **Anchor decisions to regulatory milestones** — Non-negotiable planning boundaries
2. **Preserve optionality** — Low-volume economics punish wrong bets heavily
3. **Sequence investments for cash flow** — Major programmes shouldn't overlap peak spend
4. **Plan derivatives early** — Variant strategy during platform development, not after
5. **Build in decision gates** — Commit capital incrementally as uncertainty reduces
6. **Leverage heritage assets** — Brand history is a competitive advantage
7. **Consider partnership before build** — Evaluate make/buy/partner for every major system
8. **Link to operational execution** — Strategy without cascade is just a document

## Quick Reference Commands

```
# Full planning cycle
"Create 5-year product plan for [company description]"

# Specific analyses
"Analyse competitive positioning for [segment]"
"Evaluate powertrain options for [programme]"
"Assess partnership opportunity with [OEM/supplier]"
"Model financial returns for [programme]"

# Integration
"Cascade product strategy to hoshin objectives"
"Create supplier development plan for [programme]"
"Build APQP timeline for [programme] SOP [date]"
```
