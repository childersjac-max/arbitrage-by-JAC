# Start multi-agent from scratch (Windows Git Bash)

Assume **nothing** is running. Follow in order.

---

## A. One-time: clone repo

```bash
cd ~
mkdir -p Projects
cd Projects
git clone https://github.com/childersjac-max/arbitrage-by-JAC.git
cd arbitrage-by-JAC
git fetch origin
git checkout origin/cursor/fix-chat-workflow-ui-state-4fea -- local-llm/workload_lock.py local-llm/ui/multi_agent_stream.py local-llm/ui/chat_tab.py local-llm/ui_state.py multi-agent-llm/pipeline_core.py
git checkout origin/cursor/deploy-full-arb-dashboard-4fea -- prompts/llm_deploy_phases prompts/llm_deploy_full_arb_dashboard.txt
```

---

## B. One-time: install Ollama + models

1. Install from https://ollama.com and open **Ollama** from Start menu (leave running).
2. In Git Bash:

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
curl -s http://127.0.0.1:11434/api/tags
```

Expect JSON with both models listed.

3. Warm up (first CPU load takes minutes):

```bash
ollama run qwen2.5:3b-instruct-q4_K_M
```

Type `hi`, wait for reply, then `/bye`.

---

## C. One-time: Python environments

### Harvester venv (orchestrator + dashboard)

```bash
cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
bash bootstrap.sh
source venv/Scripts/activate
pip install -r requirements.txt
```

### Odds API key (once — saved forever)

```bash
notepad ~/Projects/arbitrage-by-JAC/harvester/.env
```

Set one line: `ODDS_API_KEY=your_key_from_the-odds-api.com`  
Save. Never paste the key in chat.

Verify:

```bash
cd ~/Projects/arbitrage-by-JAC/sports_arbitrage_pipeline
source venv/Scripts/activate
cd ../harvester
python cli.py health
```

Expect: `the_odds_api: OK`

### Local LLM venv (Gradio + multi-agent UI)

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
bash scripts/setup.sh
source .venv/Scripts/activate
python doctor.py
```

Expect: `ollama: OK`

### Multi-agent config

```bash
cd ~/Projects/arbitrage-by-JAC/multi-agent-llm
cp .env.example .env
notepad .env
```

Set at minimum:

```env
PROJECT_ROOT=C:/Users/child/Projects/arbitrage-by-JAC
TIMEOUT_PLANNER_SEC=600
TIMEOUT_CODER_SEC=900
TIMEOUT_REVIEWER_SEC=600
MODEL_PLANNER=qwen2.5:3b-instruct-q4_K_M
MODEL_CODER=qwen2.5-coder:7b-instruct-q4_K_M
MODEL_REVIEWER=qwen2.5:3b-instruct-q4_K_M
INJECT_FILE_MAP=0
```

`INJECT_FILE_MAP=0` keeps prompts smaller for CPU.

---

## D. Every session: start multi-agent UI

**Terminal 1 — keep Ollama running** (Start menu app).

**Terminal 2 — Gradio:**

```bash
cd ~/Projects/arbitrage-by-JAC/local-llm
source .venv/Scripts/activate
python web_app.py
```

Open **http://127.0.0.1:7860**

1. Tab **Chat**
2. **Chat mode** → **Multi-agent (Planner → Coder → Reviewer)**
3. Click **Wake up model** (wait 1–3 min on CPU)
4. Paste **one phase prompt** from `prompts/llm_deploy_phases/` (see below)
5. Send — wait; Planner can take **5+ minutes** on first run

---

## E. Six phase prompts (paste one per session)

| Order | File | What it does |
|-------|------|----------------|
| 1 | `PHASE_1_harvester_config_ingest.txt` | **All active sports** × h2h/spreads/totals/outrights |
| — | `ALL_SPORTS_AND_MARKETS.txt` | Canonical sport keys + all bet types |
| 2 | `PHASE_2_event_markets_multisport.txt` | Code: props, alts, all leagues |
| 3 | `PHASE_3_arb_engine_all_lines.txt` | Code: arb math for all market types |
| 4 | `PHASE_4_dashboard_lan_url.txt` | Code: deploy :8765 + phone URL |
| 5 | `PHASE_5_verify_browser.txt` | Run dashboard, confirm in browser |
| 6 | `PHASE_6_always_on_optional.txt` | Auto-refresh / scheduled runs |

**Do not paste all six at once.** Finish each phase; paste terminal output; then next phase.

---

## F. Two apps — two ports

| URL | App |
|-----|-----|
| http://127.0.0.1:7860 | Local LLM multi-agent **chat** |
| http://127.0.0.1:8765 | **Arbitrage results dashboard** (after Phase 4–5) |

---

## G. Troubleshooting

| Error | Fix |
|-------|-----|
| `pydantic_settings` missing | Use `sports_arbitrage_pipeline/venv`, not `local-llm/.venv` |
| `WorkloadKind.MULTI_AGENT` | Pull `local-llm/workload_lock.py` from fix branch |
| Read timed out (120s) | Set `TIMEOUT_PLANNER_SEC=600` in `multi-agent-llm/.env`; warm Ollama first |
| Could not reach Ollama | Start Ollama app; `curl http://127.0.0.1:11434/api/tags` |

---

## H. Terminal-only multi-agent (no browser)

```bash
cd ~/Projects/arbitrage-by-JAC/multi-agent-llm
source .venv/Scripts/activate 2>/dev/null || bash setup.sh && source .venv/Scripts/activate
python multi_agent_runner.py --interactive
```
