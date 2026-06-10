from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from src.parser import discover_local_exports, load_uploaded_exports


def _build_archive_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "connections/followers_and_following/followers_1.json",
            json.dumps(
                [
                    {
                        "string_list_data": [
                            {"value": "alice"},
                            {"value": "bob"},
                        ]
                    }
                ]
            ),
        )
        archive.writestr(
            "connections/followers_and_following/following.json",
            json.dumps(
                {
                    "relationships_following": [
                        {"title": "alice"},
                        {"title": "carol"},
                    ]
                }
            ),
        )
        archive.writestr(
            "connections/followers_and_following/recently_unfollowed_profiles.json",
            json.dumps(
                [
                    {
                        "label_values": [
                            {"label": "Username", "value": "dave"}
                        ]
                    }
                ]
            ),
        )
    return buffer.getvalue()


def test_load_uploaded_exports_reads_zip_contents() -> None:
    exports = load_uploaded_exports(
        [("instagram-sample_user-2026-06-10-ABC123.zip", _build_archive_bytes())]
    )

    assert len(exports) == 1
    export = exports[0]
    assert export.metadata.account_name == "sample_user"
    assert export.metadata.export_date.isoformat() == "2026-06-10"
    assert export.followers == {"alice", "bob"}
    assert export.following == {"alice", "carol"}
    assert export.recently_unfollowed == {"dave"}


def test_discover_local_exports_sorts_by_export_date(tmp_path: Path) -> None:
    older_dir = (
        tmp_path
        / "instagram-sample_user-2026-06-01-AAA"
        / "connections"
        / "followers_and_following"
    )
    newer_dir = (
        tmp_path
        / "instagram-sample_user-2026-06-05-BBB"
        / "connections"
        / "followers_and_following"
    )
    older_dir.mkdir(parents=True)
    newer_dir.mkdir(parents=True)

    (older_dir / "followers_1.json").write_text(
        json.dumps([{"string_list_data": [{"value": "alice"}]}]),
        encoding="utf-8",
    )
    (older_dir / "following.json").write_text(
        json.dumps({"relationships_following": [{"title": "alice"}]}),
        encoding="utf-8",
    )
    (newer_dir / "followers_1.json").write_text(
        json.dumps([{"string_list_data": [{"value": "alice"}, {"value": "bob"}]}]),
        encoding="utf-8",
    )
    (newer_dir / "following.json").write_text(
        json.dumps({"relationships_following": [{"title": "alice"}]}),
        encoding="utf-8",
    )

    exports = discover_local_exports(tmp_path)

    assert [export.metadata.export_date.isoformat() for export in exports] == [
        "2026-06-01",
        "2026-06-05",
    ]
