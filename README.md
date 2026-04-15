# Dota 2 Friends Dashboard + Discord Bot

This repo now includes two ways to view your Dota stats:

1. **Streamlit dashboard** (`dashboard.py`) for interactive web charts.
2. **Discord slash-command bot** (`discord_bot.py`) that posts a weekly leaderboard on demand.

The Discord bot supports:
- `/player add` to register players
- `/player remove`
- `/player activate`
- `/player deactivate`
- `/player list`
- `/weekly` to show top and worst performers among active players in the past 7 days

---

## Quick start (local)

### 1) Create env + install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Optional API key (for higher OpenDota limits)

```bash
export DOTA_API_KEY="<your_opendota_or_steam_api_key>"
```

### 3A) Run Streamlit dashboard

```bash
streamlit run dashboard.py
```

### 3B) Run Discord bot

```bash
export DISCORD_BOT_TOKEN="<your_discord_bot_token>"
python discord_bot.py
```

---

## Discord app setup (one-time)

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application and add a **Bot**.
3. Under **Bot**, copy the token and set it as `DISCORD_BOT_TOKEN`.
4. Under **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`
5. Open the generated URL to invite your bot to your server (or run `/invite` once the bot is online).

### Slash commands in your server

After the bot starts, use:

- `/player add steam_id:<steam64> alias:<name>`
- `/player deactivate steam_id:<steam64>`
- `/player activate steam_id:<steam64>`
- `/player list`
- `/weekly`
- `/invite` (prints your OAuth invite URL)

The bot stores guild player settings in `players.json`.

---

## Deploy 24/7 (recommended)

Use a host that supports long-running Python processes (Railway, Render, Fly.io, VPS).

### Example process command

```bash
python discord_bot.py
```

### Required env vars on host

- `DISCORD_BOT_TOKEN` (required)
- `DOTA_API_KEY` (optional)

---

## Files

- `dota_service.py`: shared OpenDota API + leaderboard logic
- `discord_bot.py`: Discord slash-command bot
- `dashboard.py`: Streamlit dashboard
- `players.json`: created automatically for tracked players

