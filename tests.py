"""Offline guardrail checks (ported from midterm.ipynb cell 46, plus cases for the Part D changes).

Run: python tests.py   (no API key needed)
"""
from rag import Draft, Evidence, Review, build_answer, quote_supported, redact_pii, result

CONTEXT = (
    "[Source 1]\nTitle: Curriculum\n"
    "URL: https://datascience.uchicago.edu/curriculum/\n"
    "Content: The curriculum includes a capstone. Contact test@example.com.\n\n"
    "[Source 2]\nTitle: Curriculum\n"
    "URL: https://datascience.uchicago.edu/curriculum/\n"
    "Content: Capstone projects use real-world datasets. Apply at [the portal](https://apply-psd.uchicago.edu/portal/x).\n"
    "- November 9, 2026 - First Priority Application Deadline\n- December 7, 2026 - Second Priority Application Deadline"
)
SUPPORTED = Draft(status="answered", text="The program includes a capstone.", evidence=[
    Evidence(source_id=1, quote="The curriculum includes a capstone."),
    Evidence(source_id=2, quote="Capstone projects use real-world datasets."),
])


def approve(_):
    return Review(reason="ok", approved=True)


def run(draft, context=CONTEXT, review=approve):
    return build_answer(lambda _: context, lambda _: draft, review)("Capstone?")


def main():
    # --- original Part C contract ---
    def retrieve_for_test(question):
        assert "student@example.com" not in question
        return CONTEXT

    def generate_for_test(payload):
        assert "test@example.com" not in str(payload)          # PII in sources is redacted
        assert "[REDACTED]" in payload["question"]             # PII in the question is redacted
        return SUPPORTED

    out = build_answer(retrieve_for_test, generate_for_test, approve)("Is there a capstone? student@example.com")
    assert out["status"] == "answered"
    assert out["sources"] == [{"title": "Curriculum", "url": "https://datascience.uchicago.edu/curriculum/"}]
    assert build_answer(retrieve_for_test, generate_for_test, approve)(" ")["status"] == "invalid_input"

    for bad_evidence in (
        [],                                                              # no evidence
        [Evidence(source_id=99, quote="The curriculum includes a capstone.")],  # unknown source
        [Evidence(source_id=1, quote="Tuition is free.")],                # fabricated quote
        [Evidence(source_id=1, quote="Tuition is $1,000 per course for all students.")],
    ):
        assert run(SUPPORTED.model_copy(update={"evidence": bad_evidence}))["status"] == "insufficient_evidence"

    assert run(SUPPORTED, review=lambda _: Review(reason="no", approved=False))["sources"] == []
    assert run(SUPPORTED, context="")["status"] == "insufficient_evidence"
    for status in ("out_of_scope", "unsafe"):
        assert run(Draft(status=status, text="", evidence=[])) == result(status)

    # --- Part D changes ---
    # formatting differences no longer cause false refusals
    assert quote_supported("November 9, 2026 - First Priority Application Deadline; December 7, 2026 - Second "
                           "Priority Application Deadline", CONTEXT)
    assert quote_supported("Apply at the portal", CONTEXT)
    assert not quote_supported("Applications are free for everyone in 2026", CONTEXT)
    # links: allowed only when they appear in a source
    ok = Draft(status="answered", text="Apply here: https://apply-psd.uchicago.edu/portal/x",
               evidence=[Evidence(source_id=2, quote="Capstone projects use real-world datasets.")])
    assert run(ok)["status"] == "answered"
    invented = ok.model_copy(update={"text": "Apply here: https://evil.example.com/phish"})
    assert run(invented)["status"] == "insufficient_evidence"
    assert run(ok.model_copy(update={"text": "See [portal](https://apply-psd.uchicago.edu/portal/x)"}))["status"] \
        == "insufficient_evidence"
    assert run(ok.model_copy(update={"text": "<script>alert(1)</script>"}))["status"] == "insufficient_evidence"
    # an unverified quote is dropped, but a verified one still grounds the answer
    mixed = SUPPORTED.model_copy(update={"evidence": [
        Evidence(source_id=1, quote="The curriculum includes a capstone."), Evidence(source_id=1, quote="Made up.")]})
    assert run(mixed)["status"] == "answered"
    # official contact e-mail allowed in answers, personal e-mail still blocked
    assert redact_pii("a@uchicago.edu b@gmail.com", keep_official=True) == "a@uchicago.edu [REDACTED]"
    leak = ok.model_copy(update={"text": "Email jane.doe@gmail.com"})
    assert run(leak)["status"] == "insufficient_evidence"
    # past dates are tagged for the model; quotes that keep the tag still verify
    import datetime
    from rag import mark_past_dates
    assert mark_past_dates("November 9, 2026 and December 7, 2026", datetime.date(2026, 11, 10)) == \
        "November 9, 2026 (already passed) and December 7, 2026"
    dated = SUPPORTED.model_copy(update={"evidence": [
        Evidence(source_id=2, quote="November 9, 2026 (already passed) - First Priority Application Deadline")]})
    assert build_answer(lambda _: CONTEXT, lambda _: dated, approve, today=datetime.date(2026, 11, 10))("x")["status"] \
        == "answered"
    # a decline labelled 'answered' is not shown as an answer
    poem = SUPPORTED.model_copy(update={"text": "I cannot write a poem about pizza based on the provided sources."})
    assert run(poem)["status"] == "out_of_scope"
    lack = SUPPORTED.model_copy(update={"text": "The provided sources do not mention a fee waiver."})
    assert run(lack)["status"] == "insufficient_evidence"
    from rag import scope_note
    assert scope_note("[x] FAQs > MBA/MS > Tests\n\nTOEFL 104").startswith("(Applies only")
    print("All offline checks passed.")


if __name__ == "__main__":
    main()
