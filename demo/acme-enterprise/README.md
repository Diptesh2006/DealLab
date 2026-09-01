# ACME Enterprise Demo Dataset

Synthetic demo data for DealLab. These files are not real contracts and must not be treated as legal or financial advice.

## Story

- Provider: AsterGrid AI Infrastructure Pvt. Ltd.
- Customer: ACME Enterprise Pvt. Ltd.
- Deal: AsterGrid Enterprise API Platform
- Base price: INR 30,00,000 per year
- Included usage: 1M API units per month, normalized to 12M units per year
- Overage: INR 0.20 per unit
- Overage ceiling: INR 1,00,000 per month
- Introductory discount: 15% for 3 months
- Support: broad support obligation, interpreted as unlimited for the initial term
- Renewal: 8% uplift in the master agreement; Amendment 1 waives the first renewal increase only
- SLA: 99.5% monthly availability with 5% service credits

## Internal Assumptions

The assumptions are tuned to make the deal look acceptable in the expected case but fragile under combined stress:

- Variable API serving cost: INR 0.01 per call
- Monthly infrastructure cost: INR 60,000
- Support cost/hour: INR 1,200
- Implementation expense: INR 1,50,000
- Target gross margin: 55%
- Typical support consumption: 120 hours/year
- Expected annual cost inflation: 4%

## Benchmark

`expected-benchmark-outputs.json` is generated from the deterministic backend engine.

Current deal:

- Deal health: Commercially Fragile
- Healthy scenarios: 50%
- Expected margin: 59.68%
- Downside margin: 33.76%
- Annual exposure: INR 9,06,958.20

Best zero-base-price optimization in the benchmark:

- Remove monthly overage cap
- Increase overage price from INR 0.20/unit to INR 0.35/unit
- Healthy scenarios improve from 50% to 80%

## Files

- `contract.pdf` and `contract.txt`: synthetic master agreement
- `amendment-1.pdf` and `amendment-1.txt`: first-renewal waiver
- `approved-exception.pdf` and `approved-exception.txt`: approved temporary discount exception
- `effective-terms.json`: normalized effective commercial terms
- `cost-assumptions.json`: internal finance assumptions
- `sample-scenarios.json`: demo scenario inputs
- `expected-benchmark-outputs.json`: deterministic benchmark output

Regenerate PDFs and benchmark output with:

```bash
python scripts/generate_demo_assets.py
```
