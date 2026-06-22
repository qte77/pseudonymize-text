"""`.eml` detection + header-rewrite regression tests.

Covers two defects found by an end-to-end run:
1. `detect` skipped `.eml`/`.mbox` entirely, so `apply --plan` shipped
   unredacted mail (the documented audit-first workflow leaked PII).
2. Address-header display-name tokens were mangled to ``<NAME>:hex>`` when the
   ``email`` library re-serialized the header under ``policy.default``.
"""

import json
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

import pytest

from pseudonymize_text.cli import main
from pseudonymize_text.formats.eml import transform_message

_KEY = "ab" * 32


def _stub_transform(text: str, _rel: Path) -> str:
    return text.replace("John Doe", "<NAME:abc123>").replace(
        "john.doe@acme.com", "<EMAIL:def456>"
    )


def test_address_header_token_is_wellformed_and_reparses() -> None:
    """BUG 2: From/To display-name tokens must survive re-serialization intact."""
    msg = EmailMessage()
    msg["From"] = "John Doe <john.doe@acme.com>"
    msg["Subject"] = "Note from John Doe"
    msg.set_content("hi")

    transform_message(msg, _stub_transform, Path("m.eml"))
    raw = bytes(msg)

    reparsed = BytesParser(policy=policy.default).parsebytes(raw)
    from_hdr = str(reparsed["From"])
    assert "<NAME>:" not in from_hdr, f"mangled token in From: {from_hdr!r}"
    assert "<NAME:abc123>" in from_hdr, f"NAME token lost in From: {from_hdr!r}"
    assert "<EMAIL:def456>" in from_hdr
    # Subject is not an address header — whole-value substitution still applies.
    assert "<NAME:abc123>" in str(reparsed["Subject"])


def _write_eml(in_dir: Path) -> None:
    in_dir.mkdir(parents=True, exist_ok=True)
    (in_dir / "m.eml").write_text(
        "From: John Doe <john.doe@acme.com>\n"
        "To: Jane Roe <jane.roe@acme.com>\n"
        "Subject: Invoice\n"
        'Content-Type: text/plain; charset="utf-8"\n'
        "\n"
        "Pay IBAN DE89370400440532013000 please.\n",
        encoding="utf-8",
    )


def _terms(tmp_path: Path) -> Path:
    p = tmp_path / "terms.csv"
    p.write_text("value,type,id\nJohn Doe,name,p1\nJane Roe,name,p2\n", encoding="utf-8")
    return p


def test_detect_records_eml_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BUG 1: detect must surface mail spans in the audit plan."""
    in_dir = tmp_path / "in"
    _write_eml(in_dir)
    report = tmp_path / "plan.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", _KEY)

    rc = main(["detect", str(in_dir), "--terms", str(_terms(tmp_path)), "--report", str(report)])

    assert rc == 0
    records = [json.loads(line) for line in report.read_text().splitlines()[1:]]
    files = {r["file"] for r in records}
    assert "m.eml" in files, "detect produced no spans for the .eml file"
    types = {r["type"] for r in records if r["file"] == "m.eml"}
    assert {"name", "email", "iban"} <= types


def test_apply_plan_redacts_mail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BUG 1: apply --plan must redact mail, not ship it in plaintext."""
    in_dir = tmp_path / "in"
    _write_eml(in_dir)
    plan = tmp_path / "plan.jsonl"
    out_dir = tmp_path / "out"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", _KEY)
    terms = _terms(tmp_path)

    assert main(["detect", str(in_dir), "--terms", str(terms), "--report", str(plan)]) == 0
    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--terms", str(terms), "--plan", str(plan),
            "--mapping", str(tmp_path / "map.json"),
            "--report", str(tmp_path / "rep.jsonl"),
        ]
    )

    assert rc == 0
    out = (out_dir / "m.eml").read_text(encoding="utf-8")
    for plaintext in ("john.doe@acme.com", "jane.roe@acme.com", "DE89370400440532013000"):
        assert plaintext not in out, f"{plaintext!r} leaked through apply --plan"
    # Output stays valid RFC 5322; address-header tokens are recoverable after
    # the standard RFC 2047 header decode (body-part tokens are literal).
    reparsed = BytesParser(policy=policy.default).parsebytes(out.encode("utf-8"))
    header_text = str(reparsed["From"]) + str(reparsed["To"])
    assert "<NAME:" in header_text
    assert "<EMAIL:" in header_text
    assert "<IBAN:" in out
