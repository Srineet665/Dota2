from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import discord
from discord import app_commands
from discord.ext import commands

from dota_service import (
    add_loss_rate,
    collect_period_summaries,
    format_fetch_timestamp,
    highlight_top_players,
)

DATA_FILE = Path("players.json")


class PlayerStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.data = {}
            return
        with self.path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        self.data = payload if isinstance(payload, dict) else {}

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, sort_keys=True)

    def guild_players(self, guild_id: int) -> Dict[str, Any]:
        key = str(guild_id)
        if key not in self.data:
            self.data[key] = {"players": {}}
        if "players" not in self.data[key]:
            self.data[key]["players"] = {}
        return self.data[key]["players"]

    def upsert_player(self, guild_id: int, steam_id: str, alias: Optional[str], active: bool = True) -> None:
        players = self.guild_players(guild_id)
        players[steam_id] = {
            "steam_id": steam_id,
            "alias": alias or "",
            "active": active,
        }
        self.save()

    def remove_player(self, guild_id: int, steam_id: str) -> bool:
        players = self.guild_players(guild_id)
        existed = steam_id in players
        if existed:
            players.pop(steam_id)
            self.save()
        return existed

    def set_active(self, guild_id: int, steam_id: str, active: bool) -> bool:
        players = self.guild_players(guild_id)
        if steam_id not in players:
            return False
        players[steam_id]["active"] = active
        self.save()
        return True

    def list_players(self, guild_id: int) -> List[Dict[str, Any]]:
        players = self.guild_players(guild_id)
        return list(players.values())

    def active_steam_ids(self, guild_id: int) -> List[str]:
        players = self.guild_players(guild_id)
        return [sid for sid, obj in players.items() if obj.get("active", True)]

    def alias_for(self, guild_id: int, steam_id: str) -> str:
        players = self.guild_players(guild_id)
        alias = players.get(steam_id, {}).get("alias", "")
        return alias or steam_id


class DotaDiscordBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.store = PlayerStore(DATA_FILE)
        self.api_key = os.getenv("DOTA_API_KEY")

    async def setup_hook(self) -> None:
        await self.tree.sync()


bot = DotaDiscordBot()
player_group = app_commands.Group(name="player", description="Manage tracked Dota players")


def build_invite_url(application_id: int) -> str:
    params = urlencode(
        {
            "client_id": str(application_id),
            "permissions": "18432",  # Send Messages + Embed Links
            "scope": "bot applications.commands",
        }
    )
    return f"https://discord.com/oauth2/authorize?{params}"


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user}")


@player_group.command(name="add", description="Add or update a tracked Steam64 player")
@app_commands.describe(steam_id="Steam64 ID", alias="Optional display name")
async def player_add(interaction: discord.Interaction, steam_id: str, alias: Optional[str] = None) -> None:
    if not steam_id.isdigit():
        await interaction.response.send_message("Steam ID must be a numeric Steam64 ID.", ephemeral=True)
        return

    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    bot.store.upsert_player(guild.id, steam_id, alias=alias, active=True)
    display_name = alias or steam_id
    await interaction.response.send_message(f"Added player **{display_name}** (`{steam_id}`) as active.")


@player_group.command(name="remove", description="Remove a tracked Steam64 player")
@app_commands.describe(steam_id="Steam64 ID")
async def player_remove(interaction: discord.Interaction, steam_id: str) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    removed = bot.store.remove_player(guild.id, steam_id)
    if removed:
        await interaction.response.send_message(f"Removed `{steam_id}`.")
    else:
        await interaction.response.send_message(f"`{steam_id}` is not tracked.", ephemeral=True)


@player_group.command(name="activate", description="Mark a tracked player active")
@app_commands.describe(steam_id="Steam64 ID")
async def player_activate(interaction: discord.Interaction, steam_id: str) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    updated = bot.store.set_active(guild.id, steam_id, True)
    if updated:
        await interaction.response.send_message(f"Activated `{steam_id}`.")
    else:
        await interaction.response.send_message(f"`{steam_id}` is not tracked.", ephemeral=True)


