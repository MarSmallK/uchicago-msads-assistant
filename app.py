"""Part D: Streamlit front end for the UChicago MS-ADS RAG assistant.

Calls Part C's answer(query) (rag.py, copied verbatim from midterm.ipynb). Text input only.
"""
import base64
import html
import os
import re
import threading
import time
from pathlib import Path

import streamlit as st

import rag

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
DB_PATH = os.getenv("PART_B_DB_PATH", str(HERE / "PartB_chroma_db"))
MAX_REQUESTS_PER_SESSION = int(os.getenv("MAX_QUESTIONS_PER_SESSION", "200"))

st.set_page_config(page_title="UChicago MS in Applied Data Science", page_icon="🎓", layout="centered")

# Short label -> full question (all taken from the course test set)
CHIPS = {
    "💰  Tuition": "What is tuition cost for the program?",
    "📅  Deadlines": "What are the deadlines for the in-person program?",
    "🌐  TOEFL / IELTS": "What are the minimum scores for the TOEFL and IELTS English Language Requirement?",
    "🎓  Courses to graduate": "How many courses must you complete to earn UChicago's Master's in Applied Data Science?",
}
MORE = {
    "Scholarships": "What scholarships are available for the program?",
    "Application fee waiver": "Is there an application fee waiver?",
    "Decision timeline": "How long will it take for me to receive a decision on my application?",
    "Advising appointment": "Can I set up an advising appointment with the enrollment management team?",
    "Transcript address": "Where can I mail my official transcripts?",
    "Online program visa": "Does the Master's in Applied Data Science Online program provide visa sponsorship?",
    "MBA/MS application": "How do I apply to the MBA/MS program?",
    "STEM / OPT": "Is the MS in Applied Data Science program STEM/OPT eligible?",
}
STATUS_STYLE = {
    "answered": "ok", "clarification": "info", "insufficient_evidence": "warn",
    "out_of_scope": "info", "unsafe": "warn", "invalid_input": "warn", "error": "err",
}


