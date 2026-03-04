from __future__ import annotations

import re
from pathlib import Path

from protocol_generator_gui.persistence import DraftPersistence


def test_write_json_atomic_replaces_target(tmp_path: Path):
    target = tmp_path / "protocol.json"
    target.write_text('{"stale":true}', encoding="utf-8")

    DraftPersistence.write_json_atomic(target, {"MethodInformation": {"MethodName": "A"}})

    assert '"MethodName": "A"' in target.read_text(encoding="utf-8")


def test_temp_draft_save_and_recover(tmp_path: Path):
    temp_path = tmp_path / "draft.json"
    persistence = DraftPersistence(temp_path)

    persistence.save_temp_draft({"AssayInformation": [{"AssayName": "Assay-1"}]})

    assert persistence.load_temp_draft() == {"AssayInformation": [{"AssayName": "Assay-1"}]}


def test_now_stamp_uses_hh_mm_format():
    stamp = DraftPersistence.now_stamp()
    assert re.fullmatch(r"\d{2}:\d{2}", stamp)