@player_group.command(name="deactivate", description="Mark a tracked player inactive")
@app_commands.describe(steam_id="Steam64 ID")
async def player_deactivate(interaction: discord.Interaction, steam_id: str) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    updated = bot.store.set_active(guild.id, steam_id, False)
    if updated:
        await interaction.response.send_message(f"Deactivated `{steam_id}`.")
    else:
        await interaction.response.send_message(f"`{steam_id}` is not tracked.", ephemeral=True)


@player_group.command(name="list", description="List tracked players")
async def player_list(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    players = bot.store.list_players(guild.id)
    if not players:
        await interaction.response.send_message("No players tracked yet. Use `/player add`.", ephemeral=True)
        return

    lines = []
    for player in players:
        sid = player["steam_id"]
        alias = player.get("alias", "") or sid
        marker = "🟢" if player.get("active", True) else "⚫"
        lines.append(f"{marker} **{alias}** (`{sid}`)")

    await interaction.response.send_message("\n".join(lines))




@bot.tree.command(name="invite", description="Get the bot invite URL")
async def invite(interaction: discord.Interaction) -> None:
    application_id = bot.application_id
    if application_id is None:
        await interaction.response.send_message(
            "Application ID is unavailable right now. Try again in a moment.",
            ephemeral=True,
        )
        return

    url = build_invite_url(application_id)
    await interaction.response.send_message(f"Invite URL: {url}", ephemeral=True)

@bot.tree.command(name="weekly", description="Show weekly leaderboard for active players")
async def weekly(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    steam_ids = bot.store.active_steam_ids(guild.id)
    if not steam_ids:
        await interaction.response.send_message(
            "No active players found. Add players with `/player add`.", ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    weekly_df, errors = collect_period_summaries(steam_ids, 7, bot.api_key)
    if weekly_df.empty:
        detail = "\n".join(errors) if errors else "No matches found in the last 7 days."
        await interaction.followup.send(f"Could not build weekly leaderboard.\n{detail}")
        return

    active_df = weekly_df[weekly_df["games"] > 0].copy()
    if active_df.empty:
        await interaction.followup.send("No active players played any matches in the last 7 days.")
        return

    ranked_df = active_df.copy()
    ranked_df["steam_id"] = ranked_df["steam_id"].map(lambda sid: bot.store.alias_for(guild.id, sid))

    top = highlight_top_players(ranked_df, "win_rate", top_n=5)
    worst = highlight_top_players(add_loss_rate(ranked_df), "loss_rate", top_n=5)

    embed = discord.Embed(
        title="Dota 2 Weekly Leaderboard",
        description=f"Active players with matches in last 7 days. Updated {format_fetch_timestamp()}",
        color=discord.Color.blue(),
    )

    top_lines = []
    for idx, row in top.reset_index(drop=True).iterrows():
        top_lines.append(
            f"`#{idx+1}` **{row['steam_id']}** — {row['win_rate']}% WR ({int(row['wins'])}-{int(row['losses'])}, {int(row['games'])} games)"
        )

    worst_lines = []
    for idx, row in worst.reset_index(drop=True).iterrows():
        worst_lines.append(
            f"`#{idx+1}` **{row['steam_id']}** — {row['loss_rate']:.1f}% loss ({int(row['wins'])}-{int(row['losses'])}, {int(row['games'])} games)"
        )

    embed.add_field(name="Top performers", value="\n".join(top_lines) or "N/A", inline=False)
    embed.add_field(name="Worst performers", value="\n".join(worst_lines) or "N/A", inline=False)

    if errors:
        embed.set_footer(text=f"Warnings: {' | '.join(errors[:2])}")

    await interaction.followup.send(embed=embed)


bot.tree.add_command(player_group)


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set.")
    bot.run(token)


if __name__ == "__main__":
    main()
