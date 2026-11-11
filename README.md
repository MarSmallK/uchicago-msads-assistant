# UChicago MS in Applied Data Science — RAG Assistant (Part D)

Streamlit front end for the team's RAG chatbot. Parts A (crawl/clean/chunk) and B (MiniLM + ChromaDB)
produced `PartB_chroma_db/`; `rag.py` is Part C's grounded answer chain with Part D's fixes and hybrid
retrieval (see `CHANGES.md`). `python tests.py` runs the offline guardrail checks.

## Run locally
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # or .streamlit/secrets.toml
streamlit run app.py
```

## Evaluate
```bash
python evaluate.py retrieval   # no key needed
python evaluate.py e2e         # needs key: 12 test questions + regression/safety set
python evaluate.py stress      # needs key: adversarial questions
```

## Deploy (Streamlit Community Cloud, free)
1. Push this folder to a GitHub repo (it must include `PartB_chroma_db/`; `.streamlit/secrets.toml` is git-ignored).
2. On share.streamlit.io choose New app, pick the repo and `app.py`, and under Advanced settings set Python 3.13.
3. Paste `OPENAI_API_KEY = "sk-..."` into the app's Secrets box and deploy; the public URL appears after the build.
