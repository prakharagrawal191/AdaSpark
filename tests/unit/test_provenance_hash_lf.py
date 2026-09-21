"""DEC-037 s4: the LF-normalised provenance digest, added additively.

The property under test is the one that FAILED on Day 29: a file governed by
``* text=auto`` under ``core.autocrlf=true`` produces a different raw-byte
digest in each checkout representation, so ``rl_yaml_sha256`` can never be
stable across clones. The LF sibling must be invariant across all three
representations while the raw field keeps its exact original meaning.
"""
from __future__ import annotations

import hashlib

import pytest

from sparkrl.training.loop import _sha256_file, _sha256_file_lf

pytestmark = pytest.mark.unit

CONTENT_LINES = ("alpha: 0.2", "gamma: 0.0", "epsilon_start: 1.0", "")
LF = "\n".join(CONTENT_LINES).encode("utf-8")
CRLF = "\r\n".join(CONTENT_LINES).encode("utf-8")
CR = "\r".join(CONTENT_LINES).encode("utf-8")
# The real Day-29 divergence: 19 lines CRLF then the rest LF, which is what
# an editor appending LF lines to a CRLF checkout actually leaves behind.
MIXED = b"alpha: 0.2\r\ngamma: 0.0\r\nepsilon_start: 1.0\n"


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_lf_digest_is_invariant_across_checkout_representations(tmp_path):
    """The whole point: one content, one LF digest, whatever the endings."""
    digests = {
        name: _sha256_file_lf(_write(tmp_path, name, data))
        for name, data in (("lf.yaml", LF), ("crlf.yaml", CRLF),
                           ("cr.yaml", CR), ("mixed.yaml", MIXED))
    }
    assert len(set(digests.values())) == 1, digests
    # and it equals the digest of the canonical LF bytes
    assert set(digests.values()) == {hashlib.sha256(LF).hexdigest()}


def test_raw_digest_still_diverges_and_is_unchanged(tmp_path):
    """The raw field keeps its exact meaning - this is NOT a bug fix to it.

    If this ever starts passing as a single value, _sha256_file has been
    silently redefined and every recorded manifest hash has become
    incomparable, which DEC-037 s4 forbids.
    """
    raw = {name: _sha256_file(_write(tmp_path, name, data))
           for name, data in (("lf.yaml", LF), ("crlf.yaml", CRLF),
                              ("mixed.yaml", MIXED))}
    assert len(set(raw.values())) == 3, raw
    assert raw["lf.yaml"] == hashlib.sha256(LF).hexdigest()
    assert raw["crlf.yaml"] == hashlib.sha256(CRLF).hexdigest()


def test_both_helpers_return_none_on_unreadable_path(tmp_path):
    """A missing file is never a crash, for either helper."""
    missing = tmp_path / "does-not-exist.yaml"
    assert _sha256_file(missing) is None
    assert _sha256_file_lf(missing) is None


def test_manifest_records_both_fields_and_keeps_schema_v1():
    """Additive only: the sibling is emitted and the pinned schema is intact.

    ``scripts/validate_day29.py`` asserts record_schema_version equals
    "rl-training-run/v1" exactly, so the sibling field must NOT bump it.
    """
    import inspect

    from sparkrl.training import loop

    src = inspect.getsource(loop)
    assert '"rl_yaml_sha256": _sha256_file(' in src
    assert '"rl_yaml_sha256_lf": _sha256_file_lf(' in src
    assert '"t_ref_gate_sha256": _sha256_file(' in src
    assert '"t_ref_gate_sha256_lf": _sha256_file_lf(' in src
    assert loop.MANIFEST_SCHEMA == "rl-training-run/v1"
