from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from src.parser import InstagramExport, sort_exports


@dataclass(frozen=True)
class AnalysisResult:
    followers: set[str]
    following: set[str]
    recently_unfollowed: set[str]
    mutuals: set[str]
    not_following_back: set[str]
    fans: set[str]
    unfollowers: set[str]
    new_followers: set[str]


@dataclass(frozen=True)
class GrowthMetrics:
    new_followers: set[str]
    lost_followers: set[str]

    @property
    def net_change(self) -> int:
        return len(self.new_followers) - len(self.lost_followers)


@dataclass(frozen=True)
class HistoricalPoint:
    label: str
    export_date: str
    followers: int
    following: int
    net_growth: int


@dataclass(frozen=True)
class DashboardPayload:
    exports: list[InstagramExport]
    current_export: InstagramExport
    comparison_export: InstagramExport | None
    current_analysis: AnalysisResult
    growth: GrowthMetrics | None
    history: list[HistoricalPoint]


def analyze(
    followers: set[str],
    following: set[str],
    recently_unfollowed: set[str] | None = None,
    previous_followers: set[str] | None = None,
) -> AnalysisResult:
    previous = previous_followers or set()
    recent = recently_unfollowed or set()
    mutuals = followers & following
    not_following_back = following - followers
    fans = followers - following
    unfollowers = previous - followers if previous_followers is not None else set()
    new_followers = followers - previous if previous_followers is not None else set()

    return AnalysisResult(
        followers=followers,
        following=following,
        recently_unfollowed=recent,
        mutuals=mutuals,
        not_following_back=not_following_back,
        fans=fans,
        unfollowers=unfollowers,
        new_followers=new_followers,
    )


def build_dashboard_payload(exports: Sequence[InstagramExport]) -> DashboardPayload:
    if not exports:
        raise ValueError("At least one export is required.")

    ordered_exports = sort_exports(exports)
    current_export = ordered_exports[-1]
    timeline_exports = _timeline_for_current_account(ordered_exports, current_export)
    comparison_export = timeline_exports[-2] if len(timeline_exports) > 1 else None

    current_analysis = analyze(
        followers=current_export.followers,
        following=current_export.following,
        recently_unfollowed=current_export.recently_unfollowed,
        previous_followers=(
            comparison_export.followers if comparison_export is not None else None
        ),
    )
    growth = (
        GrowthMetrics(
            new_followers=current_analysis.new_followers,
            lost_followers=current_analysis.unfollowers,
        )
        if comparison_export is not None
        else None
    )

    return DashboardPayload(
        exports=timeline_exports,
        current_export=current_export,
        comparison_export=comparison_export,
        current_analysis=current_analysis,
        growth=growth,
        history=_build_history(timeline_exports),
    )


def build_summary(payload: DashboardPayload) -> dict[str, float | int]:
    result = payload.current_analysis
    followers_count = len(result.followers)
    following_count = len(result.following)

    return {
        "followers": followers_count,
        "following": following_count,
        "mutuals": len(result.mutuals),
        "not_following_back": len(result.not_following_back),
        "fans": len(result.fans),
        "recently_unfollowed": len(result.recently_unfollowed),
        "unfollowers": len(result.unfollowers),
        "new_followers": len(result.new_followers),
        "follow_back_rate": _safe_percentage(len(result.mutuals), following_count),
        "follower_following_ratio": _safe_ratio(followers_count, following_count),
        "not_following_back_pct": _safe_percentage(
            len(result.not_following_back),
            following_count,
        ),
        "fans_pct": _safe_percentage(len(result.fans), followers_count),
        "mutual_pct": _safe_percentage(len(result.mutuals), following_count),
    }


def export_csv(path: Path, usernames: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["username"])
        for username in sorted(usernames):
            writer.writerow([username])


def _timeline_for_current_account(
    ordered_exports: Sequence[InstagramExport],
    current_export: InstagramExport,
) -> list[InstagramExport]:
    current_account = current_export.metadata.account_name
    if current_account is None:
        return list(ordered_exports)

    account_exports = [
        export
        for export in ordered_exports
        if export.metadata.account_name == current_account
    ]
    return account_exports or list(ordered_exports)


def _build_history(exports: Sequence[InstagramExport]) -> list[HistoricalPoint]:
    history: list[HistoricalPoint] = []
    previous_followers: set[str] | None = None

    for index, export in enumerate(exports, start=1):
        followers_count = len(export.followers)
        following_count = len(export.following)
        net_growth = (
            followers_count - len(previous_followers)
            if previous_followers is not None
            else 0
        )
        history.append(
            HistoricalPoint(
                label=f"Export {index}",
                export_date=(
                    export.metadata.export_date.isoformat()
                    if export.metadata.export_date is not None
                    else export.metadata.source_name
                ),
                followers=followers_count,
                following=following_count,
                net_growth=net_growth,
            )
        )
        previous_followers = export.followers

    return history


def _safe_percentage(value: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 2)
