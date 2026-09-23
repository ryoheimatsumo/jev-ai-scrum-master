"""Regression checks for documentation; not a security or translation certification."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_docs", ROOT / "scripts/check_public_docs.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def fixture_docs(root):
    (root / "docs").mkdir()
    (root / "docs/languages.json").write_text(json.dumps({
        "schema_version": 1,
        "pairs": [{"en": "README.md", "ja": "README.ja.md"}],
        "single_source": [],
    }))
    (root / "README.md").write_text("# Guide\n\n[日本語](README.ja.md)\n\nSetup.\n")
    (root / "README.ja.md").write_text("# 案内\n\n[English](README.md)\n\n設定。\n")
    return root


def test_current_public_docs():
    assert checker.check(ROOT) == []


def test_valid_fixture(tmp_path):
    assert checker.check(fixture_docs(tmp_path)) == []


@pytest.mark.parametrize("change", ["missing_pair", "broken_link", "mixed_language", "missing_switch", "obsolete", "unclosed_fence", "duplicate"])
def test_rejects_doc_regressions(tmp_path, change):
    root = fixture_docs(tmp_path)
    en = root / "README.md"
    if change == "missing_pair":
        (root / "README.ja.md").unlink()
    elif change == "broken_link":
        en.write_text(en.read_text() + "[missing](missing.md)\n")
    elif change == "mixed_language":
        en.write_text(en.read_text() + "設定は日本語だけです。\n")
    elif change == "missing_switch":
        en.write_text("# Guide\n\nSetup.\n")
    elif change == "obsolete":
        en.write_text(en.read_text() + "OWNER/jev-ai-scrum-master\n")
    elif change == "unclosed_fence":
        en.write_text(en.read_text() + "```sh\necho test\n")
    else:
        p = root / "docs/languages.json"
        data = json.loads(p.read_text()); data["pairs"] *= 2
        p.write_text(json.dumps(data))
    assert checker.check(root)


def test_external_urls_do_not_trigger_network_checks(tmp_path):
    root = fixture_docs(tmp_path)
    p = root / "README.md"
    p.write_text(p.read_text() + "[upstream](https://example.invalid/docs)\n")
    assert checker.check(root) == []


def test_examples_in_code_are_not_links(tmp_path):
    root = fixture_docs(tmp_path)
    p = root / "README.md"
    p.write_text(p.read_text() + "```text\n[fake](absent.md)\n日本語の例\n```\n")
    assert checker.check(root) == []


def test_path_escape_is_rejected(tmp_path):
    root = fixture_docs(tmp_path)
    p = root / "README.md"
    p.write_text(p.read_text() + "[outside](../outside.md)\n")
    assert checker.check(root)


def test_invalid_catalog(tmp_path):
    root = fixture_docs(tmp_path)
    (root / "docs/languages.json").write_text('{"schema_version":99,"pairs":[]}')
    assert checker.check(root)
