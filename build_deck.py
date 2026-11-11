"""Build the Part D slides in the same visual style as the team deck (Midterm Project_GenAI.pptx).

Reads ../PartD_results/*.csv; anything not yet measured is shown as 'pending', never invented.
Output: ../PartD_results/PartD_slides.pptx (paste into the shared deck, or import slides in Google Slides).
"""
import csv
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "PartD_results"
TEMPLATE = ROOT / "Midterm Project_GenAI.pptx"
SHOT = RES / "ui_screenshot.png"

MAROON, TEAL, GRAY, INK = "800000", "136571", "636363", "232323"
LIGHT, PINK, WHITE = "F1F5F6", "F8F2F2", "FFFFFF"
LABEL = "Part D  |  Front End, Deployment & Evaluation"


def rgb(h):
    return RGBColor.from_string(h)


def text(slide, x, y, w, h, s, size=11, bold=False, color=INK, align=None):
    tb = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    for i, line in enumerate(s.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.name, r.font.size, r.font.bold = "Arial", Pt(size), bold
        r.font.color.rgb = rgb(color)
        if align:
            p.alignment = align
    return tb


def box(slide, x, y, w, h, fill):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x), Emu(y), Emu(w), Emu(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.fill.background()
    return s


def frame(prs, title, n):
    blank = [l for l in prs.slide_layouts if l.name == "BLANK"][0]
    s = prs.slides.add_slide(blank)
    text(s, 480073, 240030, 8229819, 685800, title, 23, True, MAROON)
    text(s, 315476, 4876038, 4500000, 137160, LABEL, 8, False, GRAY)
    text(s, 8709892, 4869180, 200000, 171450, str(n), 8, False, GRAY)
    return s


def bullets(slide, x, y, w, items, size=11, gap=300000):
    for i, it in enumerate(items):
        text(slide, x, y + i * gap, w, 274320, "• " + it, size)


def read(name):
    p = RES / name
    return list(csv.DictReader(open(p))) if p.is_file() else None


def mean(rows, key):
    vals = [float(r[key]) for r in rows if r[key] != ""]
    return sum(vals) / len(vals) if vals else 0.0


def main(first_no, merge=False):
    prs = Presentation(str(TEMPLATE))
    ids = prs.slides._sldIdLst
    if merge:
        first_no = len(ids) + 1  # append after the team's existing slides
    else:
        for sld in list(ids):  # drop the team's slides, keep master/layouts/theme
            prs.part.drop_rel(sld.rId)
            ids.remove(sld)

    # ---- 1. architecture ----
    s = frame(prs, "Part D: System Design & User Interface", first_no)
    text(s, 514364, 994410, 5000000, 240030, "END-TO-END PIPELINE", 14, True, TEAL)
    steps = [("STREAMLIT UI", "Chat box, suggested questions"), ("RETRIEVE (B)", "MiniLM + ChromaDB top-5"),
             ("GENERATE (C)", "gpt-4.1-mini + quotes"), ("REVIEW (C)", "Entailment check")]
    x = 445782
    for i, (a, b) in enumerate(steps):
        box(s, x, 1405889, 1850000, 768096, LIGHT)
        text(s, x + 82000, 1563623, 1700000, 212598, a, 12, True, TEAL)
        text(s, x + 82000, 1865376, 1700000, 205740, b, 8, False, GRAY)
        if i < 3:
            text(s, x + 1855000, 1639062, 205745, 240030, "→", 16, True, TEAL)
        x += 2060000
    text(s, 548655, 2503170, 3900000, 240030, "What the user sees", 14, True, TEAL)
    bullets(s, 548655, 2846070, 3900000, [
        "Answer plus clickable source links",
        "Expandable list of retrieved passages",
        "Clear message for refusals / clarifications",
        "Suggested questions, one tap to ask"], gap=329000)
    text(s, 4800728, 2503170, 3900000, 240030, "Design decisions", 14, True, TEAL)
    bullets(s, 4800728, 2846070, 3900000, [
        "Calls Part C's answer(query) unchanged",
        "Handles all 7 response statuses",
        "Identical questions served from cache",
        "Per-session question cap bounds API cost"], gap=329000)
    box(s, 548655, 4354830, 8024074, 308610, PINK)
    text(s, 685818, 4409694, 7700000, 171450,
         "Single-turn by design: Part C keeps no chat history, so each question is answered independently.",
         10, True, MAROON)

    # ---- 2. deployment ----
    s = frame(prs, "Part D: Deployment & Operations", first_no + 1)
    text(s, 514364, 994410, 4000000, 240030, "DEPLOYMENT", 14, True, TEAL)
    cards = [("Streamlit app", "Python 3.12, deps pinned to the versions Part C was built with"),
             ("Streamlit Community Cloud", "Free hosting from a GitHub repo; public URL for DSI staff"),
             ("Secrets", "OPENAI_API_KEY stored in the platform secrets, never in code")]
    y = 1300000
    for a, b in cards:
        box(s, 514364, y, 8024074, 560000, LIGHT)
        text(s, 672102, y + 90000, 2300000, 171450, a, 12, True, TEAL)
        text(s, 3000000, y + 110000, 5400000, 300000, b, 11)
        y += 650000
    text(s, 514364, 3300000, 4000000, 240030, "OPERATIONAL SAFEGUARDS", 14, True, TEAL)
    bullets(s, 548655, 3640000, 3900000, ["Knowledge base and models cached after first load",
                                          "Answer cache (1 h) for repeated questions"], gap=300000)
    bullets(s, 4800728, 3640000, 3900000, ["Session cap on questions (default 40)",
                                           "Graceful error text if the LLM API fails"], gap=300000)
    box(s, 548655, 4354830, 8024074, 308610, PINK)
    text(s, 685818, 4409694, 7700000, 171450, "Live URL: <paste app URL here>", 10, True, MAROON)

    # ---- 3. evaluation ----
    s = frame(prs, "Part D: Evaluation on the 12-Question Test Set", first_no + 2)
    ret, e2e = read("retrieval_eval.csv"), read("e2e_eval.csv")
    text(s, 514364, 946404, 6000000, 240030, "RETRIEVAL (TOP-5) AND END-TO-END ANSWERS", 14, True, TEAL)
    box(s, 548655, 1300000, 8024074, 308610, TEAL)
    for x, h in ((699535, "METRIC"), (5000000, "RETRIEVAL"), (6900000, "FULL ANSWER")):
        text(s, x, 1376000, 1800000, 137160, h, 10, True, WHITE)
    n = len(ret) if ret else 12
    pend = "pending"
    rows = [
        ("Source hit (right page cited / in top-5)",
         f"{sum(int(r['source_hit@5']) for r in ret)}/{n}" if ret else pend,
         f"{sum(int(r['source_hit']) for r in e2e)}/{len(e2e)}" if e2e else pend),
        ("Questions with all key facts",
         f"{sum(int(r['all_facts_in_top5']) for r in ret)}/{n}" if ret else pend,
         f"{sum(int(r['all_facts']) for r in e2e)}/{len(e2e)}" if e2e else pend),
        ("Mean key-fact recall",
         f"{mean(ret, 'fact_recall@5'):.2f}" if ret else pend,
         f"{mean(e2e, 'fact_recall'):.2f}" if e2e else pend),
        ("Answered (not refused)", "n/a",
         f"{sum(int(r['answered']) for r in e2e)}/{len(e2e)}" if e2e else pend),
        ("Relevance, LLM judge (1-5)", "n/a",
         f"{mean(e2e, 'judge_1to5'):.2f}" if e2e else pend),
        ("Mean latency", f"{mean(ret, 'latency_s'):.2f}s" if ret else pend,
         f"{mean(e2e, 'latency_s'):.1f}s" if e2e else pend),
    ]
    y = 1640000
    for i, (a, b, c) in enumerate(rows):
        if i % 2 == 0:
            box(s, 548655, y - 30000, 8024074, 330000, LIGHT)
        text(s, 699535, y + 40000, 4200000, 171450, a, 11)
        text(s, 5000000, y + 40000, 1700000, 171450, b, 11, True, MAROON)
        text(s, 6900000, y + 40000, 1500000, 171450, c, 11, True, MAROON)
        y += 330000
    text(s, 603520, 3720000, 8092656, 600000,
         "Key facts come from the course sample answers (regex match; the transcript address uses the suite shown on the "
         "current site). Relevance is graded by an LLM against the reference answer. Part B's own proxy metrics "
         "(Source Hit 83.3%) use a stricter expected-URL list, so they are not directly comparable.",
         8, False, GRAY)

    # ---- 4. challenges ----
    s = frame(prs, "Part D: Challenges & Future Improvements", first_no + 3)
    text(s, 514364, 994410, 4000000, 240030, "CHALLENGES", 14, True, TEAL)
    bullets(s, 548655, 1340000, 3900000, [
        "Strict answer review means gaps in the site\nbecome refusals, not guesses",
        "Site changes: sample answers differ from live\npages (e.g. mailing suite number)",
        "API cost and latency: two LLM calls per question",
        "Heavy dependencies (PyTorch, ChromaDB) on a\nfree host"], size=10, gap=520000)
    text(s, 4800728, 994410, 4000000, 240030, "NEXT STEPS", 14, True, TEAL)
    bullets(s, 4800728, 1340000, 3900000, [
        "Add chat history for follow-up questions",
        "Hybrid search (BM25 + embeddings) and a reranker",
        "Scheduled re-crawl so answers track the website",
        "Human-labelled test set beyond 12 questions",
        "Collect thumbs-up/down feedback in the UI"], size=10, gap=400000)
    if SHOT.is_file():
        s.shapes.add_picture(str(SHOT), Emu(5200000), Emu(3500000), height=Emu(1150000))
    out = RES / ("Midterm Project_GenAI_with_D.pptx" if merge else "PartD_slides.pptx")
    prs.save(out)
    print("saved", out)


if __name__ == "__main__":
    if "--merge" in sys.argv:
        main(10, merge=True)
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
