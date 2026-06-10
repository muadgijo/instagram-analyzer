from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.analyzer import DashboardPayload, build_summary
from src.utils import history_to_frame

PLOT_TEMPLATE = "plotly_white"


def create_relationship_breakdown_chart(payload: DashboardPayload) -> go.Figure:
    result = payload.current_analysis
    frame = pd.DataFrame(
        {
            "relationship": ["Mutuals", "Fans", "Not Following Back"],
            "count": [
                len(result.mutuals),
                len(result.fans),
                len(result.not_following_back),
            ],
        }
    )
    figure = px.pie(
        frame,
        names="relationship",
        values="count",
        hole=0.58,
        color="relationship",
        color_discrete_sequence=["#0f172a", "#2563eb", "#f59e0b"],
        template=PLOT_TEMPLATE,
    )
    figure.update_traces(textposition="inside", textinfo="percent+label")
    figure.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    return figure


def create_network_overview_chart(payload: DashboardPayload) -> go.Figure:
    summary = build_summary(payload)
    frame = pd.DataFrame(
        {
            "metric": ["Followers", "Following"],
            "count": [summary["followers"], summary["following"]],
        }
    )
    figure = px.bar(
        frame,
        x="count",
        y="metric",
        orientation="h",
        color="metric",
        color_discrete_sequence=["#2563eb", "#0f172a"],
        template=PLOT_TEMPLATE,
    )
    figure.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
    return figure


def create_distribution_chart(payload: DashboardPayload) -> go.Figure:
    summary = build_summary(payload)
    frame = pd.DataFrame(
        {
            "segment": ["Mutuals", "Fans", "Not Following Back"],
            "percentage": [
                summary["mutual_pct"],
                summary["fans_pct"],
                summary["not_following_back_pct"],
            ],
        }
    )
    figure = px.bar(
        frame,
        x="segment",
        y="percentage",
        color="segment",
        text="percentage",
        color_discrete_sequence=["#0f172a", "#2563eb", "#f59e0b"],
        template=PLOT_TEMPLATE,
    )
    figure.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    figure.update_layout(
        yaxis_title="Percentage",
        showlegend=False,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    return figure


def create_historical_trend_chart(payload: DashboardPayload) -> go.Figure | None:
    if len(payload.history) < 2:
        return None

    history_frame = history_to_frame(payload)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history_frame["export_date"],
            y=history_frame["followers"],
            mode="lines+markers",
            name="Followers",
            line=dict(color="#2563eb", width=3),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=history_frame["export_date"],
            y=history_frame["following"],
            mode="lines+markers",
            name="Following",
            line=dict(color="#0f172a", width=3),
        )
    )
    figure.add_trace(
        go.Bar(
            x=history_frame["export_date"],
            y=history_frame["net_growth"],
            name="Net Growth",
            marker_color="#16a34a",
            opacity=0.45,
        )
    )
    figure.update_layout(
        template=PLOT_TEMPLATE,
        margin=dict(t=20, b=20, l=20, r=20),
        yaxis_title="Accounts",
    )
    return figure
