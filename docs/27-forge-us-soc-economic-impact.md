# ThinkingSOC Forge — U.S. SOC capacity and economic impact

This document provides a reproducible way to estimate how ThinkingSOC Forge could affect analyst workload, investigation throughput, and SOC operating capacity in the United States. It is a planning model—not a fabricated customer case, guaranteed saving, or claim that one demo proves production ROI.

The model deliberately separates:

1. **external facts** from named sources;
2. **organization-specific planning assumptions** that must be edited;
3. **observed Forge metrics** captured from live evidence artifacts.

## 1. Executive example

Consider a six-analyst U.S. private-sector SOC. Assume it sees 30 repeat investigations per business day that are covered by an approved exact-detection Forge runbook. If the measured manual baseline is 25 minutes and the complete Forge-assisted handling time—including analyst review—is 5 minutes, then:

- 7,800 eligible repeat investigations occur per year;
- 2,600 analyst hours are returned per year;
- that equals 1.25 standard 2,080-hour FTEs of capacity;
- using the wage-derived loaded rate below, gross annual capacity value is about **$223,000**;
- the eligible repeat lane uses one-fifth of its former time, a theoretical **5× throughput** for that lane;
- the returned time can support about **6,240 additional 25-minute manual-equivalent investigations** per year.

If the organization enters a hypothetical $60,000 annual incremental platform/model/operations cost, the planning model produces about $163,000 net capacity value, 272% ROI, and 3.2-month payback. The $60,000 input is not a known ThinkingSOC production price; it exists to demonstrate the calculation and must be replaced with the buyer's actual fully loaded cost.

## 2. External U.S. data inputs

### Analyst wage

The U.S. Bureau of Labor Statistics (BLS) reports that information security analysts had:

- **$124,910 median annual wage** in May 2024;
- **$60.05 median hourly wage**;
- projected **29% employment growth from 2024 to 2034**;
- approximately **16,000 openings per year** over that period.

