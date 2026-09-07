from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.produce_graphify import concept_id, extract_document


def test_producer_extracts_only_bounded_source_sections(tmp_path):
    document = tmp_path / "README.md"
    document.write_text("# Product\ntext\n## Safety\nmore\n")
    result = extract_document(tmp_path, "README.md")
    assert result["source"] == "README.md"
    assert [item["label"] for item in result["concepts"]] == ["Product", "Safety"]
    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["relation"] == "FOLLOWS"
    assert result["concepts"][0]["id"] == concept_id("Product", "README.md", 0)