# ---------- assets ----------
def b64(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


MASCOT_SVG = (ASSETS / "mascot.svg").read_text()
_crest = next((p for p in (ASSETS / "crest.svg", ASSETS / "crest.png") if p.is_file()), None)
LOGO_SRC = (
    b64(_crest, "image/svg+xml" if _crest.suffix == ".svg" else "image/png")
    if _crest else b64(ASSETS / "dsi_logo.svg", "image/svg+xml")
)

CSS = """
<style>
@property --a {syntax:'<angle>'; inherits:false; initial-value:0deg;}
@keyframes spin {to {--a:360deg;}}
@keyframes float {0%,100% {transform:translateY(0);} 50% {transform:translateY(-8px);}}
@keyframes drift {0% {transform:translate(0,0) scale(1);} 50% {transform:translate(4%,-3%) scale(1.15);} 100% {transform:translate(0,0) scale(1);}}
@keyframes pulse {0%,100% {transform:scale(1); opacity:.85;} 50% {transform:scale(1.18); opacity:1;}}
@keyframes rise {from {opacity:0; transform:translateY(10px);} to {opacity:1; transform:none;}}

html, body, [data-testid="stApp"] {background:#110a0c !important; color:#ece3e1;}
[data-testid="stApp"]::before, [data-testid="stApp"]::after {
  content:''; position:fixed; z-index:0; pointer-events:none; border-radius:50%; filter:blur(90px);
}
[data-testid="stApp"]::before {width:60vw; height:60vw; left:-15vw; top:-25vw; background:#5a1a24; opacity:.5; animation:drift 20s ease-in-out infinite;}
[data-testid="stApp"]::after {width:55vw; height:55vw; right:-18vw; bottom:-28vw; background:#7a2c38; opacity:.28; animation:drift 26s ease-in-out infinite reverse;}
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {display:none !important;}
[data-testid="stBottom"], [data-testid="stBottom"] > div {background:transparent !important;}
.block-container {max-width:720px; padding-top:1.4rem !important; position:relative; z-index:1;}

.bar {display:flex; align-items:center; justify-content:center; animation:rise .6s both;}
.bar img {height:34px; opacity:.92;}
.bar .tag {font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:#d9b5b8;}

.hero {text-align:center; padding:.6rem 0 1rem; animation:rise .8s both;}
.stage {position:relative; width:250px; height:250px; margin:0 auto;}
.stage .orb {position:absolute; inset:14px; border-radius:50%;
  background:conic-gradient(from var(--a), #b4475a, #7a1f2b, #c58b72, #8e2a3a, #b4475a);
  filter:blur(30px); opacity:.7; animation:spin 12s linear infinite, pulse 6s ease-in-out infinite;}
.stage .ring {position:absolute; inset:30px; border-radius:50%; border:1px solid rgba(255,255,255,.18);
  background:radial-gradient(circle at 35% 28%, rgba(255,255,255,.28), rgba(255,255,255,.04) 60%); backdrop-filter:blur(6px);}
.stage svg {position:absolute; left:50%; top:50%; width:160px; height:160px; margin:-84px 0 0 -80px; animation:float 5s ease-in-out infinite; filter:drop-shadow(0 10px 18px rgba(0,0,0,.45));}
.hero h1 {font-family:'Iowan Old Style','Palatino Linotype',Georgia,serif; font-weight:600; font-size:2.35rem; line-height:1.1; margin:.4rem 0 .1rem; letter-spacing:-.01em;
  background:linear-gradient(90deg,#f6eeec,#e9cfd2); -webkit-background-clip:text; background-clip:text; color:transparent;}
.hero .sub {font-size:.82rem; letter-spacing:.2em; text-transform:uppercase; color:#bda7a9;}
.hero .hi {margin-top:1rem; font-size:1rem; color:#e3d6d4;}

div[data-testid="stButton"] button {border:1px solid rgba(255,255,255,.12); border-radius:999px; background:rgba(255,255,255,.05);
  color:#ece3e1; justify-content:center; backdrop-filter:blur(10px); transition:all .2s; min-height:2.6rem; width:100%;}
div[data-testid="stButton"] button p {font-size:.92rem; white-space:normal;}
div[data-testid="stButton"] button:hover {border-color:#b4475a; background:rgba(180,71,90,.16); color:#fff; transform:translateY(-1px); box-shadow:0 6px 18px rgba(0,0,0,.3);}
[data-testid="stExpander"] {border:none !important; background:transparent !important;}
[data-testid="stExpander"] summary {color:#bda7a9; justify-content:center;}

[data-testid="stChatInput"] {background:transparent !important;}
[data-testid="stChatInput"] {max-width:720px; margin:0 auto;}
[data-testid="stChatInput"] > div {border:2px solid transparent !important; border-radius:30px !important;
  background:linear-gradient(#1c1114,#1c1114) padding-box, conic-gradient(from var(--a), #b4475a, #5a1a24, #c58b72, #7a1f2b, #b4475a) border-box !important;
  animation:spin 12s linear infinite; box-shadow:0 0 28px rgba(122,31,43,.3);}
[data-testid="stChatInput"] textarea {color:#fff !important; min-height:30px !important;}
[data-testid="stChatInput"] textarea::placeholder {color:#a8949a !important;}

[data-testid="stChatMessage"] {background:transparent !important; padding:.4rem 0; animation:rise .4s both;}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {font-size:1rem; line-height:1.6;}
[data-testid="stChatMessage"]:has(.umark) {flex-direction:row-reverse; text-align:right;}
[data-testid="stChatMessage"]:has(.umark) [data-testid="stChatMessageContent"] {flex:1; display:flex; flex-direction:column; align-items:flex-end;}
[data-testid^="stChatMessageAvatar"] {width:38px !important; height:38px !important; min-width:38px; border-radius:50% !important; background:rgba(255,255,255,.07) !important; font-size:1.25rem;}
[data-testid^="stChatMessageAvatar"] img {width:38px !important; height:38px !important; object-fit:contain; padding:3px;}
.bubble {background:linear-gradient(135deg,#7d2433,#5a1a26); padding:.7rem 1rem; border-radius:18px 18px 4px 18px; display:inline-block; text-align:left; max-width:100%;}
.glass {white-space:pre-line; overflow-wrap:anywhere; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.09); border-radius:18px 18px 18px 4px; text-align:left; padding:1rem 1.15rem; backdrop-filter:blur(14px);}
.glass.warn {border-color:rgba(214,170,120,.45);} .glass.err {border-color:rgba(190,90,100,.55);} .glass.info {border-color:rgba(255,255,255,.2);}
.src {display:inline-block; margin:.55rem .4rem 0 0; padding:.28rem .75rem; border-radius:999px; font-size:.8rem; text-decoration:none;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.14); color:#e9cfd2 !important;}
.src:hover {background:rgba(180,71,90,.2); border-color:#b4475a;}
.meta {font-size:.75rem; color:#a8949a; margin-top:.4rem;}
.thinking {display:flex; align-items:center; gap:.8rem; color:#bda7a9; font-size:.92rem;}
.thinking .dot {width:26px; height:26px; border-radius:50%; background:conic-gradient(from var(--a),#b4475a,#5a1a24,#c58b72,#b4475a);
  filter:blur(3px); animation:spin 2.4s linear infinite, pulse 1.2s ease-in-out infinite;}
.umark {display:none;}
[data-testid="stElementContainer"]:has(.umark) {display:none;}
[data-testid="stChatMessage"]:has(.umark) [data-testid="stMarkdownContainer"] {text-align:right;}
[data-testid="stChatMessage"]:has(.umark) [data-testid="stMarkdownContainer"] .meta {text-align:right;}
.note {text-align:center; color:#9a8689; font-size:.75rem; margin-top:.3rem;}
@media (prefers-reduced-motion: reduce) {* {animation:none !important;}}
</style>
"""


# ---------- backend ----------
def get_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:  # no secrets file locally
        return None


@st.cache_resource(show_spinner="Loading the knowledge base...")
def get_retriever():
    return rag.load_retriever(DB_PATH)


@st.cache_resource(show_spinner=False)
def get_answer_fn(_retrieve_context):
    key = get_api_key()
    if not key:
        return None
    os.environ["OPENAI_API_KEY"] = key
    return rag.create_answer(_retrieve_context)


@st.cache_resource(show_spinner=False)
def answer_cache():
    return {"lock": threading.Lock(), "items": {}}


def cached_answer(fn, question: str):
    """Repeat questions are served from cache (faster, no API cost). Only good results are
    cached, so a transient API error is never replayed to the next person."""
    cache, key = answer_cache(), " ".join(question.lower().split())
    hit = cache["items"].get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    out = fn(question)
    if out["status"] in ("answered", "clarification"):
        with cache["lock"]:
            if len(cache["items"]) > 500:
                cache["items"].clear()
            cache["items"][key] = (time.time(), out)
    return out


GREETING = re.compile(r"(?i)^\s*(hi|hello|hey|hiya|yo|good (morning|afternoon|evening)|thanks?( you)?|thank you|"
                      r"ok(ay)?|你好|您好|谢谢|嗨)[\s!.。！?？]*$")
GREETING_REPLY = ("Hi! I'm Phoenix, the assistant for UChicago's MS in Applied Data Science. "
                  "Ask me about admissions, deadlines, tuition, scholarships, courses or careers.")
URL = re.compile(r"https?://[^\s<>()\[\]\"']+[^\s<>()\[\]\"'.,;:!?]")


def linkify(text):
    """Escape the answer, then turn URLs (already verified against the sources) into links."""
    out, last = [], 0
    for m in URL.finditer(text):
        out.append(html.escape(text[last:m.start()]))
        u = html.escape(m.group())
        out.append(f'<a href="{u}" target="_blank">{u}</a>')
        last = m.end()
    out.append(html.escape(text[last:]))
    return "".join(out)


# ---------- rendering ----------
def esc(s):
    return html.escape(str(s))


def render_header(compact: bool):
    st.markdown(
        f'<div class="bar"><img src="{LOGO_SRC}" alt="Data Science Institute">'
        "</div>",
        unsafe_allow_html=True,
    )
    if not compact:
        st.markdown(
            f'<div class="hero"><div class="stage"><div class="orb"></div><div class="ring"></div>{MASCOT_SVG}</div>'
            "<h1>MS in Applied Data Science</h1>"
            '<div class="sub">University of Chicago</div>'
            '<div class="hi">Hi, I\'m Phoenix. What would you like to know?</div></div>',
            unsafe_allow_html=True,
        )


def render_assistant(turn):
    kind = STATUS_STYLE.get(turn["status"], "info")
    st.markdown(f'<div class="glass {kind}">{linkify(turn["response"])}</div>', unsafe_allow_html=True)
    if turn["sources"]:
        st.markdown(
            "".join(f'<a class="src" href="{esc(s["url"])}" target="_blank">↗ {esc(s["title"])}</a>'
                    for s in turn["sources"]),
            unsafe_allow_html=True,
        )
    if turn.get("passages"):
        with st.expander(f"Retrieved passages ({len(turn['passages'])})"):
            for p in turn["passages"]:
                st.markdown(f"**[{p['source_id']}] {p['title']}** · [{p['url']}]({p['url']})")
                st.text(p["passage"][:1800] + ("..." if len(p["passage"]) > 1800 else ""))
    if turn.get("latency") is not None:
        st.markdown(f'<div class="meta">{turn["latency"]:.1f}s</div>', unsafe_allow_html=True)


def render_user(turn):
    st.markdown('<span class="umark"></span>', unsafe_allow_html=True)
    st.markdown(f'<div class="bubble">{esc(turn["question"])}</div>', unsafe_allow_html=True)


def avatar():
    return str(ASSETS / "mascot.svg")


# ---------- page ----------
st.markdown(CSS, unsafe_allow_html=True)
st.session_state.setdefault("history", [])
st.session_state.setdefault("count", 0)
history = st.session_state["history"]

try:
    retrieve_context = get_retriever()
except Exception as exc:  # missing DB etc.
    st.error(f"Knowledge base could not be loaded: {exc}")
    st.stop()

render_header(compact=bool(history))

if not get_api_key():
    st.markdown('<div class="note">⚠️ Language model not configured: answers disabled.</div>', unsafe_allow_html=True)

pending = st.session_state.pop("pending", None)

if not history:
    cols = st.columns(2)
    for i, (label, q) in enumerate(CHIPS.items()):
        if cols[i % 2].button(label, key=f"chip{i}", use_container_width=True):
            pending = q
    with st.expander("More questions"):
        cols = st.columns(2)
        for i, (label, q) in enumerate(MORE.items()):
            if cols[i % 2].button(label, key=f"more{i}", use_container_width=True):
                pending = q

for turn in history:
    with st.chat_message("user", avatar="🙂"):
        render_user(turn)
    with st.chat_message("assistant", avatar=avatar()):
        render_assistant(turn)

typed = st.chat_input("Ask anything…")
if history:
    if st.button("New chat"):
        st.session_state["history"] = []
        st.rerun()
else:
    st.markdown('<div class="note">Answers come from the official program website. Please confirm deadlines and fees there.</div>',
                unsafe_allow_html=True)

question = pending or (typed or "").strip()
if question:
    turn = {"question": question}
    with st.chat_message("user", avatar="🙂"):
        render_user(turn)
    with st.chat_message("assistant", avatar=avatar()):
        slot = st.empty()
        passages, latency = [], None
        if GREETING.match(question):
            out = rag.result("answered", GREETING_REPLY)
        elif st.session_state["count"] >= MAX_REQUESTS_PER_SESSION:
            out = rag.result("error", "This session reached its question limit. Please refresh to continue.")
        else:
            st.session_state["count"] += 1
            slot.markdown('<div class="thinking"><div class="dot"></div>Searching the program website…</div>',
                          unsafe_allow_html=True)
            start = time.time()
            try:
                fn = get_answer_fn(retrieve_context)
                out = cached_answer(fn, question) if fn else rag.result("error", "The assistant isn't configured yet.")
            except Exception:
                out = rag.result("error")
            try:
                search = getattr(fn, "retrieve_context", retrieve_context) if fn else retrieve_context
                passages = list(rag.parse_context(search(rag.redact_pii(question))).values())
            except Exception:
                passages = []
            latency = time.time() - start
        slot.empty()
        turn.update(out)
        turn.update(passages=passages, latency=latency)
        render_assistant(turn)
    history.append(turn)
    if len(history) == 1:
        st.rerun()  # collapse the hero into the compact header
