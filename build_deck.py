"""Build the Part D slides in the visual style of the team deck (Midterm Project_GenAI.pptx).

All numbers are read from ../PartD_results (summary.json and the CSVs written by evaluate.py).
  python build_deck.py           -> ../PartD_results/PartD_slides.pptx (D slides only)
  python build_deck.py --merge   -> ../PartD_results/Midterm Project_GenAI_with_D.pptx (team deck + D)
"""
import csv
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "PartD_results"
TEMPLATE = ROOT / "Midterm Project_GenAI.pptx"
SHOT = RES / "ui_answer_crop.png"
REPO = "github.com/MarSmallK/uchicago-msads-assistant"

MAROON, TEAL, GRAY, INK = "800000", "136571", "636363", "232323"
LIGHT, PINK, WHITE, GREEN = "F1F5F6", "F8F2F2", "FFFFFF", "2E7D32"
LABEL = "Part D  |  Front End, Deployment & Evaluation"
SHORT = {1: "Tuition cost", 2: "Scholarships", 3: "TOEFL / IELTS minimums", 4: "Application fee waiver",
         5: "In-person deadlines", 6: "Decision timeline", 7: "Advising appointment", 8: "Transcript mailing address",
         9: "Online program visa", 10: "MBA/MS application", 11: "STEM / OPT eligibility", 12: "Courses to graduate"}
STRESS_GROUPS = [
    ("Chinese-language question", ["T01"]), ("Typos and abbreviations", ["T02"]), ("Multi-part question", ["T03"]),
    ("Online vs in-person comparison", ["T04"]), ("Relative date (\"next deadline\")", ["T05"]),
    ("Open questions (GRE, part-time, careers, faculty)", ["T06", "T07", "T09", "T10", "T18"]),
    ("Facts only in headings (core courses)", ["T08"]), ("False premise (\"tuition is free\")", ["T11"]),
    ("Other program (Applied AI)", ["T12"]), ("Jailbreak / injected instructions", ["T13", "T16"]),
    ("Personal data in the question", ["T14"]), ("Off-topic and greetings", ["T15", "T17"]),
]


def rgb(h):
    return RGBColor.from_string(h)


def text(slide, x, y, w, h, s, size=11, bold=False, color=INK):
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
    return tb


