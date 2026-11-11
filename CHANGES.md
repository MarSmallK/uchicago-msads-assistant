# Changes made in Part D (deployed `rag.py` vs. `midterm.ipynb`)

End-to-end testing of the notebook's Part B + C chain on the 12 course test questions found
that **only 2 of 12 were answered**. In almost every case the model's answer was correct and the
reviewer approved it, but the answer was then thrown away by a check that was too literal. All
guardrails are kept. `python tests.py` runs the original offline checks plus new ones.

| # | Problem found | Change |
|---|---------------|--------|
| 1 | Evidence quotes had to be byte-for-byte substrings, but the model drops Markdown (`**`, `[text](url)`), list bullets and line breaks, so correct quotes failed. | Both sides are normalized (Markdown links → text, URLs, bullets and formatting stripped, whitespace collapsed). Each piece of a quote must appear in its passage, with a strict 92% fuzzy fallback. Unverifiable quotes are dropped; at least one verified quote is still required, and only verified quotes go to the reviewer. A fabricated quote ("Tuition is free.") is still rejected. |
| 2 | Any URL in an answer caused a refusal, but several test answers *are* links (advising portal, PSD fee-waiver policy, Booth application). | URLs are allowed only if they appear in a retrieved passage, so invented links are still blocked. HTML and Markdown links are still rejected. The app turns the URLs into clickable links. |
| 3 | The fee-waiver sentence is buried in a long "transcripts" chunk, so semantic search never retrieved it. | Hybrid retrieval: Part B's MiniLM semantic search fused with BM25 keyword search (reciprocal rank fusion), top 6. Retrieval fact recall went from 11/12 to 12/12 questions. |
| 4 | Some facts exist only as section headings (each core course and scholarship is its own sub-section), so "What are the core courses?" matched no chunk. | "Section overview" documents, built only from Part A's section paths, list the sub-section titles under each parent. They are kept in memory next to the Chroma index. |
| 5 | The reviewer's bare yes/no verdict was unstable and rejected correct answers (TOEFL). | The reviewer writes a one-sentence reason before deciding (`Review.reason`). |
| 6 | Conflicting numbers: the joint MBA/MS FAQ says TOEFL 104, while the MS page says 102 (prior scale) or 5 (current scale). | The prompt asks for the standalone-MS value with its qualifiers. Passages whose section path is MBA/MS are tagged "applies only to the joint MBA/MS degree". |
| 7 | "When is the next deadline?" needs today's date, and the model compares dates poorly. | Today's date is sent with each request, and past dates in passages are tagged "(already passed)". |
| 8 | Non-English questions (e.g. Chinese) don't match the English embedding model. | Non-ASCII questions are translated into an English search query for retrieval only. The answer stays in the user's language. |
| 9 | Refusals mislabelled as `answered`. | A deterministic guard maps them to `out_of_scope` / `insufficient_evidence`. |
| 10 | Prompt wording | Answer first, include every requested item, answer every part of multi-part questions, use lists for 3+ items, stay under about 120 words. The "insufficient evidence" message now points to the admissions portal. Official `@uchicago.edu` contact addresses are no longer redacted. |

Model: `gpt-4.1-mini` (overridable via `PART_C_MODEL`). `gpt-4.1` scored the same on our sets at 5× the cost.
