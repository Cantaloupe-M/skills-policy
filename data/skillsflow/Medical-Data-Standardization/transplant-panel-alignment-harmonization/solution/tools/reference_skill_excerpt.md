---
name: pie-dimensional-analysis
version: 1.0.0
description: "Mathematical verification for physical calculations: unit tracking algebra (exponent maps), PhysicalQuantity pattern for compound units, SI/Imperial mixed-unit handling, Buckingham pi theorem for dimensionless groups, and common engineering dimensionless numbers. Activates for unit verification, dimensional consistency checks, scaling analysis, and calculation validation across all infrastructure domains."
user-invocable: true
allowed-tools: Read Grep Glob Bash
metadata:
  extensions:
    gsd-skill-creator:
      version: 1
      createdAt: "2026-02-26"
      triggers:
        intents:
          - "unit conversion"
          - "unit tracking"
          - "dimensional analysis"
          - "dimensionless"
          - "Reynolds number"
          - "Nusselt number"
          - "Buckingham pi"
          - "scaling"
          - "unit check"
          - "SI"
          - "imperial"
          - "unit mismatch"
          - "physical quantity"
        contexts:
          - "calculation verification"
          - "infrastructure engineering"
          - "unit algebra"
          - "dimensional homogeneity"
applies_to:
  - skills/physical-infrastructure/**
  - lib/units.ts
---

# Dimensional Analysis Skill

## At a Glance

Dimensional analysis is the mathematical verification layer that ensures physical calculations are dimensionally consistent -- catching unit errors before they become calculation errors.

**When to activate:**
- Verify multi-step calculations for unit consistency
- Mix SI and Imperial units in the same calculation
- Scale experimental data to new conditions via dimensionless groups
- Identify governing parameters of a physical system
- Validate Calculator agent outputs before committing to CalculationRecord

**Key capabilities:**
- Unit tracking via exponent maps (PhysicalQuantity pattern)
- Compound unit algebra: multiply, divide, power, dimensional homogeneity
- Dimensional mismatch detection at every arithmetic step
- SI to Imperial conversion for all infrastructure engineering domains
- Buckingham pi theorem for deriving dimensionless groups
- Infrastructure dimensionless numbers: Reynolds, Nusselt, Prandtl, Grashof, Froude, Strouhal

**Integration:** Cross-cutting skill -- applies to outputs from fluid-systems, power-systems, and thermal-engineering. Acts as verification layer before Calculator agent commits to CalculationRecord.

> **NOTE:** Dimensional analysis verifies mathematical self-consistency only. It does not replace engineering judgment or safety verification. Dimensionally correct equations can still be physically wrong if incorrect constants or assumptions are used.

**Quick routing:**
- Unit conversions only --> @references/unit-algebra.md for full tables
- Pi theorem derivation --> @references/buckingham-pi.md for worked examples
- Tolerance stack-up --> see Tolerance Stack-Up Analysis section below
- Spatial fit checking --> see Spatial Constraint Verification section below

---

## Unit Tracking Algebra

### The Seven SI Base Units

| Symbol | Quantity | Notes |
|--------|----------|-------|
| m | length | meter |
| kg | mass | kilogram (only SI base unit with a prefix) |
| s | time | second |
| A | electric current | ampere |
| K | temperature | kelvin (absolute; not degrees Celsius) |
| mol | amount of substance | mole |
| cd | luminous intensity | candela (rarely used in infrastructure) |

### Compound Units as Exponent Maps

Every physical quantity carries its unit as a map of base unit exponents. This representation makes unit algebra mechanical -- multiply means add exponents, divide means subtract.

Examples:
- Velocity: 2.4 m/s --> `{ value: 2.4, units: { m: 1, s: -1 } }`
- Pressure: 101325 Pa --> `{ value: 101325, units: { kg: 1, m: -1, s: -2 } }`
- Power: 1000 W --> `{ value: 1000, units: { kg: 1, m: 2, s: -3 } }`
- Thermal conductivity: 385 W/(m*K) --> `{ value: 385, units: { kg: 1, m: 1, s: -3, K: -1 } }`

### Common Infrastructure Units -- Exponent Map Reference

| Quantity | SI Unit | Symbol | Exponent Map |
|----------|---------|--------|-------------|
| Force | Newton | N | { kg:1, m:1, s:-2 } |
| Pressure | Pascal | Pa | { kg:1, m:-1, s:-2 } |
| Energy | Joule | J | { kg:1, m:2, s:-2 } |
| Power | Watt | W | { kg:1, m:2, s:-3 } |
| Dynamic viscosity | -- | Pa*s | { kg:1, m:-1, s:-1 } |
| Heat transfer coeff | -- | W/(m^2*K) | { kg:1, s:-3, K:-1 } |
| Thermal conductivity | -- | W/(m*K) | { kg:1, m:1, s:-3, K:-1 } |

### The PhysicalQuantity Interface

The Calculator agent implements unit-safe arithmetic using this TypeScript pattern. The SKILL documents the knowledge; `lib/units.ts` provides the implementation.

```typescript
interface PhysicalQuantity {
  value: number;
  units: { [baseUnit: string]: number }; // exponent map
}

function multiply(a: PhysicalQuantity, b: PhysicalQuantity): PhysicalQuantity {
  const result: PhysicalQuantity = { value: a.value * b.value, units: { ...a.units } };
  for 