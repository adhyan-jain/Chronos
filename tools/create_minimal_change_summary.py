"""Create a one-page, local-only summary of the manuscript revisions."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/docs/Revon_Minimal_Changes_Summary.pdf"
CHANGES = (
    "Added a dedicated Revon-H versus Revon-M comparison, retaining adverse and inconclusive findings.",
    "Tested five switching thresholds using separate calibration and held-out workloads; no universal optimum is claimed.",
    "Corrected storage attribution and reported measured H/M footprints and retained changesets.",
    "Consolidated dataset provenance, environments, timing, correctness and statistical methods.",
    "Replaced the decision diagram with the implemented ancestry, threshold and fallback logic.",
    "Restricted claims and clarified that diff selection adapts while trie geometry remains fixed.",
    "Verified 31 numbered, cited references and reviewed source attribution and prose.",
    "Produced Discover Computing and IEEE editions, repaired pagination and archived older versions.",
)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm, topMargin=24*mm, bottomMargin=22*mm,
        title="Revon: Minimal Revision Summary", author="Revon authors")
    title = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=18,
        leading=23, textColor=colors.HexColor("#17364A"), spaceAfter=10)
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=11,
        leading=16, spaceAfter=10)
    label = ParagraphStyle("Label", parent=body, fontName="Helvetica-Bold", spaceBefore=10)
    story = [Paragraph("Revon: Minimal Revision Summary", title),
        Paragraph("2 October 2026", body),
        Paragraph("Adaptive Merkle Trie Versioning for Efficient Structured Data Management", label),
        Spacer(1, 5*mm)]
    story.extend(Paragraph(f"{number}. {text}", body) for number, text in enumerate(CHANGES, 1))
    story.extend([
        Paragraph("Still outstanding", label),
        Paragraph("Independent Linux hardware replication, author-confirmed declarations and public release of the new evidence. Threshold generalization remains uncertain.", body),
        Paragraph("Ready for supervisor review; further work is required before journal submission. The source review does not certify plagiarism clearance or AI authorship.", body),
    ])
    document.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
