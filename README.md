# Dota 2 Friends Dashboard

A lightweight Streamlit dashboard that compares recent Dota 2 match results for a group of friends. Supply your Steam64 IDs (from your profile URLs) and an optional OpenDota/Dota Web API key to see who is winning or losing the most over the past week or month.

## Features
- Converts Steam64 profile IDs into Dota account IDs automatically.
- Pulls recent matches for each player from the OpenDota API (supports an API key if you have one).
- Summary tables for the last 7 days and 30 days: games played, wins, losses, win rate, average K/D/A, and streak highlights.
- Highlights the top winners and top losers in your group.
- Designed for easy embedding in Discord via Streamlit Community Cloud or any HTTPS host.

## Quick start
1. (Recommended) Use Python 3.10+ and create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the dashboard locally (add your API key via env var or in the UI):
   ```bash
   # Optionally set your OpenDota/Steam Web API key for higher rate limits
   export DOTA_API_KEY="<your_api_key>"

   # Launch Streamlit
   streamlit run dashboard.py
   ```
4. Open the URL Streamlit prints (default: http://localhost:8501) to interact with the dashboard. Paste your Steam64 profile IDs (one per line or comma-separated). Add your OpenDota or Steam API key (optional) to improve rate limits.

## Embedding in Discord
- Deploy the app to a public URL (e.g., Streamlit Community Cloud or any HTTPS host).
- In Discord, create an embed in a message or channel topic that links to the hosted dashboard URL. Discord does not natively render arbitrary iframes, so the link/preview card is the most reliable way to surface the dashboard to your friends.
- For lightweight status messages, you can also use Discord webhooks that post the summary tables as images (future enhancement).

## Environment variables
- `DOTA_API_KEY` (optional): Your OpenDota or Steam Web API key. You can also paste it into the dashboard sidebar at runtime.

## Supported Steam IDs
The dashboard ships with two example Steam64 IDs based on your profiles. Replace or extend them in the text area when running the app.

