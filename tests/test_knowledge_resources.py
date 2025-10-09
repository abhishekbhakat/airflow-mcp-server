"""Tests for resources directory registration helpers."""

from pathlib import Path

from airflow_mcp_server.knowledge_resources import load_knowledge_resources


def _materialize(resources):
    return {uri: reader() for uri, _title, reader, _mime in resources}


def test_registers_markdown_files(tmp_path: Path):
    """Markdown files should be discovered with stable URIs."""
    doc = tmp_path / "Guide.md"
    doc.write_text("# Title\nBody", encoding="utf-8")

    resources = load_knowledge_resources(str(tmp_path))
    contents = _materialize(resources)

    assert "file:///guide" in contents
    assert contents["file:///guide"] == "# Title\nBody"


def test_duplicate_names_get_unique_slugs(tmp_path: Path):
    """Files with matching stems should receive unique identifiers."""
    (tmp_path / "note.md").write_text("first", encoding="utf-8")
    (tmp_path / "note.markdown").write_text("second", encoding="utf-8")

    resources = load_knowledge_resources(str(tmp_path))
    contents = _materialize(resources)

    assert "file:///note" in contents
    assert "file:///note-2" in contents
    assert contents["file:///note"] == "first"
    assert contents["file:///note-2"] == "second"


def test_missing_directory_logs_warning(caplog):
    """Missing directories should be skipped gracefully."""
    with caplog.at_level("WARNING"):
        resources = load_knowledge_resources("/path/does/not/exist")

    assert resources == []
    assert caplog.records
    assert "Resources directory not found" in caplog.records[0].msg
