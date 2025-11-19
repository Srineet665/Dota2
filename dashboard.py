import os
from typing import Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import requests
import streamlit as st

STEAM_EPOCH = 76561197960265728
DEFAULT_STEAM_IDS = [
    "76561198355928347",  # You
    "76561198220727716",  # Friend
]

def steam64_to_account_id(steam64: str) -> Optional[int]:
    try:
        return int(steam64) - STEAM_EPOCH
    except ValueError:
        return None


def normalize_ids(raw_text: str) -> List[str]:
    candidates = [part.strip() for part in raw_text.replace("\n", ",").split(",")]
    return [c for c in candidates if c.isdigit()]


@st.cache_data(ttl=300)
def fetch_matches(account_id: int, days: int, api_key: Optional[str]) -> pd.DataFrame:
    params = {"date": days, "limit": 200}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.opendota.com/api/players/{account_id}/matches"
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    matches = pd.DataFrame(response.json())
    if matches.empty:
        return matches

    matches["win"] = matches.apply(
        lambda row: (row["player_slot"] < 128) == bool(row["radiant_win"]), axis=1
    )
    matches["loss"] = ~matches["win"]
    matches["start_time"] = pd.to_datetime(matches["start_time"], unit="s")
    return matches


def summarize_matches(df: pd.DataFrame, steam_id: str, label: str) -> Dict[str, object]:
    total = len(df)
    wins = int(df["win"].sum())
    losses = int(df["loss"].sum())
    win_rate = (wins / total * 100) if total else 0
    avg_k = df["kills"].mean() if total else 0
    avg_d = df["deaths"].mean() if total else 0
    avg_a = df["assists"].mean() if total else 0

    best_streak = 0
    if total:
        sorted_wins = df.sort_values("start_time", ascending=True)["win"].tolist()
        current = 0
        for result in sorted_wins:
            if result:
                current += 1
                best_streak = max(best_streak, current)
            else:
                current = 0
    return {
        "steam_id": steam_id,
        "label": label,
        "games": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "avg_k": round(avg_k, 1),
        "avg_d": round(avg_d, 1),
        "avg_a": round(avg_a, 1),
        "best_streak": best_streak,
    }


def collect_period_summaries(
    steam_ids: List[str], days: int, api_key: Optional[str]
) -> Tuple[pd.DataFrame, List[str]]:
    rows = []
    errors = []
    for sid in steam_ids:
        account_id = steam64_to_account_id(sid)
        if account_id is None:
            errors.append(f"Invalid Steam64 ID: {sid}")
            continue
        try:
            matches = fetch_matches(account_id, days, api_key)
        except requests.HTTPError as exc:  # type: ignore
            errors.append(f"HTTP error for {sid}: {exc}")
            continue
        except requests.RequestException as exc:  # type: ignore
            errors.append(f"Network error for {sid}: {exc}")
            continue
        rows.append(summarize_matches(matches, sid, f"Last {days} days"))
    df = pd.DataFrame(rows)
    return df, errors


def highlight_top_players(df: pd.DataFrame, metric: str, top_n: int = 3) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values(metric, ascending=False).head(top_n)[
        ["steam_id", "win_rate", "games", "wins", "losses", metric]
    ]


def add_loss_rate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    enriched = df.copy()
    enriched["loss_rate"] = enriched.apply(
        lambda row: (row["losses"] / row["games"] * 100) if row["games"] else 0, axis=1
    )
    return enriched


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
        weekly_df, weekly_errors = collect_period_summaries(steam_ids, 7, api_key)
        if weekly_errors:
            st.error("\n".join(weekly_errors))
        if weekly_df.empty:
            st.info("No matches found for the last 7 days.")
        else:
            st.dataframe(weekly_df)
            st.altair_chart(render_chart(weekly_df, "Win rate (7 days)", "win_rate"), use_container_width=True)
            st.altair_chart(render_chart(weekly_df, "Games played (7 days)", "games"), use_container_width=True)

    with col2:
        st.subheader("Last 30 days")
        monthly_df, monthly_errors = collect_period_summaries(steam_ids, 30, api_key)
        if monthly_errors:
            st.error("\n".join(monthly_errors))
        if monthly_df.empty:
            st.info("No matches found for the last 30 days.")
        else:
            st.dataframe(monthly_df)
            st.altair_chart(render_chart(monthly_df, "Win rate (30 days)", "win_rate"), use_container_width=True)
            st.altair_chart(render_chart(monthly_df, "Games played (30 days)", "games"), use_container_width=True)

    st.subheader("Group highlights")
    best_week = (
        highlight_top_players(weekly_df, "win_rate") if "weekly_df" in locals() else pd.DataFrame()
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

    st.markdown("""
    **Tips**
    - Conduct score is not exposed via the OpenDota public API. If Valve exposes it via the Steam Web API in the future, this dashboard can be extended to include it.
    - Deploy to Streamlit Community Cloud to share with friends and link from Discord.
    - Increase the `limit` parameter in `fetch_matches` if you want to analyze more games.
    """)


if __name__ == "__main__":
    main()
