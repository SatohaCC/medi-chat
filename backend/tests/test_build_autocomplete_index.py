import tempfile
from pathlib import Path

from backend.application.medicine.autocomplete import katakana_to_hiragana
from backend.infrastructure.sources.yj_csv import parse_yj_csv


def test_katakana_to_hiragana() -> None:
    assert katakana_to_hiragana("ガスターサン") == "がすたーさん"
    assert katakana_to_hiragana("カッコントウ") == "かっこんとう"
    assert katakana_to_hiragana("アマリール100mg") == "あまりーる100mg"


def test_parse_yj_csv_handles_sample_rows() -> None:
    # Build minimal mock CSV in Shift-JIS / CP932
    csv_content = (
        '"0","Y","610406079","7","ガスター散２％","09","ｶﾞｽﾀｰｻﾝ2%","33","1","ｇ","1","9.50","0","0","0","0","0","0","0","0","0","1","0","0","0","0","0","1","","20260401","99999999","2325003B2029","001413000","0","ガスター散２％","0","2325003B2ZZZ","【般】ファモチジン散２％","2","0","0","1"\n'
        '"0","Y","610406193","4","期限切薬品","05","ｷｹﾞﾝｷﾞﾚ","33","1","ｇ","1","22.30","0","0","0","0","0","0","0","0","0","7","0","0","0","0","0","1","","20200401","20220331","1111111A1000","000000000","0","期限切薬品","0","1111111A1ZZZ","","2","0","0","1"\n'
    )
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(csv_content.encode("cp932"))
        temp_path = Path(f.name)

    try:
        items = parse_yj_csv(temp_path)
        # Expired item should be excluded
        assert len(items) == 1
        item = items[0]
        assert item["n"] == "ガスター散２％"
        assert item["k"] == "ガスターサン2%"
        assert item["h"] == "がすたーさん2%"
        assert item["y"] == "2325003B2029"
        assert item["g"] == "ファモチジン散２％"
        assert item["c"] == "内用"
    finally:
        temp_path.unlink(missing_ok=True)
