from __future__ import annotations

from datetime import date, datetime

from src.analyzer import build_dashboard_payload, build_summary
from src.parser import ExportMetadata, InstagramExport


def _build_export(
    export_date: date,
    followers: set[str],
    following: set[str],
    recently_unfollowed: set[str] | None = None,
) -> InstagramExport:
    metadata = ExportMetadata(
        source_name=f"instagram-sample_user-{export_date.isoformat()}-ABC.zip",
        source_label="sample_user",
        source_kind="zip",
        detected_path="connections/followers_and_following",
        account_name="sample_user",
        export_date=export_date,
        sort_timestamp=datetime.combine(export_date, datetime.min.time()),
    )
    return InstagramExport(
        metadata=metadata,
        followers=followers,
        following=following,
        recently_unfollowed=recently_unfollowed or set(),
    )


def test_build_dashboard_payload_computes_growth_metrics() -> None:
    older = _build_export(
        export_date=date(2026, 6, 1),
        followers={"alice", "bob"},
        following={"alice", "carol"},
    )
    newer = _build_export(
        export_date=date(2026, 6, 10),
        followers={"alice", "dave"},
        following={"alice", "carol", "erin"},
        recently_unfollowed={"zoe"},
    )

    payload = build_dashboard_payload([older, newer])
    summary = build_summary(payload)

    assert payload.comparison_export == older
    assert payload.current_analysis.unfollowers == {"bob"}
    assert payload.current_analysis.new_followers == {"dave"}
    assert payload.growth is not None
    assert payload.growth.net_change == 0
    assert summary["recently_unfollowed"] == 1
    assert summary["not_following_back"] == 2
