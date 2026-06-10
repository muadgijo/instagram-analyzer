from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from src.analyzer import DashboardPayload, build_dashboard_payload, build_summary
from src.dashboard import (
    create_distribution_chart,
    create_historical_trend_chart,
    create_network_overview_chart,
    create_relationship_breakdown_chart,
)
from src.parser import discover_local_exports, load_uploaded_exports
from src.utils import (
    build_plain_english_summary,
    describe_source,
    filter_user_frame,
    frame_to_csv_bytes,
    inject_base_styles,
    payload_to_export_frames,
    users_to_frame,
    zip_name_from_upload,
)


@dataclass
class AppState:
    payload: DashboardPayload
    source_description: str
    source_mode: str


def main() -> None:
    st.set_page_config(
        page_title="Instagram Analyzer",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_base_styles()
    _initialize_session_state()

    with st.sidebar:
        st.title("Instagram Analyzer")
        page = st.radio(
            "Navigation",
            [
                "Home",
                "Dashboard",
                "Analytics",
                "Explore Data",
                "Exports",
                "Advanced Insights",
            ],
        )
        st.caption("Upload one or more Instagram export ZIP files for analysis.")

    if page == "Home":
        render_home_page()
    else:
        app_state = st.session_state.get("analysis_state")
        if app_state is None:
            render_empty_state()
        elif page == "Dashboard":
            render_dashboard_page(app_state)
        elif page == "Analytics":
            render_analytics_page(app_state)
        elif page == "Explore Data":
            render_explore_page(app_state)
        elif page == "Exports":
            render_exports_page(app_state)
        elif page == "Advanced Insights":
            render_advanced_insights_page(app_state)


def render_home_page() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Instagram Analytics Dashboard</div>
            <p class="hero-copy">
                Upload your Instagram export ZIP to inspect followers,
                relationship patterns, recent unfollows, and changes across
                multiple exports in one place.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        """
        <div class="notice-card">
            <div class="privacy-title">Privacy notice</div>
            <p class="privacy-copy">
                This app never asks for Instagram credentials. Uploaded ZIP
                files are processed in memory within the current app session,
                not permanently stored, and discarded when the session ends.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    uploaded_files = st.file_uploader(
        "Upload Instagram export ZIP files",
        type=["zip"],
        accept_multiple_files=True,
        help=(
            "Upload one ZIP for a single snapshot or multiple ZIPs to enable "
            "historical comparisons."
        ),
    )

    left_column, right_column = st.columns([1.2, 0.8], gap="large")

    with left_column:
        if uploaded_files:
            with st.spinner("Analyzing uploaded Instagram exports..."):
                try:
                    payload = build_dashboard_payload(
                        load_uploaded_exports(
                            [
                                (zip_name_from_upload(file.name), file.getvalue())
                                for file in uploaded_files
                            ]
                        )
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    app_state = AppState(
                        payload=payload,
                        source_description=(
                            f"Uploaded {len(uploaded_files)} ZIP file(s)"
                        ),
                        source_mode="upload",
                    )
                    st.session_state["analysis_state"] = app_state
                    render_home_summary(app_state)
            return

        local_payload = _load_local_payload()
        if local_payload is not None:
            st.info(
                "No ZIP uploaded yet. Local exports were detected under `data/` "
                "and loaded automatically."
            )
            render_home_summary(local_payload)
        else:
            st.markdown(
                """
                <div class="section-card">
                    <div class="section-title">Get started</div>
                    <p class="hero-copy">
                        Upload an Instagram export ZIP to populate the dashboard.
                        The app validates the archive and extracts only the data
                        needed for analysis.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right_column:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Accepted archive contents</div>
                <p class="hero-copy">
                    The app looks for <code>followers_1.json</code>,
                    <code>following.json</code>, and, when available,
                    <code>recently_unfollowed_profiles.json</code> inside the
                    Instagram export ZIP.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_home_summary(app_state: AppState) -> None:
    payload = app_state.payload
    current = payload.current_export.metadata
    account_name = current.account_name or "Not available"
    export_date = (
        current.export_date.isoformat()
        if current.export_date is not None
        else "Not available"
    )

    st.success("Export detected and ready for analysis.")
    summary_columns = st.columns(3)
    summary_columns[0].metric("Account", account_name)
    summary_columns[1].metric("Export Date", export_date)
    summary_columns[2].metric("Exports Loaded", len(payload.exports))

    with st.expander("Export details", expanded=True):
        st.write(app_state.source_description)
        st.write(describe_source(payload))
        st.write(f"Detected export path: `{current.detected_path}`")


def render_dashboard_page(app_state: AppState) -> None:
    payload = app_state.payload
    summary = build_summary(payload)

    st.title("Dashboard")
    metric_columns = st.columns(6)
    metric_columns[0].metric("Followers", int(summary["followers"]))
    metric_columns[1].metric("Following", int(summary["following"]))
    metric_columns[2].metric("Mutual Followers", int(summary["mutuals"]))
    metric_columns[3].metric(
        "Not Following Back",
        int(summary["not_following_back"]),
    )
    metric_columns[4].metric("Fans", int(summary["fans"]))
    metric_columns[5].metric(
        "Recently Unfollowed",
        int(summary["recently_unfollowed"]),
    )

    st.write("")
    if payload.growth is not None:
        st.subheader("Growth")
        growth_columns = st.columns(3)
        growth_columns[0].metric(
            "New Followers",
            len(payload.growth.new_followers),
        )
        growth_columns[1].metric(
            "Lost Followers",
            len(payload.growth.lost_followers),
        )
        growth_columns[2].metric("Net Change", payload.growth.net_change)
    else:
        st.info("Upload or detect at least two exports to unlock growth metrics.")


def render_analytics_page(app_state: AppState) -> None:
    payload = app_state.payload
    st.title("Analytics")

    chart_row_one = st.columns(2, gap="large")
    chart_row_one[0].plotly_chart(
        create_relationship_breakdown_chart(payload),
        use_container_width=True,
    )
    chart_row_one[1].plotly_chart(
        create_network_overview_chart(payload),
        use_container_width=True,
    )

    chart_row_two = st.columns(2, gap="large")
    chart_row_two[0].plotly_chart(
        create_distribution_chart(payload),
        use_container_width=True,
    )
    trend_figure = create_historical_trend_chart(payload)
    if trend_figure is not None:
        chart_row_two[1].plotly_chart(trend_figure, use_container_width=True)
    else:
        chart_row_two[1].info(
            "Historical trend analysis appears when at least two exports are "
            "available for the same account."
        )


def render_explore_page(app_state: AppState) -> None:
    payload = app_state.payload
    st.title("Explore Data")

    tab_definitions = {
        "Mutual Followers": users_to_frame(payload.current_analysis.mutuals),
        "Not Following Back": users_to_frame(
            payload.current_analysis.not_following_back
        ),
        "Fans": users_to_frame(payload.current_analysis.fans),
        "Recently Unfollowed": users_to_frame(
            payload.current_analysis.recently_unfollowed
        ),
    }

    tabs = st.tabs(list(tab_definitions.keys()))
    for tab, (label, data_frame) in zip(tabs, tab_definitions.items()):
        with tab:
            controls = st.columns([2, 1])
            query = controls[0].text_input(
                f"Search {label}",
                key=f"search_{label}",
            )
            sort_label = controls[1].selectbox(
                "Sort",
                ["A to Z", "Z to A"],
                key=f"sort_{label}",
            )
            filtered = filter_user_frame(
                data_frame,
                query=query,
                ascending=sort_label == "A to Z",
            )
            st.caption(f"{len(filtered)} rows")
            st.dataframe(filtered, use_container_width=True, hide_index=True)


def render_exports_page(app_state: AppState) -> None:
    payload = app_state.payload
    st.title("Exports")
    st.write("Download the current analysis as CSV files.")

    export_frames = payload_to_export_frames(payload)
    for file_name, data_frame in export_frames.items():
        st.download_button(
            label=f"Download {file_name}",
            data=frame_to_csv_bytes(data_frame),
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
        )


def render_advanced_insights_page(app_state: AppState) -> None:
    payload = app_state.payload
    summary = build_summary(payload)

    st.title("Advanced Insights")
    insight_columns = st.columns(5)
    insight_columns[0].metric(
        "Follow-back Rate",
        f"{summary['follow_back_rate']:.2f}%",
    )
    insight_columns[1].metric(
        "Follower / Following Ratio",
        f"{summary['follower_following_ratio']:.2f}",
    )
    insight_columns[2].metric(
        "Not Following Back %",
        f"{summary['not_following_back_pct']:.2f}%",
    )
    insight_columns[3].metric("Fans %", f"{summary['fans_pct']:.2f}%")
    insight_columns[4].metric("Mutual %", f"{summary['mutual_pct']:.2f}%")

    st.subheader("Summary")
    st.write(build_plain_english_summary(payload))

    with st.expander("Advanced context"):
        st.write(describe_source(payload))
        if payload.comparison_export is None:
            st.write("Historical comparisons are currently unavailable.")
        else:
            st.write(
                "The previous export is used as the baseline for new follower, "
                "lost follower, and net growth calculations."
            )


def render_empty_state() -> None:
    st.title("Dashboard unavailable")
    st.info("Go to Home and upload an Instagram export ZIP to begin analysis.")


def _initialize_session_state() -> None:
    if "analysis_state" not in st.session_state:
        st.session_state["analysis_state"] = None


def _load_local_payload() -> AppState | None:
    app_state = st.session_state.get("analysis_state")
    if app_state is not None:
        return app_state

    try:
        exports = discover_local_exports(Path("data"))
        if not exports:
            return None
        payload = build_dashboard_payload(exports)
    except ValueError:
        return None

    app_state = AppState(
        payload=payload,
        source_description="Loaded from local data/ directory",
        source_mode="local",
    )
    st.session_state["analysis_state"] = app_state
    return app_state


if __name__ == "__main__":
    main()
