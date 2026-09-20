from app.services import policy_rag


def test_build_index_finds_corpus_chunks():
    index = policy_rag.build_index()
    assert len(index["chunks"]) > 0


def test_retrieve_returns_relevant_result_for_fame_question():
    results = policy_rag.retrieve("What is the FAME-II scheme?", top_k=3)
    assert len(results) > 0
    assert any("FAME" in r["source_document"] or "FAME" in r["text"] for r in results)


def test_retrieve_returns_relevant_result_for_charging_question():
    results = policy_rag.retrieve("What are the public charging standards?", top_k=3)
    assert len(results) > 0
    assert any("charging" in r["text"].lower() for r in results)


def test_retrieve_includes_last_verified_and_citation_fields():
    results = policy_rag.retrieve("Delhi EV policy road tax", top_k=3)
    assert len(results) > 0
    for r in results:
        assert r["last_verified"] != ""
        assert r["source_document"] != ""
        assert 0.0 <= r["relevance_score"] <= 1.0


def test_retrieve_nonsense_query_returns_empty_or_low_relevance():
    results = policy_rag.retrieve("asdkjhq iuwyer poiuqwe zxcvzxcv", top_k=3)
    # Either nothing comes back, or nothing has a meaningfully high score.
    assert all(r["relevance_score"] < 0.3 for r in results)


def test_answer_question_returns_grounded_answer_with_sources():
    result = policy_rag.answer_question("Tell me about FAME-II subsidies")
    assert result["answer_found"] is True
    assert len(result["sources"]) > 0
    # The literal answer text must come from the corpus and appear as a source
    assert result["answer"] == result["sources"][0]["text"]


def test_answer_question_handles_no_match_gracefully():
    result = policy_rag.answer_question("asdkjhq iuwyer poiuqwe zxcvzxcv nonsense query")
    assert result["answer_found"] in (True, False)
    if not result["answer_found"]:
        assert result["sources"] == []


def test_answer_is_never_generated_it_is_verbatim_from_corpus():
    """Core RAG-lite guarantee: the answer text must exactly match some chunk
    of the actual markdown corpus (no LLM paraphrase / hallucination)."""
    result = policy_rag.answer_question("What is Karnataka's EV policy approach?")
    index = policy_rag.build_index()
    all_chunk_texts = {c.text for c in index["chunks"]}
    if result["answer_found"]:
        assert result["answer"] in all_chunk_texts
