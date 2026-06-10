from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from src.analyzer import DashboardPayload, build_summary


def inject_base_styles() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 2rem;
        }
        .hero-card,
        .notice-card,
        .section-card {
            border: 1px solid rgba(49, 51, 63, 0.12);
            border-radius: 20px;
            padding: 1.5rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }
        .hero-title {
            font-size: 2.3rem;
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: 0.75rem;
            color: #0f172a;
        }
        .hero-copy {
            font-size: 1rem;
            color: #334155;
            margin-bottom: 0;
        }
        .privacy-title {
            font-size: 0.95rem;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 0.4rem;
        }
        .privacy-copy {
            font-size: 0.92rem;
            color: #475569;
            margin-bottom: 0;
        }
        .section-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def users_to_frame(usernames: set[str]) -> pd.DataFrame:
    return pd.DataFrame({"username": sorted(usernames)})


def history_to_frame(payload: DashboardPayload) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "label": point.label,
                "export_date": point.export_date,
                "followers": point.followers,
                "following": point.following,
                "net_growth": point.net_growth,
            }
            for point in payload.history
        ]
    )


def filter_user_frame(
    data_frame: pd.DataFrame,
    query: str,
    ascending: bool,
) -> pd.DataFrame:
    filtered = data_frame
    if query:
        lowered_query = query.casefold()
        filtered = filtered[
            filtered["username"].str.casefold().str.contains(lowered_query, na=False)
        ]
    return filtered.sort_values("username", ascending=ascending, ignore_index=True)


def frame_to_csv_bytes(data_frame: pd.DataFrame) -> bytes:
    return data_frame.to_csv(index=False).encode("utf-8")


def payload_to_export_frames(payload: DashboardPayload) -> dict[str, pd.DataFrame]:
    result = payload.current_analysis
    export_frames = {
        "mutuals.csv": users_to_frame(result.mutuals),
        "fans.csv": users_to_frame(result.fans),
        "not_following_back.csv": users_to_frame(result.not_following_back),
        "recently_unfollowed.csv": users_to_frame(result.recently_unfollowed),
    }
    if payload.comparison_export is not None:
        export_frames["unfollowers.csv"] = users_to_frame(result.unfollowers)
    return export_frames


def build_plain_english_summary(payload: DashboardPayload) -> str:
    summary = build_summary(payload)
    sentences = [
        (
            f"You currently have {summary['followers']} followers and follow "
            f"{summary['following']} accounts."
        ),
        (
            f"{summary['mutuals']} accounts are mutual connections, which is a "
            f"{summary['follow_back_rate']:.2f}% follow-back rate."
        ),
        (
            f"{summary['not_following_back']} of the accounts you follow do not "
            f"follow you back, representing "
            f"{summary['not_following_back_pct']:.2f}% of your following list."
        ),
        (
            f"{summary['fans']} people follow you without a return follow, or "
            f"{summary['fans_pct']:.2f}% of your follower base."
        ),
    ]
    if payload.growth is not None:
        sentences.append(
            (
                f"Compared with the previous export, you gained "
                f"{len(payload.growth.new_followers)} new followers and lost "
                f"{len(payload.growth.lost_followers)}, for a net change of "
                f"{payload.growth.net_change}."
            )
        )
    if summary["recently_unfollowed"] > 0:
        sentences.append(
            f"Instagram also reports {summary['recently_unfollowed']} recently "
            "unfollowed accounts in this export."
        )
    return " ".join(sentences)


def format_export_date(export_date: str | None) -> str:
    return export_date or "Not available"


def describe_source(payload: DashboardPayload) -> str:
    current = payload.current_export.metadata
    account = current.account_name or "Unknown"
    export_date = (
        current.export_date.isoformat()
        if current.export_date is not None
        else "Not available"
    )
    return (
        f"Source: {current.source_kind} | Account: {account} | "
        f"Export date: {export_date}"
    )


def zip_name_from_upload(filename: str) -> str:
    return Path(filename).name
