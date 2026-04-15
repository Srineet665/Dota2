from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests

STEAM_EPOCH = 76561197960265728
OPEN_DOTA_BASE_URL = "https://api.opendota.com/api"


PLACEHOLDER_API_KEYS = {"optional", "none", "null", "your_api_key", "your_opendota_or_steam_key_here"}


def normalize_api_key(api_key: Optional[str]) -> Optional[str]:
    if api_key is None:
        return None

    cleaned = api_key.strip()
    if not cleaned:
        return None

    if cleaned.lower() in PLACEHOLDER_API_KEYS:
        return None

    if cleaned.lower().startswith("your_"):
        return None

    return cleaned


@dataclass
class PlayerSummary:
    steam_id: str
    label: str
    games: int
    wins: int
    losses: int
    win_rate: float
    avg_k: float
    avg_d: float
    avg_a: float
    best_streak: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "steam_id": self.steam_id,
            "label": self.label,
            "games": self.games,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "avg_k": self.avg_k,
            "avg_d": self.avg_d,
            "avg_a": self.avg_a,
            "best_streak": self.best_streak,
        }


class DotaServiceError(RuntimeError):
    """Raised when the Dota API call fails or response is malformed."""


def steam64_to_account_id(steam64: str) -> Optional[int]:
    try:
        return int(steam64) - STEAM_EPOCH
    except ValueError:
        return None


def normalize_ids(raw_text: str) -> List[str]:
    candidates = [part.strip() for part in raw_text.replace("\n", ",").split(",")]
    return [c for c in candidates if c.isdigit()]


def fetch_matches(account_id: int, days: int, api_key: Optional[str]) -> pd.DataFrame:
    clean_key = normalize_api_key(api_key)
    params: Dict[str, object] = {"date": days, "limit": 200}
    if clean_key:
        params["api_key"] = clean_key

    url = f"{OPEN_DOTA_BASE_URL}/players/{account_id}/matches"
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
    except requests.exceptions.SSLError as exc:
        if clean_key:
            retry_params = {"date": days, "limit": 200}
            try:
                response = requests.get(url, params=retry_params, timeout=20)
                response.raise_for_status()
            except requests.RequestException as retry_exc:
                raise DotaServiceError(
                    f"Failed to fetch matches for account_id={account_id} with and without api_key: {retry_exc}"
                ) from retry_exc
        else:
            raise DotaServiceError(f"Failed to fetch matches for account_id={account_id}: {exc}") from exc
    except requests.RequestException as exc:
        raise DotaServiceError(f"Failed to fetch matches for account_id={account_id}: {exc}") from exc

    try:
        matches = pd.DataFrame(response.json())
    except ValueError as exc:
        raise DotaServiceError(f"Unexpected JSON for account_id={account_id}: {exc}") from exc

    if matches.empty:
        return matches

    required = {"player_slot", "radiant_win", "start_time", "kills", "deaths", "assists"}
    missing = required.difference(matches.columns)
    if missing:
        raise DotaServiceError(
            f"OpenDota response missing fields for account_id={account_id}: {sorted(missing)}"
        )

    matches["win"] = matches.apply(
        lambda row: (row["player_slot"] < 128) == bool(row["radiant_win"]), axis=1
    )
    matches["loss"] = ~matches["win"]
    matches["start_time"] = pd.to_datetime(matches["start_time"], unit="s", utc=True)
    return matches


def summarize_matches(df: pd.DataFrame, steam_id: str, label: str) -> PlayerSummary:
    total = len(df)
    wins = int(df["win"].sum()) if total else 0
    losses = int(df["loss"].sum()) if total else 0
    win_rate = (wins / total * 100) if total else 0.0
    avg_k = float(df["kills"].mean()) if total else 0.0
    avg_d = float(df["deaths"].mean()) if total else 0.0
    avg_a = float(df["assists"].mean()) if total else 0.0

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

    return PlayerSummary(
        steam_id=steam_id,
        label=label,
        games=total,
        wins=wins,
        losses=losses,
        win_rate=round(win_rate, 1),
        avg_k=round(avg_k, 1),
        avg_d=round(avg_d, 1),
        avg_a=round(avg_a, 1),
        best_streak=best_streak,
    )


def collect_period_summaries(
    steam_ids: Iterable[str], days: int, api_key: Optional[str]
) -> tuple[pd.DataFrame, List[str]]:
    rows: List[Dict[str, object]] = []
    errors: List[str] = []

    for sid in steam_ids:
        account_id = steam64_to_account_id(sid)
        if account_id is None:
            errors.append(f"Invalid Steam64 ID: {sid}")
            continue

        try:
            matches = fetch_matches(account_id, days, api_key)
            summary = summarize_matches(matches, sid, f"Last {days} days")
            rows.append(summary.to_dict())
        except DotaServiceError as exc:
            errors.append(str(exc))

    return pd.DataFrame(rows), errors


def add_loss_rate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    enriched = df.copy()
    enriched["loss_rate"] = enriched.apply(
        lambda row: (row["losses"] / row["games"] * 100) if row["games"] else 0,
        axis=1,
    )
    return enriched


def highlight_top_players(df: pd.DataFrame, metric: str, top_n: int = 3) -> pd.DataFrame:
    if df.empty:
        return df

    return df.sort_values(metric, ascending=False).head(top_n)[
        ["steam_id", "win_rate", "games", "wins", "losses", metric]
    ]


def format_fetch_timestamp(ts: Optional[datetime] = None) -> str:
    current = ts or datetime.now(timezone.utc)
    return current.strftime("%Y-%m-%d %H:%M UTC")
