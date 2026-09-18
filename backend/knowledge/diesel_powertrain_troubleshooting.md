# Heavy Diesel Engine Powertrain Diagnostic Reference
## Common Rail Engines (Cummins, Isuzu, Cat, Weichai, Perkins)

### 1. Exhaust Smoke Color Troubleshooting Matrix

#### A. Black Smoke (Incomplete Fuel Combustion / Excessive Fuel-to-Air Ratio)
- **Primary Causes**:
  1. *Air Induction Restriction*: Air cleaner primary filter element saturated with site dust; turbocharger compressor wheel coated in oil/carbon.
  2. *Charge Air Cooler (CAC) Leak*: Ruptured silicone elbow or split aluminum end tank seam (audible hiss under load). Boost pressure falls below target.
  3. *Fuel Injector Nozzle Erosion*: Injector spray holes enlarged or needle seat worn, causing droplet dribble rather than fine atomization.
  4. *Exhaust Gas Recirculation (EGR) Valve Stuck Open*: Inert exhaust gas continuously dilutes combustion chamber oxygen.
- **Diagnostic Action**: Inspect air filter restriction indicator gauge. Perform CAC pressure decay test (charge to 2.0 bar and observe hold). Run cylinder cutout test on diagnostic scan tool to identify offending cylinder.

#### B. White Smoke (Unburned Fuel Vapor or Coolant Vapor)
- **Primary Causes**:
  1. *Coolant Ingress (Sweet Odor, Persistent Steam)*: Blown cylinder head gasket fire ring, cracked cylinder liner, or leaking EGR cooler tube bundle.
  2. *Cold Cylinder / Late Injection Timing (Pungent Acrid Diesel Odor)*: Low cylinder compression (<22 bar), faulty glow plug or intake grid heater, cracked injector pintle tip dumping raw fuel that fails to ignite.
- **Diagnostic Action**:
  - Test for combustion gas in coolant expansion tank (chemical block test or bubble test via overflow tube submerged in clear water).
  - Check engine oil level: If oil level is rising, unburned diesel or coolant is diluting crankcase.

#### C. Blue Smoke (Lubricating Engine Oil Combustion)
- **Primary Causes**:
  1. Turbocharger turbine/compressor journal bearing oil seals blown (check intake piping and exhaust downpipe for wet oil pools).
  2. Worn valve guides and hardened valve stem oil seals.
  3. Worn or stuck piston compression and oil scraper rings, glazed cylinder liners (crankcase blow-by pressure elevated >100 mm H2O).
- **Diagnostic Action**: Measure crankcase blow-by with a differential manometer connected to oil filler neck or dipstick tube while machine digs at full power.

---

### 2. Common Rail Fuel System Hard Start / No Start Diagnostics
- **Minimum Cranking Parameters Required for ECM to Authorize Injection**:
  - Cranking Speed: Minimum 150 - 180 RPM.
  - Common Rail Fuel Pressure: Minimum 250 - 300 bar (3600 - 4350 psi).
  - Camshaft / Crankshaft Sensor Sync: Signal pulse synchronized without timing jitter.
- **Troubleshooting Steps**:
  1. Verify low-pressure fuel supply: Lift pump delivery pressure must maintain 4.0 - 6.0 bar before the high-pressure pump inlet.
  2. Check for air in fuel system: Bleed fuel system at primary filter hand primer pump until clear fuel emerges without froth from bleeder screw.
  3. Perform Common Rail Injector Static Leak-off Test: Disconnect injector return lines. Crank engine for 10 seconds. Excessive return fuel (>5-10 ml per injector) reveals a worn internal control valve leaking rail pressure to tank.
