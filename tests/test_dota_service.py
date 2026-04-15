import pandas as pd

from dota_service import add_loss_rate, normalize_ids, steam64_to_account_id, summarize_matches


def test_normalize_ids():
    raw = "76561198000000000,\nabc,76561198000000001"
    assert normalize_ids(raw) == ["76561198000000000", "76561198000000001"]


def test_steam_conversion():
    assert steam64_to_account_id("76561197960265728") == 0
    assert steam64_to_account_id("notanumber") is None


def test_summarize_matches():
    df = pd.DataFrame(
        {
            "win": [True, False, True],
            "loss": [False, True, False],
            "kills": [10, 2, 8],
            "deaths": [3, 7, 4],
            "assists": [15, 5, 12],
            "start_time": pd.to_datetime([1710000000, 1710001000, 1710002000], unit="s", utc=True),
        }
    )
    summary = summarize_matches(df, "76561198000000000", "Last 7 days")
    assert summary.games == 3
    assert summary.wins == 2
    assert summary.losses == 1
    assert summary.best_streak >= 1


def test_add_loss_rate():
    df = pd.DataFrame(
        {
            "steam_id": ["1"],
            "games": [4],
            "wins": [1],
            "losses": [3],
            "win_rate": [25.0],
        }
    )
    out = add_loss_rate(df)
    assert float(out.iloc[0]["loss_rate"]) == 75.0
