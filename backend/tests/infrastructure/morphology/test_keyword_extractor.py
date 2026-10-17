from backend.infrastructure.morphology.keyword_extraction import extract_search_keywords


def test_extract_adverse_events():
    assert "下痢" in extract_search_keywords("下痢する？")
    assert "頭痛" in extract_search_keywords("頭痛は出る？")
    assert "発熱" in extract_search_keywords("発熱したときは？")
    assert "吐き気" in extract_search_keywords("吐き気はある？")


def test_extract_adjective_symptoms():
    kw = extract_search_keywords("眠くなる？")
    assert "眠気" in kw or "傾眠" in kw


def test_extract_conditions():
    assert "空腹時" in extract_search_keywords("空腹時に飲める？")
    assert "アルコール" in extract_search_keywords("アルコールと一緒に飲んで平気？")
    assert "グレープフルーツ" in extract_search_keywords(
        "グレープフルーツと一緒に飲んで平気？"
    )


def test_extract_empty_or_stop_words():
    assert extract_search_keywords("") == []
    # General inquiry about adverse events should not extract noise
    assert "副作用" not in extract_search_keywords("副作用は何がある？")
