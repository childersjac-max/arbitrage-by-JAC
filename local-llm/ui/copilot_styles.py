"""Copilot-like visual design for Gradio."""

from __future__ import annotations

import gradio as gr

from performance_profiles import PerformanceProfile


COPILOT_CSS = """
/* ---- App shell ---- */
.copilot-app { max-width: 960px; margin: 0 auto; }
.copilot-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; margin-bottom: 8px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 55%, #3b82f6 100%);
  color: #fff; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}
.copilot-header h1 { margin: 0; font-size: 1.25rem; font-weight: 600; letter-spacing: -0.02em; }
.copilot-header .sub { opacity: 0.9; font-size: 0.8rem; margin-top: 4px; }
.copilot-badge {
  display: inline-block; padding: 4px 10px; border-radius: 999px;
  background: rgba(255,255,255,0.2); font-size: 0.75rem; font-weight: 500;
}
.copilot-status-bar {
  font-size: 0.8rem; color: var(--body-text-color-subdued);
  padding: 6px 12px; margin-bottom: 8px;
  border-radius: 8px; background: var(--background-fill-secondary);
}

/* ---- Chat area ---- */
#copilot-chat {
  min-height: 420px !important;
  max-height: min(62vh, 640px) !important;
  border: 1px solid var(--border-color-primary) !important;
  border-radius: 16px !important;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.04);
}
#copilot-chat .message { padding: 10px 14px !important; line-height: 1.55 !important; }
#copilot-chat .user { background: #eff6ff !important; border-radius: 16px 16px 4px 16px !important; }
#copilot-chat .bot {
  background: var(--background-fill-primary) !important;
  border-radius: 16px 16px 16px 4px !important;
  border: 1px solid var(--border-color-primary) !important;
  max-height: 420px; overflow-y: auto;
}
.dark #copilot-chat .user { background: #1e3a5f !important; color: #e2e8f0 !important; }

/* ---- Sticky composer ---- */
.copilot-composer-wrap {
  position: sticky; bottom: 0; z-index: 10;
  padding: 12px 0 4px;
  background: linear-gradient(to top, var(--background-fill-primary) 85%, transparent);
}
.copilot-composer {
  border: 1px solid var(--border-color-primary) !important;
  border-radius: 16px !important;
  padding: 4px !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.copilot-composer textarea {
  border: none !important; box-shadow: none !important;
  font-size: 0.95rem !important; resize: none !important;
}
.copilot-send-btn {
  min-width: 96px !important; border-radius: 12px !important;
  font-weight: 600 !important;
}

/* ---- Suggestion chips ---- */
.copilot-suggestions .gr-button {
  font-size: 0.8rem !important; border-radius: 999px !important;
  padding: 6px 14px !important;
}

/* ---- Toolbar ---- */
.copilot-toolbar .gr-button { font-size: 0.85rem !important; }

/* ---- Profile pills ---- */
.copilot-profile .wrap { gap: 8px !important; }
.copilot-profile label {
  border-radius: 999px !important; padding: 6px 14px !important;
  border: 1px solid var(--border-color-primary) !important;
}

/* ---- Typing animation (assistant placeholders) ---- */
@keyframes copilot-pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
#copilot-chat .bot:has(p:first-child:is([data-thinking])) {
  animation: copilot-pulse 1.2s ease-in-out infinite;
}

/* Hide default footer clutter in chat tab */
.copilot-chat-tab > .prose:first-child { display: none; }
"""

COPILOT_HEAD_JS = """
<script>
(function() {
  function scrollChatToBottom() {
    const root = document.querySelector('#copilot-chat');
    if (!root) return;
    const scrollers = root.querySelectorAll('[data-testid="bot"], .bubble-wrap, .message-wrap');
  const panel = root.closest('.block') || root;
    if (panel) panel.scrollTop = panel.scrollHeight;
  }
  const obs = new MutationObserver(() => scrollChatToBottom());
  window.addEventListener('load', () => {
    const root = document.querySelector('#copilot-chat');
    if (root) obs.observe(root, { childList: true, subtree: true, characterData: true });
  });
})();
</script>
"""

SUGGESTED_PROMPTS = [
    "Explain sports arbitrage in 3 bullet points",
    "What should live in harvester vs local-llm?",
    "Sketch a minimal Odds API integrator in Python",
    "How do I normalize team names to JSON?",
]


def render_header_html(profile: PerformanceProfile, *, ollama_ok: bool = True) -> str:
    status = "Online" if ollama_ok else "Check Ollama"
    return f"""
<div class="copilot-header">
  <div>
    <h1>Local Copilot</h1>
    <div class="sub">Private · Ollama on your machine · No cloud</div>
  </div>
  <div style="text-align:right">
    <span class="copilot-badge">{profile.label}</span>
    <div class="sub" style="margin-top:6px">{profile.ollama_model}</div>
    <div class="sub">{status}</div>
  </div>
</div>
{COPILOT_HEAD_JS}
"""


def copilot_theme() -> gr.Theme:
    return gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.slate,
        neutral_hue=gr.themes.colors.gray,
        font=gr.themes.GoogleFont("Segoe UI"),
    ).set(
        body_background_fill="*neutral_50",
        block_background_fill="white",
        block_border_width="1px",
        block_radius="12px",
        button_large_radius="12px",
        input_radius="12px",
    )
