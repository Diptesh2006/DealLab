from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.models.economics import CompanyAssumptions
from backend.app.models.intelligence import EffectiveTerm
from backend.app.optimization.deal_optimizer import optimize_deal, prepare_revised_terms
from backend.app.simulation.stress import run_stress_test


DEMO_DIR = ROOT / "demo" / "acme-enterprise"


def main() -> None:
    _generate_pdfs()
    _generate_benchmarks()


def _generate_pdfs() -> None:
    for source_name, pdf_name, title in [
        ("contract.txt", "contract.pdf", "DealLab Demonstration Agreement"),
        ("amendment-1.txt", "amendment-1.pdf", "Amendment 1"),
        ("approved-exception.txt", "approved-exception.pdf", "Approved Commercial Exception"),
    ]:
        source = DEMO_DIR / source_name
        target = DEMO_DIR / pdf_name
        _write_pdf(source.read_text(encoding="utf-8"), target, title)


def _write_pdf(text: str, target: Path, title: str) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "DemoBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#17202a"),
        spaceAfter=6,
    )
    heading = ParagraphStyle(
        "DemoHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#17202a"),
        spaceAfter=12,
    )
    warning = ParagraphStyle(
        "DemoWarning",
        parent=body,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#8a5a00"),
    )

    story = [Paragraph(title, heading)]
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    for index, paragraph in enumerate(paragraphs):
        style = warning if index == 0 and paragraph.startswith("SYNTHETIC") else body
        story.append(Paragraph(paragraph.replace("\n", "<br/>"), style))
        story.append(Spacer(1, 2 * mm))

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="DealLab synthetic demo generator",
    )
    doc.build(story)


def _generate_benchmarks() -> None:
    terms = [EffectiveTerm(**item) for item in json.loads((DEMO_DIR / "effective-terms.json").read_text(encoding="utf-8"))]
    assumptions = CompanyAssumptions(**json.loads((DEMO_DIR / "cost-assumptions.json").read_text(encoding="utf-8"))["assumptions"])
    scenario_config = json.loads((DEMO_DIR / "sample-scenarios.json").read_text(encoding="utf-8"))

    stress = run_stress_test(
        terms,
        assumptions,
        expected_usage_units=scenario_config["expected_usage_units"],
        expected_usage_revenue=scenario_config["expected_usage_revenue"],
    )
    optimization = optimize_deal(
        terms,
        assumptions,
        expected_usage_units=scenario_config["expected_usage_units"],
        expected_usage_revenue=scenario_config["expected_usage_revenue"],
        max_changed_clauses=2,
    )
    revised_terms = prepare_revised_terms(optimization.options[0]) if optimization.options else None

    benchmark = {
        "synthetic_demo_data": True,
        "health": stress.health.model_dump(mode="json"),
        "scenario_margins": [
            {
                "scenario": item.scenario.name,
                "gross_margin_percent": item.economics.gross_margin_percent,
                "downside_exposure": item.economics.downside_exposure,
                "status": item.status,
            }
            for item in stress.scenarios
        ],
        "top_failure_modes": [mode.model_dump(mode="json") for mode in stress.failure_modes[:3]],
        "optimization": optimization.model_dump(mode="json"),
        "prepared_revised_terms": revised_terms.model_dump(mode="json") if revised_terms else None,
        "tuning_note": (
            "The synthetic economics are tuned so the expected case is acceptable, while high adoption, "
            "support intensity, and combined downside scenarios expose commercial fragility."
        ),
    }
    (DEMO_DIR / "expected-benchmark-outputs.json").write_text(
        json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
