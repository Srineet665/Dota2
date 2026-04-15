import os

import altair as alt
import pandas as pd
import streamlit as st

from dota_service import (
    add_loss_rate,
    collect_period_summaries,
    highlight_top_players,
    normalize_ids,
)

DEFAULT_STEAM_IDS = [
    "76561198355928347",  # You
    "76561198220727716",  # Friend
]


@st.cache_data(ttl=300)
def cached_collect_period_summaries(steam_ids: list[str], days: int, api_key: str):
    return collect_period_summaries(steam_ids, days, api_key)


def render_chart(df: pd.DataFrame, title: str, metric: str) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("steam_id:N", title="Steam64 ID"),
            y=alt.Y(f"{metric}:Q", title=metric.replace("_", " ").title()),
            tooltip=["steam_id", metric, "games", "win_rate"],
        )
        .properties(title=title)
    )


def main() -> None:
    st.set_page_config(page_title="Dota 2 Friends Dashboard", layout="wide")
    st.title("Dota 2 Friends Dashboard")
    st.caption(
        "Paste your Steam64 profile IDs (from the URL) to see who has been winning lately."
    )

    default_ids = "\n".join(DEFAULT_STEAM_IDS)
    steam_input = st.text_area(
        "Steam64 IDs",
        value=default_ids,
        help="Paste one per line or comma-separated.",
    )

    api_key = st.text_input(
        "OpenDota or Steam API key (optional)",
        value=os.getenv("DOTA_API_KEY", ""),
        help="Improves rate limits. Either OpenDota or Steam Web API keys work with this endpoint.",
    )

    steam_ids = normalize_ids(steam_input)
    if not steam_ids:
        st.warning("Please enter at least one valid Steam64 ID.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Last 7 days")
        weekly_df, weekly_errors = cached_collect_period_summaries(steam_ids, 7, api_key)
        if weekly_errors:
            st.error("\n".join(weekly_errors))
        if weekly_df.empty:
            st.info("No matches found for the last 7 days.")
        else:
            st.dataframe(weekly_df)
            st.altair_chart(
                render_chart(weekly_df, "Win rate (7 days)", "win_rate"),
                use_container_width=True,
            )
            st.altair_chart(
                render_chart(weekly_df, "Games played (7 days)", "games"),
                use_container_width=True,
            )

    with col2:
        st.subheader("Last 30 days")
        monthly_df, monthly_errors = cached_collect_period_summaries(steam_ids, 30, api_key)
        if monthly_errors:
            st.error("\n".join(monthly_errors))
        if monthly_df.empty:
            st.info("No matches found for the last 30 days.")
        else:
            st.dataframe(monthly_df)
            st.altair_chart(
                render_chart(monthly_df, "Win rate (30 days)", "win_rate"),
                use_container_width=True,
            )
            st.altair_chart(
                render_chart(monthly_df, "Games played (30 days)", "games"),
                use_container_width=True,
            )

    st.subheader("Group highlights")
    best_week = (
        highlight_top_players(weekly_df, "win_rate")
        if "weekly_df" in locals() and not weekly_df.empty
        else pd.DataFrame()
    )
    worst_week = (
        highlight_top_players(add_loss_rate(weekly_df), "loss_rate")
        if "weekly_df" in locals() and not weekly_df.empty
        else pd.DataFrame()
    )

    if not weekly_df.empty:
        st.markdown("**Top win rates (7 days)**")
        st.dataframe(best_week)
        st.markdown("**Most losses by percentage (7 days)**")
        st.dataframe(worst_week)

    st.markdown(
        """
    **Tips**
    - Conduct score is not exposed via the OpenDota public API. If Valve exposes it via the Steam Web API in the future, this dashboard can be extended to include it.
    - Deploy to Streamlit Community Cloud to share with friends and link from Discord.
    - Increase the `limit` parameter in `fetch_matches` if you want to analyze more games.
    """
    )


if __name__ == "__main__":
    main()
