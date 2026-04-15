# Dota 2 Friends Dashboard + Discord Bot

This repo includes:
1. **Streamlit dashboard** (`dashboard.py`) for interactive charts.
2. **Discord bot** (`discord_bot.py`) with slash commands for weekly leaderboards.

## Discord commands
- `/player add steam_id:<steam64> alias:<name>`
- `/player remove steam_id:<steam64>`
- `/player activate steam_id:<steam64>`
- `/player deactivate steam_id:<steam64>`
- `/player list`
- `/weekly` (top + worst active players in last 7 days)
- `/invite` (prints OAuth invite URL)

The bot stores tracked players per-server in `players.json`.

---

## Local run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set env vars:

```bash
export DISCORD_BOT_TOKEN="<your_discord_bot_token>"
export DOTA_API_KEY="<optional_api_key>"
# Optional for fast slash command registration in one test server:
export GUILD_ID="<your_discord_server_id>"
```

Run bot:

```bash
python discord_bot.py
```

Run dashboard:

```bash
streamlit run dashboard.py
```

---

## Discord app setup

1. Go to <https://discord.com/developers/applications>
2. Create app → add Bot.
3. Copy **Bot Token** and set `DISCORD_BOT_TOKEN`.
4. OAuth2 URL Generator:
   - Scopes: `bot`, `applications.commands`
   - Bot permissions: `Send Messages`, `Embed Links`
5. Invite to your server.

Direct invite URL format:

```text
https://discord.com/oauth2/authorize?client_id=<APPLICATION_ID>&permissions=18432&scope=bot%20applications.commands
```

---

## 24/7 hosting (chosen: Render)

This repo now includes `render.yaml` for one-click Render deployment as a **worker** process.

### Steps
1. Push this repo to GitHub.
2. In Render: **New +** → **Blueprint**.
3. Select your repo (Render reads `render.yaml`).
4. Set environment variables in Render:
   - `DISCORD_BOT_TOKEN` (required)
   - `DOTA_API_KEY` (optional)
   - `GUILD_ID` (optional, recommended for testing)
5. Deploy.

Render start command is already configured as:

```bash
python discord_bot.py
```

---

## Security note

If you ever paste your bot token publicly, **immediately regenerate it** in the Discord Developer Portal.

---

## Project files
- `dota_service.py`: shared OpenDota + leaderboard logic
- `discord_bot.py`: Discord bot and slash commands
- `dashboard.py`: Streamlit dashboard
- `render.yaml`: Render deployment blueprint
- `.env.example`: environment variable template
