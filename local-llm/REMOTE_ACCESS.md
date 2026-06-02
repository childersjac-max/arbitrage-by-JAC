# Use the local LLM chat from your phone (anywhere)

Your PC runs **Ollama** and the **Gradio** UI. The phone is only a browser. The PC must stay on and connected to the internet.

## Option A — Public link (easiest, no VPN)

Gradio creates a temporary **https://….gradio.live** URL that works on cellular or any Wi‑Fi.

### Windows (recommended)

1. Start **Ollama** (Start menu).
2. Double-click **`run-local-llm-remote.bat`** at the repo root  
   (or `local-llm/scripts/run_remote.bat`).
3. In the terminal, copy the line:
   ```text
   AWAY FROM HOME — open this URL on your phone:
     https://xxxxxxxx.gradio.live
   ```
4. On your phone, open that URL and log in with:
   - **User:** `admin` (unless you changed it)
   - **Password:** printed when you first ran `enable_remote.py`, or in `local-llm/.env` as `LOCAL_LLM_UI_AUTH_PASSWORD`

The same URL is saved in `local-llm/data/remote_url.txt`.

### One-time setup (Git Bash)

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
source .venv/Scripts/activate
python scripts/enable_remote.py
python web_app.py
```

### Important

| Topic | Detail |
|--------|--------|
| **Security** | The link is on the public internet. Always use the login password. Do not commit `.env` to git. |
| **Lifetime** | Gradio share links last about **72 hours** per session; restart the app for a new link. |
| **PC** | Must stay on with Ollama + the app running. |
| **Speed** | Still limited by your home PC’s CPU. |

To turn off remote mode, set `LOCAL_LLM_UI_SHARE=0` in `.env` and use normal `python web_app.py`.

---

## Option B — Tailscale (private, best for daily use)

No public URL. Your phone joins a private network to your PC.

1. Install [Tailscale](https://tailscale.com/download) on your **PC** and **phone** (same account).
2. On the PC, enable LAN mode once:
   ```bash
   python scripts/enable_phone.py
   ```
3. In the Tailscale app on your phone, note your PC’s Tailscale IP (e.g. `100.64.12.34`).
4. On the PC, run the app as usual (`python web_app.py` or `run_phone.bat`).
5. On your phone (Tailscale connected), open:
   ```text
   http://100.64.12.34:7860
   ```
   (Use your PC’s real Tailscale IP.)

Works on cellular through Tailscale’s encrypted tunnel. No Gradio public link.

---

## Same home Wi‑Fi only

See the main README: `scripts/run_phone.bat` or `LOCAL_LLM_UI_LAN=1` — no public internet exposure.