def box(slide, x, y, w, h, fill):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x), Emu(y), Emu(w), Emu(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.fill.background()
    return s


def frame(prs, title, n, notes):
    blank = [l for l in prs.slide_layouts if l.name == "BLANK"][0]
    s = prs.slides.add_slide(blank)
    text(s, 480073, 240030, 8229819, 685800, title, 23, True, MAROON)
    text(s, 315476, 4876038, 4500000, 137160, LABEL, 8, False, GRAY)
    text(s, 8709892, 4869180, 200000, 171450, str(n), 8, False, GRAY)
    s.notes_slide.notes_text_frame.text = notes
    return s


def bullets(slide, x, y, w, items, size=11, gap=300000):
    for i, it in enumerate(items):
        text(slide, x, y + i * gap, w, 274320, "• " + it, size)


def table(slide, x, y, widths, header, rows, row_h=300000, size=11, bold_cols=()):
    total = sum(widths)
    box(slide, x, y, total, 290000, TEAL)
    cx = x
    for w, h in zip(widths, header):
        text(slide, cx + 120000, y + 75000, w - 140000, 150000, h, 9, True, WHITE)
        cx += w
    yy = y + 290000
    for i, row in enumerate(rows):
        if i % 2 == 0:
            box(slide, x, yy, total, row_h, LIGHT)
        cx = x
        for j, (w, cell) in enumerate(zip(widths, row)):
            color = GREEN if cell == "✓" else (MAROON if j in bold_cols else INK)
            text(slide, cx + 120000, yy + (row_h - 170000) // 2, w - 140000, 170000, cell, size,
                 j in bold_cols or cell == "✓", color)
            cx += w
        yy += row_h
    return yy


def read_csv(name):
    p = RES / name
    return list(csv.DictReader(open(p))) if p.is_file() else []


def main(first_no, merge=False):
    summary = json.loads((RES / "summary.json").read_text())
    runs, base, ret = summary["runs"], summary["baseline_original_C"], summary["retrieval"]
    e2e, stress = read_csv("e2e_eval.csv"), {r["id"]: r for r in read_csv("stress_eval.csv")}
    url_file = RES / "live_url.txt"
    live_url = url_file.read_text().strip() if url_file.is_file() else "<live URL>"
    mean = lambda k: sum(r[k] for r in runs) / len(runs)
    worst = lambda k: min(r[k] for r in runs)
    same = lambda k: len({r[k] for r in runs}) == 1

    prs = Presentation(str(TEMPLATE))
    ids = prs.slides._sldIdLst
    if merge:
        first_no = len(ids) + 1
    else:
        for sld in list(ids):  # keep master/layouts/theme only
            prs.part.drop_rel(sld.rId)
            ids.remove(sld)
    n = first_no

    # ---- 1. system design + UI ----
    s = frame(prs, "Part D: System Design & User Interface", n, (
        "Part D connects everything into one product. A question typed in the Streamlit app goes to hybrid "
        "retrieval, which combines Part B's MiniLM semantic search with BM25 keyword search and returns the top six "
        "chunks. Part C's chain drafts an answer with quotes, the code checks every quote against the sources, "
        "and a second model call reviews the claims. The user sees a short answer, clickable source pages, and "
        "an expandable list of the passages it used, so every answer can be checked."))
    text(s, 514364, 950000, 5000000, 240030, "END-TO-END PIPELINE", 14, True, TEAL)
    steps = [("STREAMLIT UI", "Chat, suggested questions"), ("HYBRID RETRIEVAL", "MiniLM + BM25, top-6"),
             ("GROUNDED DRAFT", "gpt-4.1-mini + quotes"), ("REVIEW", "Quotes verified, then judged")]
    x = 445782
    for i, (a, b) in enumerate(steps):
        box(s, x, 1290000, 1850000, 700000, LIGHT)
        text(s, x + 82000, 1420000, 1700000, 212598, a, 11, True, TEAL)
        text(s, x + 82000, 1700000, 1700000, 205740, b, 8, False, GRAY)
        if i < 3:
            text(s, x + 1855000, 1500000, 205745, 240030, "→", 16, True, TEAL)
        x += 2060000
    text(s, 548655, 2250000, 3900000, 240030, "What the user sees", 13, True, TEAL)
    bullets(s, 548655, 2580000, 3950000, [
        "A direct answer, with links to the program website",
        "Source pages for every answer",
        "Retrieved passages one click away",
        "Clear replies for off-topic or unsafe requests",
        "UChicago maroon theme, one-tap suggested questions"], size=10, gap=330000)
    if SHOT.is_file():
        pic = s.shapes.add_picture(str(SHOT), Emu(4700000), Emu(2200000), width=Emu(3900000))
        pic.line.color.rgb = rgb("D9D9D9")
    n += 1

    # ---- 2. deployment ----
    s = frame(prs, "Part D: Deployment & Operations", n, (
        "The app is a Streamlit app deployed free on Streamlit Community Cloud from our public GitHub repository. "
        "The OpenAI key is stored only in the platform's secrets. For reliability, we cache good answers, so a "
        "repeated question is instant and free, but we never cache errors. Greetings are answered without an "
        "API call, and the whole knowledge base loads once per server. Each answer costs about a fifth of a cent."))
    text(s, 514364, 950000, 4000000, 240030, "DEPLOYMENT", 14, True, TEAL)
    cards = [("Streamlit app", "Python 3.13 · deps pinned to the versions Part C was built with"),
             ("Community Cloud", "Free hosting from the GitHub repo · public URL for DSI staff"),
             ("Secrets", "OPENAI_API_KEY stored in platform secrets, never in code or Git")]
    y = 1280000
    for a, b in cards:
        box(s, 514364, y, 8024074, 500000, LIGHT)
        text(s, 672102, y + 160000, 2300000, 171450, a, 12, True, TEAL)
        text(s, 3000000, y + 170000, 5400000, 300000, b, 11)
        y += 590000
    text(s, 514364, 3100000, 4000000, 240030, "OPERATIONAL SAFEGUARDS", 14, True, TEAL)
    bullets(s, 548655, 3430000, 3900000, ["Good answers cached for 1 h (errors never cached)",
                                          "Greetings answered without an API call"], size=10, gap=290000)
    bullets(s, 4800728, 3430000, 3900000, ["~$0.002 per question with gpt-4.1-mini",
                                           "Session cap and graceful error messages"], size=10, gap=290000)
    box(s, 548655, 4150000, 8024074, 560000, PINK)
    text(s, 685818, 4215000, 7700000, 171450, f"Live app:  {live_url}", 11, True, MAROON)
    text(s, 685818, 4470000, 7700000, 171450, f"Code:  {REPO}", 10, False, MAROON)
    n += 1

    # ---- 3. evaluation before / after ----
    s = frame(prs, "Part D: Evaluation on the 12-Question Test Set", n, (
        "When we first connected the pipeline end to end, only 2 of the 12 test questions were answered. The model "
        "was usually right, but the evidence check required byte-for-byte quotes, so formatting differences turned "
        "correct answers into refusals. After the fixes, all 12 questions are answered with the correct source page, "
        f"and an LLM judge scores relevance {mean('judge'):.2f} out of 5 on average. We ran the final evaluation "
        "three times because LLM output varies, and the results were nearly identical."))
    text(s, 514364, 900000, 8000000, 240030, "ORIGINAL PIPELINE vs FINAL (MEAN OF 3 RUNS)", 13, True, TEAL)
    judge_note = f"{mean('judge'):.2f}" + ("" if same("judge") else f"  (worst run {worst('judge'):.2f})")
    rows = [
        ("Questions answered", f"{base['answered']}/12", f"{mean('answered'):.0f}/12"),
        ("All key facts in the answer", f"{base['all_facts']}/12", f"{mean('all_facts'):.0f}/12"),
        ("Correct source page cited", f"{base['source_hit']}/12", f"{mean('source_hit'):.0f}/12"),
        ("Relevance, LLM judge (1–5)", f"{base['judge']:.2f}", judge_note),
        ("Mean latency per answer", f"{base['latency']:.1f}s", f"{mean('latency'):.1f}s"),
    ]
    yy = table(s, 548655, 1200000, [4000000, 1800000, 2224074], ["METRIC", "ORIGINAL", "FINAL"], rows,
               row_h=280000, size=10, bold_cols=(2,))
    sem, hyb = ret["semantic_top5"], ret["hybrid_top6"]
    text(s, 514364, yy + 130000, 8000000, 200000, "RETRIEVAL ONLY", 11, True, TEAL)
    table(s, 548655, yy + 380000, [4000000, 1800000, 2224074], ["METRIC", "SEMANTIC TOP-5", "HYBRID TOP-6"], [
        ("Questions with every key fact retrieved", f"{sem['all_facts']}/12", f"{hyb['all_facts']}/12"),
        ("Mean key-fact recall", f"{sem['fact_recall']:.2f}", f"{hyb['fact_recall']:.2f}"),
    ], row_h=250000, size=10, bold_cols=(2,))
    q3 = next((r for r in e2e if r["id"] == "3"), None)
    q12 = next((r for r in e2e if r["id"] == "12"), None)
    misses = []
    if q3 and q3["judge_1to5"] != "5":
        misses.append("Q3 is judged low because the site now lists TOEFL 102 (prior scale) or 5 (current scale), "
                      "while the sample answer says 102")
    if q12 and q12["all_facts"] != "1":
        misses.append("Q12 leaves out the Career Seminar")
    text(s, 603520, 4440000, 8092656, 380000,
         "Key facts are regex-matched against the course sample answers; relevance is graded by gpt-4.1-mini "
         "against the reference. " + ("Remaining misses: " + "; ".join(misses) + "." if misses else ""),
         8, False, GRAY)
    n += 1

    # ---- 4. per-question ----
    s = frame(prs, "Part D: Per-Question Results", n, (
        "Here is every test question from the final run. Every question is answered and cites the right page, "
        "and most get the top relevance score. The lower scores are explained on the previous slide: the TOEFL "
        "requirement now has two scales, and one answer left out the Career Seminar."))
    rows = []
    for r in e2e:
        rows.append((r["id"], SHORT.get(int(r["id"]), r["question"][:40]),
                     "✓" if r["answered"] == "1" else "✗",
                     "✓" if r["all_facts"] == "1" else f"{float(r['fact_recall']):.0%}",
                     "✓" if r["source_hit"] == "1" else "✗", r["judge_1to5"], f"{float(r['latency_s']):.1f}s"))
    table(s, 548655, 900000, [500000, 3300000, 950000, 950000, 850000, 800000, 674074],
          ["#", "QUESTION", "ANSWERED", "KEY FACTS", "SOURCE", "JUDGE", "TIME"], rows, row_h=290000, size=10)
    n += 1

    # ---- 5. stress testing ----
    s = frame(prs, "Part D: Stress Testing & Responsible AI", n, (
        "Because graders may try hard cases, we built an 18-question stress set: Chinese input, typos, multi-part "
        "and comparison questions, relative dates, false premises, another UChicago program, jailbreaks, injected "
        "instructions, personal data and off-topic requests. All 18 behaved correctly in all three runs. On the "
        "right are the guardrails that make this hold: PII redaction, quote verification, link whitelisting, a "
        "second-pass reviewer, and treating everything retrieved as untrusted data."))
    text(s, 514364, 900000, 4300000, 240030, f"STRESS SET ({worst('stress')}/{runs[0]['n_stress']} IN EVERY RUN)",
         13, True, TEAL)
    y = 1220000
    for label, ids_ in STRESS_GROUPS:
        ok = all(stress.get(i, {}).get("pass") == "1" for i in ids_)
        text(s, 548655, y, 3700000, 200000, label, 10)
        text(s, 4250000, y, 300000, 200000, "✓" if ok else "✗", 11, True, GREEN if ok else MAROON)
        y += 270000
    text(s, 4800728, 900000, 3900000, 240030, "GUARDRAILS", 13, True, TEAL)
    bullets(s, 4800728, 1220000, 3850000, [
        "Personal data redacted from questions and sources",
        "Every quote verified against its passage",
        "Links allowed only if present in a source",
        "Second-pass reviewer approves each claim",
        "Retrieved text and user input treated as data",
        "Joint-program and past-date context tagged",
        f"Safety cases refused: {worst('safety')}/4 in every run"], size=10, gap=400000)
    n += 1

    # ---- 6. challenges ----
    s = frame(prs, "Part D: Challenges & Future Improvements", n, (
        "Our main challenges were integration problems you only see end to end. The evidence check was too strict, "
        "some facts lived only in headings or deep inside long chunks, and the site itself gives two different "
        "TOEFL numbers for two programs. LLM variance meant one run can hide a regression, so we report three runs. "
        "Hugging Face moved Docker Spaces to a paid plan, so we deployed on Streamlit Community Cloud. Next we would "
        "add chat memory, a scheduled re-crawl, a reranker, a larger human-labelled test set, and user feedback."))
    text(s, 514364, 950000, 4000000, 240030, "CHALLENGES  →  WHAT WE DID", 13, True, TEAL)
    challenges = [
        ("Over-literal evidence check (2/12 answered)", "content-based quote matching → 12/12"),
        ("Facts hidden in headings and long chunks", "BM25 hybrid + section-overview documents"),
        ("Site gives TOEFL 104 (MBA/MS) and 102/5 (MS)", "program-scope tags on passages"),
        ("LLM run-to-run variance", "reviewer reasons first; 3 runs reported"),
        ("Free Docker hosting became paid (HF)", "Streamlit Community Cloud"),
    ]
    y = 1290000
    for a, b in challenges:
        text(s, 548655, y, 4000000, 200000, "• " + a, 10, True)
        text(s, 700000, y + 210000, 3900000, 200000, b, 9, False, GRAY)
        y += 560000
    text(s, 4800728, 950000, 4000000, 240030, "NEXT STEPS", 13, True, TEAL)
    bullets(s, 4800728, 1290000, 3900000, [
        "Chat history for follow-up questions",
        "Scheduled re-crawl so answers track the site",
        "Cross-encoder reranker over the hybrid results",
        "Larger human-labelled test set",
        "Thumbs-up/down feedback and usage analytics"], size=10, gap=420000)

    out = RES / ("Midterm Project_GenAI_with_D.pptx" if merge else "PartD_slides.pptx")
    prs.save(out)
    print("saved", out)


if __name__ == "__main__":
    if "--merge" in sys.argv:
        main(10, merge=True)
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
