"""Publication hygiene regressions, not proof of security or compatibility."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

from defusedxml import ElementTree
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_content", ROOT / "scripts/check_public_content.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def test_known_token_is_reported_without_disclosing_value():
    value = "ghp_" + "a" * 36
    findings = checker.inspect_text("sample.md", value)
    assert findings and findings[0]["rule"] == "github-token"
    assert value not in json.dumps(findings)


def test_private_key_is_flagged():
    value = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    assert checker.inspect_text("sample.txt", value)[0]["rule"] == "private-key"


@pytest.mark.parametrize("path", [".env", ".env.local", "data/state.db", "id_ed25519"])
def test_secret_filenames_are_flagged(path):
    assert checker.secret_filename(path)


def test_example_environment_file_is_allowed():
    assert not checker.secret_filename(".env.example")


def test_embedded_wheel_text_is_scanned():
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("pkg/config.txt", "sk-" + "Z" * 40)
    findings, count = checker.inspect_payload("runtime.whl", stream.getvalue())
    assert count == 1
    assert any(f["rule"] == "provider-token" for f in findings)


def test_archive_path_traversal_is_reported_without_extraction():
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("../escape", "text")
    findings, _ = checker.inspect_payload("runtime.whl", stream.getvalue())
    assert findings[0]["rule"] == "unsafe-archive-path"


def test_historical_record_redaction():
    findings = checker.inspect_text("docs/validation/result.txt", "/Users/" + "someone/work\n" + 'hostname="machine-id"')
    assert {f["rule"] for f in findings} == {"local-machine-path", "local-hostname"}
    assert not checker.inspect_text("docs/validation/result.txt", '[LOCAL_WORKDIR]/work hostname="redacted-host"')


def test_checked_in_content_hygiene():
    assert checker.scan()["findings"] == []


def test_current_install_docs_have_no_publication_placeholders():
    for name in ["README.md", "docs/QUICKSTART.ja.md", "docs/DISTRIBUTION.ja.md"]:
        text = (ROOT / name).read_text()
        assert "OWNER/jev-ai-scrum-master" not in text
        assert "Publish this alpha snapshot to GitHub" not in text
        assert "Deeper Jev paths without MCP" not in text
        assert "AFTER publication" not in text
        assert "ryoheimatsumo/jev-ai-scrum-master" in text


def test_current_docs_link_to_existing_local_files():
    for name in ["README.md", "SECURITY.md", "CONTRIBUTING.md", "docs/QUICKSTART.ja.md", "docs/DISTRIBUTION.ja.md", "docs/IMPLEMENTATION_STATUS.ja.md", "docs/PUBLISHING.ja.md"]:
        path = ROOT / name
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            assert (path.parent / link.split("#", 1)[0]).exists(), (name, link)


def test_public_log_sanitization_preserves_report_outcomes():
    expected = {
        "core-tests.xml": (50, 0, 0),
        "adapter-tests.xml": (57, 0, 3),
        "skill-first/tests.xml": (170, 0, 3),
        "marketplace/tests.xml": (236, 0, 3),
    }
    for name, (tests, failures, skipped) in expected.items():
        suite = ElementTree.parse(ROOT / "docs/validation" / name).getroot().find("testsuite")
        assert int(suite.get("tests")) == tests
        assert int(suite.get("failures")) == failures
        assert int(suite.get("skipped")) == skipped


def test_public_safety_statements_remain_explicit():
    readme = (ROOT / "README.md").read_text()
    security = (ROOT / "SECURITY.md").read_text()
    assert "independent community" in readme
    assert "not an OS/network sandbox" in readme
    assert "independent AI reviewer is not implemented" in readme
    assert "not measured results" in readme
    assert "not a promise of offline inference" in security