Source: [BLS Occupational Outlook Handbook — Information Security Analysts](https://www.bls.gov/ooh/computer-and-information-technology/information-security-analysts.htm).

The BLS role is broader than a Tier 1/2 SOC analyst, and local market, seniority, shift, clearance, industry, and metro area can materially change compensation. Replace this national median with the organization's actual payroll rate whenever possible.

### Employer benefits and loaded labor cost

BLS Employer Costs for Employee Compensation for March 2026 reports private-industry compensation of:

- **$32.60/hour wages and salaries**, or **69.9%** of compensation;
- **$14.01/hour benefits**, or **30.1%**;
- **$46.60/hour total compensation** across private-industry workers.

Source: [BLS ECEC Table 1 — March 2026](https://www.bls.gov/news.release/ecec.t01.htm).

This document uses the 69.9% wage share as a planning multiplier:

```text
base hourly wage = $124,910 / 2,080 = $60.05
loaded hourly proxy = $60.05 / 0.699 = $85.91
loaded annual proxy = $85.91 × 2,080 = $178,698
```

This combines an occupation-specific wage with an all-private-industry benefit ratio. It is a transparent proxy, not an exact accounting figure. A real business case should use salary, payroll tax, benefits, paid leave, shift differential, overtime, management overhead, and contractor cost from finance/HR.

### SOC workload context

Splunk's State of Security 2025 reports that surveyed security teams said:

- 59% had too many alerts;
- 55% dealt with too many false positives;
- 57% lost investigation time because of data-management gaps;
- 59% reported moderate or significant SOC efficiency improvement from AI.

Source: [Splunk State of Security 2025](https://www.splunk.com/en_us/campaigns/state-of-security.html).

This vendor survey explains why repeated investigation work matters, but its percentages are not inserted into the ROI formula. The financial model uses only measured local volume and time.

## 3. Product metrics used by the model

Forge persists the following operational evidence:

| Metric | Source | Use |
|---|---|---|
| `duration_ms` | `verified_runbook_run` | Observed target-run automation time |
| `estimated_manual_minutes` | Analyst-entered visible baseline | Manual comparison input |
| `estimated_minutes_saved` | Deterministic calculation | Per-run capacity returned |
| `savings_percent` | Deterministic calculation | Per-run relative reduction |
| `status` | Parser/execution evidence | Count only valid outcomes according to policy |
| `successful_step_count` | Target execution | Detect partial/failed procedures |
| `total_evidence_rows` | Target execution | Evidence-yield monitoring |
| model/token metadata | Draft artifact | Model governance and variable-cost analysis |

The evidence pack captures these values in `10_forge_target_run.json` and `11_forge_metrics.json`. The model should prefer observed medians or percentiles over a single fastest demo run.

## 4. Core formulas

Define:

```text
D = eligible compatible repeat investigations per business day
W = business days per year
M = measured median manual minutes per eligible investigation
A = measured median Forge-assisted minutes, including analyst review
H = loaded analyst cost per hour
C = annual incremental Forge cost
N = number of SOC analysts
```

Then:

```text
eligible_runs_year = D × W
hours_saved_year = eligible_runs_year × max(0, M - A) / 60
fte_capacity_returned = hours_saved_year / 2,080
gross_capacity_value = hours_saved_year × H
net_planning_value = gross_capacity_value - C
roi_percent = net_planning_value / C × 100
payback_months = C / gross_capacity_value × 12
eligible_lane_speedup = M / A
team_capacity_share_returned = hours_saved_year / (N × 2,080) × 100
```

If `C` is zero or unknown, do not report ROI or payback; report hours and gross capacity only.

## 5. Reproducible six-analyst example

### Inputs

| Input | Value | Classification |
|---|---:|---|
| SOC analysts (`N`) | 6 | Example assumption |
| Eligible repeats/day (`D`) | 30 | Example assumption; must come from local alert history |
| Business days/year (`W`) | 260 | Planning convention |
| Manual minutes (`M`) | 25 | Example assumption; product default, must be validated from tickets/time study |
| Forge-assisted minutes (`A`) | 5 | Example assumption; must be replaced by evidence-pack median including review |
| Loaded analyst cost/hour (`H`) | $85.91 | Derived from BLS inputs above |
| Annual incremental cost (`C`) | $60,000 | Example assumption; replace with actual platform/model/operations cost |

### Calculation

```text
eligible runs/year = 30 × 260 = 7,800
manual hours/year = 7,800 × 25 / 60 = 3,250
Forge-assisted hours/year = 7,800 × 5 / 60 = 650
hours returned/year = 3,250 - 650 = 2,600
FTE capacity returned = 2,600 / 2,080 = 1.25
gross capacity value = 2,600 × $85.91 = $223,373
net planning value = $223,373 - $60,000 = $163,373
ROI = $163,373 / $60,000 × 100 = 272%
payback = $60,000 / $223,373 × 12 = 3.2 months
team capacity returned = 2,600 / (6 × 2,080) = 20.8%
eligible lane speedup = 25 / 5 = 5×
```

### Operational interpretation

Before Forge, the 30 repeat cases consume 12.5 analyst-hours per day. Under the 5-minute assisted assumption, they consume 2.5 analyst-hours, returning 10 hours each business day across the team.

That does not automatically remove 1.25 people from payroll. It creates capacity that may be used to:

- investigate more alerts that previously waited or aged out;
- move analysts from repetitive collection into higher-risk cases;
- reduce overtime, contractor demand, or future hiring pressure;
- standardize evidence and reduce senior-review rework;
- shorten onboarding time for analysts handling known detection families.

It becomes cash saving only when the organization demonstrably reduces overtime, outsourced volume, vacancies, or other budgeted spend.

## 6. Volume sensitivity

Assume 20 minutes saved, 260 business days, and $85.91/hour loaded cost.

| Eligible repeats/day | Hours returned/year | FTE capacity | Gross capacity value/year |
|---:|---:|---:|---:|
| 10 | 867 | 0.42 | $74,458 |
| 30 | 2,600 | 1.25 | $223,373 |
| 60 | 5,200 | 2.50 | $446,745 |

At a hypothetical $60,000 annual incremental cost, break-even occurs at approximately **8.1 eligible repeat investigations per business day**:

```text
break-even D = C / (W × (M - A) / 60 × H)
             = 60,000 / (260 × 20/60 × 85.91)
             = 8.1 repeats/day
```

This sensitivity is more credible than applying a savings percentage to all SOC alerts. Forge only creates value on alerts with an approved, compatible runbook.

## 7. Throughput without double counting

For the eligible lane:

```text
manual throughput per analyst-hour = 60 / 25 = 2.4 investigations
Forge-assisted throughput per analyst-hour = 60 / 5 = 12 investigations
lane multiplier = 12 / 2.4 = 5×
```

The six-analyst example returns 2,600 hours. At the original 25-minute handling time, that is capacity for up to:

```text
2,600 × 60 / 25 = 6,240 additional manual-equivalent investigations/year
```

Do not add both the $223,373 labor-capacity value and a separate dollar value for 6,240 extra investigations; they are two views of the same returned time.

## 8. What must be measured in a real SOC

Use at least a 30-day pilot and report both median and p90 where possible.

### Baseline

- count alerts by exact `search_name`;
- count how many have complete `soc_analysis` evidence and are eligible for a runbook;
- measure hands-on time from ticket timestamps or a time study;
- separate wait time from analyst work time;
- record escalations, rework, and senior-review minutes;
- capture overtime or outsourced-case unit cost if cash savings are claimed.

### Forge pilot

- compile only acknowledged, non-benign source investigations;
- require human approval;
- count `REUSED`, `NO_EVIDENCE`, and `FAILED` separately;
- include approval/review time in assisted handling time;
- count model, Splunk, infrastructure, support, and governance cost;
- audit whether target evidence supports the analyst's final disposition;
- do not treat zero-row or failed runs as successful savings without measuring the analyst work they still required.

### Recommended KPIs

| KPI | Formula |
|---|---|
| Eligible coverage | alerts with approved compatible runbook / total alerts |
| Reuse success rate | `REUSED` / attempted target runs |
| No-evidence rate | `NO_EVIDENCE` / attempted target runs |
| Failure rate | `FAILED` / attempted target runs |
| Median minutes returned | median(`manual_minutes - assisted_minutes`) |
| Analyst acceptance | approved suggestions used without material rewrite / reviewed runs |
| Rework rate | runs requiring new SPL or manual restart / attempted runs |
| Cost per successful reuse | total Forge operating cost / `REUSED` runs |
| Evidence yield | total evidence rows / successful steps, reported with truncation context |

## 9. Conservative business-case policy

Count financial value only when all of the following are true:

1. the target belongs to an approved exact-match runbook;
2. execution is `REUSED` under deterministic evidence rules;
3. analyst review is included in assisted time;
4. the manual baseline comes from local operations rather than the model;
5. failures, no-evidence runs, and rework are included in total cost;
6. platform/model/engineering/governance costs are included;
7. capacity value is not mislabeled as cash saving;
8. avoided-breach value is excluded unless supported by a separate risk model and real incident data.

## 10. What this example proves—and does not prove

It proves that a buyer can reproduce the economics from official wage data, local alert volume, and live Forge timing artifacts. It shows the size of the opportunity when repeated alert families consume meaningful analyst time.

It does not prove that every SOC will save $223,000, that every alert will be five times faster, that false positives will fall by a fixed percentage, or that the feature prevents a breach. Those require a production pilot with labeled outcomes.

## 11. Sources and refresh policy

Sources accessed July 15, 2026:

- [U.S. Bureau of Labor Statistics — Information Security Analysts](https://www.bls.gov/ooh/computer-and-information-technology/information-security-analysts.htm)
- [U.S. Bureau of Labor Statistics — Employer Costs for Employee Compensation, March 2026, Table 1](https://www.bls.gov/news.release/ecec.t01.htm)
- [Splunk — State of Security 2025](https://www.splunk.com/en_us/campaigns/state-of-security.html)

Refresh BLS wage and compensation inputs before presenting the business case in a later year. Preserve the source date alongside every exported ROI result.

## 12. Related documents

- [Technical implementation](./25-verified-runbook-forge.md)
- [Hackathon product and demo guide](./26-hackathon-forge-product-guide.md)
- [Submission evidence generator](../submission/README.md)
- [Hackathon change log](../HACKATHON_CHANGELOG.md)
