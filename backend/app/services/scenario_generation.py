from backend.app.models.deal import CommercialTerms, Scenario


def generate_stress_scenarios(terms: CommercialTerms) -> list[Scenario]:
    scenarios = [
        Scenario(
            name="Base case",
            revenue_multiplier=1.0,
            cost_multiplier=1.0,
            support_cost_multiplier=1.0,
            description="Commercial terms perform as contracted.",
        ),
        Scenario(
            name="Low adoption",
            revenue_multiplier=0.82 if terms.usage_commitment == 0 else 0.9,
            cost_multiplier=0.95,
            support_cost_multiplier=1.05,
            description="Customer consumption lands below forecast while support obligations remain.",
        ),
        Scenario(
            name="High service load",
            revenue_multiplier=1.0,
            cost_multiplier=1.22,
            support_cost_multiplier=1.35,
            description="Implementation and support intensity exceed plan.",
        ),
        Scenario(
            name="Late payment pressure",
            revenue_multiplier=0.97,
            cost_multiplier=1.04,
            support_cost_multiplier=1.0,
            description="Extended payment terms create working-capital drag.",
        ),
    ]
    return scenarios
