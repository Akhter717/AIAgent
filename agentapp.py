"""
Multi-Agent QA Code Generator v3.2
------------------------------------
Assignment: AI Tool Usage + MCP Integration + Real Use Case

✅ AI Tool Usage     → Groq (Llama 3.3 70B) for all 4 agents
✅ MCP Integration   → GitHub MCP — scans existing test files in a repo
                       and performs IMPACT ANALYSIS on newly generated tests
✅ Use Case          → Agentic QA pipeline: URL → Scrape → Locators →
                       Java Selenium TestNG → GitHub Impact Report
✅ Agentic Setup     → Orchestrator + 4 agents with ReAct loop + memory

Changes from v3.1:
  + GitHub MCP Agent (Agent 4): fetches existing test files from a GitHub
    repo, diffs them against newly generated code, and highlights:
      - Overlapping test coverage (duplicate scenarios)
      - Missing scenarios (gaps found in repo but not in new code)
      - New locators not present in the repo (added coverage)
      - Recommendation: merge / replace / extend
  + GitHub config section in sidebar
  + "Impact Analysis" tab in results
  + urllib3 SSL warning suppressed
  + Safer st.secrets key access

No CrewAI · No LangChain · No paid APIs · Groq free tier only
"""

import streamlit as st
import requests
import time
import re
import json
import base64
import urllib3
from bs4 import BeautifulSoup
from groq import Groq

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Agent v3.2",
    page_icon="🤖",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Bricolage+Grotesque:wght@400;600;800&display=swap');

:root {
  --bg:           #080a0f;
  --surface:      #0f1219;
  --card:         #141820;
  --border:       #1e2535;
  --border-bright:#2d3650;
  --green:        #00ff9d;
  --blue:         #4d79ff;
  --orange:       #ff8c42;
  --red:          #ff4d6d;
  --yellow:       #ffd166;
  --purple:       #b57bee;
  --text:         #d4daf0;
  --muted:        #5a6380;
}

html, body, [class*="css"] {
  font-family: 'Bricolage Grotesque', sans-serif;
  background: var(--bg) !important;
  color: var(--text) !important;
}
#MainMenu, footer, header { visibility: hidden; }

[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border-bright) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stSelectbox > div > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stNumberInput > div > div > input {
  background: var(--card) !important;
  border: 1px solid var(--border-bright) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stSidebar"] .sidebar-section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: .9rem 1rem;
  margin-bottom: .9rem;
}
[data-testid="stSidebar"] .sidebar-section-title {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .68rem;
  color: var(--blue);
  letter-spacing: .14em;
  text-transform: uppercase;
  margin-bottom: .7rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: .4rem;
}
[data-testid="stSidebar"] .api-status {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .72rem;
  padding: 5px 10px;
  border-radius: 6px;
  margin-top: .4rem;
}
[data-testid="stSidebar"] .api-ok     { background: rgba(0,255,157,.08); color: var(--green);  border: 1px solid rgba(0,255,157,.3); }
[data-testid="stSidebar"] .api-manual { background: rgba(255,140,66,.08); color: var(--orange); border: 1px solid rgba(255,140,66,.3); }
[data-testid="stSidebar"] .api-gh     { background: rgba(181,123,238,.08); color: var(--purple); border: 1px solid rgba(181,123,238,.3); }

.block-container { padding: 1rem 1.5rem !important; max-width: 1100px !important; }

.hero { padding: 1.6rem .5rem 1.2rem; text-align: center; border-bottom: 1px solid var(--border); margin-bottom: 1.4rem; }
.hero-label { font-family: 'IBM Plex Mono', monospace; font-size: .68rem; color: var(--blue); letter-spacing: .18em; text-transform: uppercase; margin-bottom: .5rem; }
.hero h1 { font-size: clamp(1.6rem,5vw,2.4rem); font-weight: 800; background: linear-gradient(135deg,#00ff9d 0%,#4d79ff 50%,#b57bee 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 .4rem; line-height: 1.15; }
.hero p { color: var(--muted); font-size: .88rem; margin: 0; }

.react-card { background: var(--card); border: 1px solid var(--border); border-left: 3px solid var(--blue); border-radius: 10px; padding: .8rem 1rem; margin-bottom: .7rem; font-size: .82rem; word-break: break-word; }
.react-card.done   { border-left-color: var(--green); }
.react-card.loop   { border-left-color: var(--orange); }
.react-card.error  { border-left-color: var(--red); }
.react-card.orch   { border-left-color: var(--yellow); }
.react-card.github { border-left-color: var(--purple); }

.agent-name { font-family: 'IBM Plex Mono', monospace; font-size: .72rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; margin-bottom: .5rem; }
.agent-name.green  { color: var(--green); }
.agent-name.blue   { color: var(--blue); }
.agent-name.orange { color: var(--orange); }
.agent-name.yellow { color: var(--yellow); }
.agent-name.red    { color: var(--red); }
.agent-name.purple { color: var(--purple); }

.trace-row   { margin-bottom: .35rem; display: flex; flex-wrap: wrap; gap: 4px; }
.trace-label { font-family: 'IBM Plex Mono', monospace; font-size: .7rem; color: var(--muted); min-width: 85px; }
.trace-val   { font-family: 'IBM Plex Mono', monospace; font-size: .76rem; color: var(--text); white-space: pre-wrap; word-break: break-word; flex: 1; }
.trace-val.green  { color: var(--green); }
.trace-val.orange { color: var(--orange); }
.trace-val.purple { color: var(--purple); }

/* Impact analysis cards */
.impact-section { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem; }
.impact-title   { font-family: 'IBM Plex Mono', monospace; font-size: .75rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; margin-bottom: .7rem; padding-bottom: .4rem; border-bottom: 1px solid var(--border); }
.impact-title.overlap { color: var(--orange); }
.impact-title.gap     { color: var(--red); }
.impact-title.new     { color: var(--green); }
.impact-title.rec     { color: var(--purple); }
.impact-item  { font-size: .83rem; color: var(--text); padding: .3rem 0; border-bottom: 1px solid var(--border); }
.impact-item:last-child { border-bottom: none; }
.impact-item span { font-family: 'IBM Plex Mono', monospace; font-size: .72rem; margin-right: 6px; }

.loc-table { width: 100%; border-collapse: collapse; font-size: .8rem; font-family: 'IBM Plex Mono', monospace; }
.loc-table th { background: var(--surface); color: var(--muted); font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; padding: .5rem .7rem; border-bottom: 1px solid var(--border-bright); text-align: left; white-space: nowrap; }
.loc-table td { padding: .55rem .7rem; border-bottom: 1px solid var(--border); vertical-align: top; word-break: break-all; }
.loc-table tr:hover td { background: rgba(77,121,255,.04); }

.badge { display: inline-block; border-radius: 5px; padding: 1px 7px; font-size: .68rem; font-weight: 700; white-space: nowrap; }
.badge-high  { background: rgba(0,255,157,.1);   color: var(--green);  border: 1px solid var(--green); }
.badge-med   { background: rgba(255,209,102,.1); color: var(--yellow); border: 1px solid var(--yellow); }
.badge-low   { background: rgba(90,99,128,.15);  color: var(--muted);  border: 1px solid var(--border-bright); }
.badge-id    { background: rgba(77,121,255,.1);  color: var(--blue);   border: 1px solid var(--blue); }
.badge-name  { background: rgba(0,255,157,.08);  color: var(--green);  border: 1px solid rgba(0,255,157,.3); }
.badge-css   { background: rgba(255,140,66,.08); color: var(--orange); border: 1px solid rgba(255,140,66,.3); }
.badge-xpath { background: rgba(255,77,109,.08); color: var(--red);    border: 1px solid rgba(255,77,109,.3); }

.locator-val { color: var(--green); font-size: .78rem; }
.score-badge { display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: .78rem; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }
.score-high { background: rgba(0,255,157,.1);   color: var(--green);  border: 1px solid var(--green); }
.score-mid  { background: rgba(255,209,102,.1); color: var(--yellow); border: 1px solid var(--yellow); }
.score-low  { background: rgba(255,77,109,.1);  color: var(--red);    border: 1px solid var(--red); }
.iter-badge { font-family: 'IBM Plex Mono', monospace; font-size: .7rem; color: var(--orange); background: rgba(255,140,66,.08); border: 1px solid rgba(255,140,66,.3); border-radius: 4px; padding: 1px 7px; margin-left: 7px; }

.stButton > button { background: linear-gradient(135deg,#00ff9d,#4d79ff) !important; color: #080a0f !important; font-weight: 700 !important; border: none !important; border-radius: 8px !important; font-family: 'Bricolage Grotesque',sans-serif !important; width: 100% !important; }
.stTextInput > div > div > input, .stSelectbox > div > div > div, .stNumberInput > div > div > input { background: var(--card) !important; color: var(--text) !important; border: 1px solid var(--border-bright) !important; border-radius: 8px !important; font-family: 'IBM Plex Mono', monospace !important; }
.stDownloadButton > button { background: var(--card) !important; color: var(--green) !important; border: 1px solid var(--green) !important; border-radius: 8px !important; }
button[kind="secondary"] { background: rgba(255,77,109,.08) !important; color: var(--red) !important; border: 1px solid var(--red) !important; font-weight: 600 !important; }
.stTabs [data-baseweb="tab"] { font-family: 'IBM Plex Mono', monospace !important; font-size: .78rem !important; }
div[data-testid="stExpander"] { background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
.stSlider label, .stCheckbox label, .stSelectbox label { color: var(--muted) !important; font-size: .82rem !important; }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 10px; border: 1px solid var(--border); }

/* Assignment badge */
.assignment-pill {
  display: inline-flex; gap: .5rem; flex-wrap: wrap; justify-content: center;
  margin-bottom: .6rem;
}
.ap { font-family: 'IBM Plex Mono', monospace; font-size: .65rem; padding: 2px 10px; border-radius: 12px; font-weight: 600; }
.ap-ai  { background: rgba(77,121,255,.12); color: var(--blue);   border: 1px solid rgba(77,121,255,.4); }
.ap-mcp { background: rgba(181,123,238,.12); color: var(--purple); border: 1px solid rgba(181,123,238,.4); }
.ap-uc  { background: rgba(0,255,157,.12); color: var(--green);  border: 1px solid rgba(0,255,157,.4); }
.ap-ag  { background: rgba(255,209,102,.12); color: var(--yellow); border: 1px solid rgba(255,209,102,.4); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

def reset_results():
    for key in ["result_memory", "result_final_code", "result_final_score",
                "result_page_data", "result_url", "pipeline_done", "result_impact"]:
        if key in st.session_state:
            del st.session_state[key]


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR CONFIG
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
<div style="font-family:'IBM Plex Mono',monospace;font-size:.68rem;color:#4d79ff;
letter-spacing:.16em;text-transform:uppercase;padding:.5rem 0 .9rem">
⚙ Configuration
</div>""", unsafe_allow_html=True)

    # ── Groq API Key ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">🔑 Groq API Key</div>', unsafe_allow_html=True)
    groq_api_key = None
    key_from_secrets = False
    try:
        secret_key = st.secrets["GROQ_API_KEY"]
        if secret_key and secret_key.startswith("gsk_"):
            groq_api_key = secret_key
            key_from_secrets = True
    except (KeyError, Exception):
        secret_key = None

    if key_from_secrets:
        st.markdown('<div class="api-status api-ok">✅ Loaded from Streamlit Secrets</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="api-status api-manual">⚠ Secret not found — enter manually</div>', unsafe_allow_html=True)
        manual_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", key="manual_api_key")
        if manual_key:
            groq_api_key = manual_key
        st.caption("[Get a free key →](https://console.groq.com)")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── GitHub MCP config ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">🐙 GitHub — Impact Analysis</div>', unsafe_allow_html=True)

    gh_token = None
    try:
        gh_secret = st.secrets["GITHUB_TOKEN"]
        if gh_secret:
            gh_token = gh_secret
            st.markdown('<div class="api-status api-gh">✅ GitHub token from Secrets</div>', unsafe_allow_html=True)
    except (KeyError, Exception):
        manual_gh = st.text_input("GitHub Token (PAT)", type="password", placeholder="ghp_...", key="manual_gh_token")
        if manual_gh:
            gh_token = manual_gh
        st.caption("Needs `repo` read scope. [Create →](https://github.com/settings/tokens)")

    gh_repo = st.text_input(
        "Repository (owner/repo)",
        placeholder="myorg/qa-tests",
        key="gh_repo"
    )
    gh_path = st.text_input(
        "Test folder path",
        value="src/test",
        placeholder="src/test/java",
        key="gh_path"
    )
    gh_enabled = bool(gh_token and gh_repo)
    if gh_enabled:
        st.markdown('<div class="api-status api-gh">🔗 GitHub Impact Analysis: ON</div>', unsafe_allow_html=True)
    else:
        st.caption("⚠ Skip GitHub fields to run without impact analysis.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Model ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">🧠 Model</div>', unsafe_allow_html=True)
    model = st.selectbox("LLM Model", ["llama-3.3-70b-versatile", "llama3-8b-8192", "gemma2-9b-it"], index=0, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Generation Options ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">🛠 Generation Options</div>', unsafe_allow_html=True)
    include_waits  = st.checkbox("WebDriverWait", value=True)
    include_testng = st.checkbox("Use TestNG",    value=True)
    max_elements   = st.slider("Max elements", 10, 40, 20)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Pipeline Tuning ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">⚡ Pipeline Tuning</div>', unsafe_allow_html=True)
    delay_secs      = st.slider("Agent delay (s)",     2, 10, 4)
    max_iterations  = st.slider("Max loop iterations", 1,  5, 3)
    score_threshold = st.slider("Quality threshold",   5,  9, 7)
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Clear Results", use_container_width=True, type="secondary"):
        reset_results()
        st.rerun()
    st.caption("QA Agent v3.2 · Groq + GitHub MCP · Streamlit")


# ══════════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="hero">
  <div class="assignment-pill">
    <span class="ap ap-ai">✅ AI Tool: Groq Llama 3.3</span>
    <span class="ap ap-mcp">✅ MCP: GitHub</span>
    <span class="ap ap-uc">✅ Use Case: Impact Analysis</span>
    <span class="ap ap-ag">✅ Agentic Pipeline</span>
  </div>
  <div class="hero-label">Scrape · Locate · Generate · Review · GitHub Impact</div>
  <h1>Multi-Agent QA System</h1>
  <p>Java Selenium TestNG · Groq Free Tier · GitHub MCP Integration</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════════════════

def tool_scrape_page(url: str, limit: int) -> dict:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (QA-AgentBot/3.2)"}, timeout=15, verify=False)
        r.raise_for_status()
        soup  = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "Unknown"
        h1s   = [h.get_text(strip=True) for h in soup.find_all("h1", limit=3)]
        forms = [str(f)[:200] for f in soup.find_all("form", limit=3)]
        elements = []
        for tag in soup.find_all(["input","button","a","select","textarea","label"], limit=limit*2):
            attrs = {k: (v if isinstance(v, str) else " ".join(v))
                     for k, v in tag.attrs.items()
                     if k in ("id","name","type","class","href","placeholder","aria-label","value","action")}
            elements.append({"tag": tag.name, "text": tag.get_text(strip=True)[:60], "attrs": attrs})
            if len(elements) >= limit:
                break
        return {"status":"success","title":title,"h1s":h1s,"url":url,"forms":forms,"elements":elements}
    except Exception as e:
        return {"status":"error","error":str(e),"url":url,"elements":[]}


def tool_validate_java_syntax(code: str) -> dict:
    issues = []
    if "Thread.sleep" in code:
        issues.append("Thread.sleep() found — should use WebDriverWait")
    if "import org.testng" not in code and "import org.junit" not in code:
        issues.append("Missing test framework import (TestNG or JUnit)")
    if "@Test" not in code:
        issues.append("No @Test annotation found")
    if "driver.quit" not in code and "driver.close" not in code:
        issues.append("No driver teardown (driver.quit/close)")
    if code.count("{") != code.count("}"):
        issues.append(f"Bracket mismatch: {{ {code.count('{')} vs }} {code.count('}')}")
    if "package com.qa" not in code:
        issues.append("Missing package declaration")
    return {"issues": issues, "issue_count": len(issues), "valid": len(issues) == 0}


def tool_score_code(code: str, issues: list) -> dict:
    score = 10
    score -= len(issues) * 1.5
    if len(code) < 500: score -= 2
    if "WebDriverWait" in code: score += 0.5
    if "PageFactory" in code or "FindBy" in code: score += 0.5
    return {"score": max(0, min(10, round(score, 1))), "max": 10}


# ══════════════════════════════════════════════════════════════════════════════
# GITHUB MCP TOOL  (REST API used as MCP proxy)
# ══════════════════════════════════════════════════════════════════════════════

def tool_github_fetch_tests(token: str, repo: str, path: str) -> dict:
    """
    Fetches Java test files from a GitHub repository folder.
    Uses GitHub Contents API — acts as the MCP server integration point.
    Returns list of {name, path, content_snippet} for existing test files.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        r = requests.get(base_url, headers=headers, timeout=15)
        if r.status_code == 404:
            return {"status": "not_found", "files": [], "message": f"Path '{path}' not found in {repo}"}
        if r.status_code == 401:
            return {"status": "auth_error", "files": [], "message": "GitHub token invalid or missing repo scope"}
        r.raise_for_status()
        items = r.json()

        java_files = []
        # Recurse into subdirectories (one level)
        for item in items if isinstance(items, list) else []:
            if item["type"] == "file" and item["name"].endswith(".java"):
                # Fetch file content
                fc = requests.get(item["url"], headers=headers, timeout=10)
                if fc.status_code == 200:
                    raw = fc.json()
                    content = ""
                    if raw.get("encoding") == "base64":
                        content = base64.b64decode(raw["content"]).decode("utf-8", errors="replace")
                    java_files.append({
                        "name": item["name"],
                        "path": item["path"],
                        "size": item["size"],
                        "content": content[:3000],  # first 3000 chars
                        "url":  item["html_url"],
                    })
            elif item["type"] == "dir":
                # One level deep search
                dr = requests.get(item["url"], headers=headers, timeout=10)
                if dr.status_code == 200:
                    for sub in dr.json() if isinstance(dr.json(), list) else []:
                        if sub["type"] == "file" and sub["name"].endswith(".java"):
                            fc2 = requests.get(sub["url"], headers=headers, timeout=10)
                            if fc2.status_code == 200:
                                raw2 = fc2.json()
                                content2 = ""
                                if raw2.get("encoding") == "base64":
                                    content2 = base64.b64decode(raw2["content"]).decode("utf-8", errors="replace")
                                java_files.append({
                                    "name": sub["name"],
                                    "path": sub["path"],
                                    "size": sub["size"],
                                    "content": content2[:3000],
                                    "url":  sub["html_url"],
                                })

        return {
            "status": "success",
            "repo": repo,
            "path": path,
            "files": java_files,
            "count": len(java_files),
        }
    except Exception as e:
        return {"status": "error", "files": [], "message": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT MEMORY
# ══════════════════════════════════════════════════════════════════════════════

def init_memory(url: str) -> dict:
    return {
        "url": url,
        "page_data": None,
        "element_analysis": None,
        "locator_rows": [],
        "raw_code": None,
        "final_code": None,
        "iterations": 0,
        "scores": [],
        "issues_history": [],
        "agent_logs": [],
        "orchestrator_plan": None,
        "github_data": None,
        "impact_report": None,
    }


def log_trace(memory: dict, agent: str, thought: str, action: str, observation: str):
    memory["agent_logs"].append({
        "agent": agent,
        "thought": thought,
        "action": action,
        "observation": observation,
        "iteration": memory["iterations"],
        "ts": time.time(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# LOCATOR TABLE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _best_locator(tag: str, attrs: dict, text: str) -> tuple:
    el_id    = attrs.get("id", "").strip()
    el_name  = attrs.get("name", "").strip()
    el_type  = attrs.get("type", "").strip()
    el_class = attrs.get("class", "").strip()
    el_href  = attrs.get("href", "").strip()
    el_ph    = attrs.get("placeholder", "").strip()
    el_aria  = attrs.get("aria-label", "").strip()
    txt      = text.strip()

    if el_id:
        return f'By.id("{el_id}")', "ID"
    if el_name and tag in ("input", "select", "textarea"):
        return f'By.name("{el_name}")', "NAME"
    if txt and len(txt) <= 40 and tag in ("button", "a", "label") and not any(c in txt for c in ['"', "'"]):
        return f'By.xpath("//{tag}[normalize-space()=\'{txt}\']")', "XPATH"
    if el_aria:
        return f'By.xpath("//*[@aria-label=\'{el_aria}\']")', "XPATH"
    if el_type and tag == "input" and el_type not in ("text", "hidden"):
        return f'By.cssSelector("input[type=\'{el_type}\']")', "CSS"
    if el_ph:
        safe_ph = el_ph.replace("'", "\\'")
        return f"By.cssSelector(\"[placeholder='{safe_ph}']\")", "CSS"
    if tag == "a" and txt and len(txt) <= 30 and txt.isascii():
        return f'By.linkText("{txt}")', "LINK"
    if el_class:
        classes = el_class.split()
        if len(classes) == 1:
            return f'By.className("{classes[0]}")', "CLASS"
        return f'By.cssSelector("{tag}.{classes[0]}")', "CSS"
    if el_href and el_href not in ("#", "/", "javascript:void(0)"):
        safe = el_href[:50].replace("'", "\\'")
        return f"By.cssSelector(\"a[href='{safe}']\")", "CSS"
    return f'By.xpath("//{tag}")', "XPATH"


def parse_locator_rows(agent1_text: str, page_elements: list) -> list:
    rows = []
    seen = set()
    line_re = re.compile(
        r'\[?\d+\]?\s*Tag:\s*(?P<tag>\S+)\s*\|'
        r'\s*Purpose:\s*(?P<purpose>[^|]+)\|'
        r'\s*Locator:\s*(?P<locator>By\.\w+\([^)]+\))\s*\|'
        r'\s*Priority:\s*(?P<priority>HIGH|MED|LOW)',
        re.IGNORECASE,
    )
    for m in line_re.finditer(agent1_text):
        loc = m.group("locator").strip()
        if loc in seen:
            continue
        seen.add(loc)
        loc_type = "XPATH"
        if "By.id("           in loc: loc_type = "ID"
        elif "By.name("       in loc: loc_type = "NAME"
        elif "By.cssSelector(" in loc: loc_type = "CSS"
        elif "By.className("  in loc: loc_type = "CLASS"
        elif "By.linkText("   in loc: loc_type = "LINK"
        rows.append({
            "tag": m.group("tag").strip().replace("<","").replace(">",""),
            "purpose": m.group("purpose").strip(),
            "locator": loc,
            "loc_type": loc_type,
            "priority": m.group("priority").strip().upper(),
        })

    if len(rows) < 3 and page_elements:
        for el in page_elements:
            attrs = el.get("attrs", {})
            tag   = el.get("tag", "?")
            text  = el.get("text", "")
            loc, loc_type = _best_locator(tag, attrs, text)
            if loc in seen:
                continue
            seen.add(loc)
            combined = (text + " " + attrs.get("placeholder","") + " " + attrs.get("aria-label","")).lower()
            el_type  = attrs.get("type","")
            if "password" in combined or el_type == "password":
                purpose, priority = "Password field", "HIGH"
            elif "email" in combined or el_type == "email":
                purpose, priority = "Email input", "HIGH"
            elif "login" in combined or "sign in" in combined:
                purpose, priority = "Login action", "HIGH"
            elif "search" in combined or el_type == "search":
                purpose, priority = "Search field", "HIGH"
            elif "submit" in combined or el_type == "submit":
                purpose, priority = "Form submit", "HIGH"
            elif tag == "select":
                purpose, priority = "Dropdown selector", "MED"
            elif tag == "textarea":
                purpose, priority = "Text area input", "MED"
            elif tag == "button":
                purpose, priority = f"Button: {text[:35] or 'unnamed'}", "MED"
            elif tag == "a":
                label = text[:30] or attrs.get("href","")[:25]
                purpose, priority = f"Link: {label}", "MED"
            elif tag == "label":
                purpose, priority = f"Label: {text[:35]}", "LOW"
            else:
                purpose, priority = f"<{tag}> element", "LOW"
            rows.append({"tag":tag,"purpose":purpose,"locator":loc,"loc_type":loc_type,"priority":priority})

    return rows


# ══════════════════════════════════════════════════════════════════════════════
# LLM WRAPPER
# ══════════════════════════════════════════════════════════════════════════════

def call_llm(client: Groq, model_name: str, system: str, user: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=0.2,
                max_tokens=4096,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err and attempt < retries - 1:
                wait = 20 * (attempt + 1)
                st.warning(f"⏳ Rate limit — waiting {wait}s (retry {attempt+2}/{retries})…")
                time.sleep(wait)
            else:
                raise
    return "LLM call failed."


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def orchestrator_plan(client, model_name, memory: dict) -> str:
    system = """You are an AI Orchestrator managing a multi-agent QA pipeline.
Output ONLY valid JSON: {"plan":["agent_1","agent_2","agent_3","agent_4_github"],"priority":"correctness|speed|coverage","notes":"brief instruction"}"""
    page_summary = (
        f"URL: {memory['url']}, Elements: {len(memory['page_data'].get('elements',[]))}"
        if memory['page_data'] and memory['page_data'].get('status') == 'success'
        else f"URL: {memory['url']}, scrape failed"
    )
    user = f"""State: {page_summary}
Iterations: {memory['iterations']}
Last score: {memory['scores'][-1] if memory['scores'] else 'none'}
Issues: {memory['issues_history'][-1] if memory['issues_history'] else 'none'}
GitHub integration: enabled
Determine execution plan including GitHub impact analysis."""
    raw = call_llm(client, model_name, system, user)
    try:
        return json.loads(raw.replace("```json","").replace("```","").strip()).get("notes","Standard pipeline with GitHub impact.")
    except Exception:
        return "Standard pipeline with GitHub impact analysis."


def orchestrator_should_loop(client, model_name, memory: dict, score: float, threshold: float) -> bool:
    if score >= threshold or memory["iterations"] >= 3:
        return False
    system = 'Answer ONLY with JSON: {"loop":true} or {"loop":false}.'
    user = f"Score {score}/{threshold}. Issues: {memory['issues_history'][-1]}. Iterations: {memory['iterations']}. Loop?"
    raw = call_llm(client, model_name, system, user)
    try:
        return json.loads(raw.replace("```json","").replace("```","").strip()).get("loop", False)
    except Exception:
        return score < threshold


# ══════════════════════════════════════════════════════════════════════════════
# AGENTS 1–3  (unchanged from v3.1)
# ══════════════════════════════════════════════════════════════════════════════

def agent_element_finder(client, model_name, memory: dict, max_el: int) -> str:
    thought = f"Identify testable elements on {memory['url']} using scraped data."
    page = memory["page_data"]
    if page["status"] == "error":
        ctx = f"Scrape failed: {page.get('error')}. URL: {memory['url']}"
    else:
        rows = [f"  <{el['tag']}> text='{el['text']}' attrs={el['attrs']}" for el in page["elements"]]
        ctx = (f"Title: {page['title']}\nH1s: {', '.join(page['h1s'])}\n"
               f"URL: {page['url']}\nForms: {len(page['forms'])}\n\nElements ({len(rows)}):\n" + "\n".join(rows))

    system = """You are a Senior QA Automation Engineer. Analyse this page and output elements in EXACTLY this format per line:
[N] Tag: <tag> | Purpose: <what it does> | Locator: By.<TYPE>("<value>") | Priority: HIGH/MED/LOW

LOCATOR SELECTION RULES:
1. By.id("...")                                — element has unique id
2. By.name("...")                              — input/select with name attr (no id)
3. By.xpath("//tag[normalize-space()='Text']") — button/a with clear visible text
4. By.xpath("//*[@aria-label='...']")          — aria-label present, no id/name
5. By.cssSelector("input[type='email']")       — typed inputs without id/name
6. By.cssSelector("[placeholder='...']")       — inputs identified by placeholder
7. By.linkText("...")                          — <a> with short clean visible text
8. By.cssSelector("tag.classname")             — unique single class
9. By.xpath("//tag[@attr='value']")            — fallback

MANDATORY DIVERSITY: use a MIX — ~30% ID/NAME, ~30% XPath, ~20% CSS, ~20% LinkText/Class.
No preamble. Output lines only."""

    user = f"""Analyse and list up to {max_el} interactive elements with MIXED Selenium locator strategies.

PAGE SNAPSHOT:
{ctx}

REMINDER: Use variety — By.id, By.xpath, By.linkText, By.cssSelector, By.name.
Output each element on its own line in the exact format above."""

    result = call_llm(client, model_name, system, user)
    log_trace(memory, "Element Finder", thought, "call_llm(element_analysis)", f"Got {result.count('[')} element entries.")
    return result


def agent_test_architect(client, model_name, memory: dict, wait_instr: bool, testng_instr: bool) -> str:
    iteration   = memory["iterations"]
    prev_issues = memory["issues_history"][-1] if memory["issues_history"] else []
    prev_code   = memory["raw_code"]

    thought = ("First pass — generating full Java POM test suite."
               if iteration == 0 else f"Iteration {iteration+1} — fixing: {prev_issues}")

    waits_note  = ("Use WebDriverWait(driver, Duration.ofSeconds(10)) + ExpectedConditions. NEVER Thread.sleep()."
                   if wait_instr else "Implicit waits acceptable.")
    testng_note = ("Use TestNG: import org.testng.annotations.*; import org.testng.Assert;"
                   if testng_instr else "Use JUnit 5: import org.junit.jupiter.api.*; import static org.junit.jupiter.api.Assertions.*;")

    fix_section = ""
    if prev_issues:
        fix_section = "\nCRITICAL — FIX THESE ISSUES:\n" + "\n".join(f"  - {i}" for i in prev_issues)
    if prev_code and iteration > 0:
        fix_section += f"\n\nPREVIOUS CODE (rejected):\n{prev_code[:1500]}\n...fix it."

    system = f"""You are a Selenium Test Architect — Java, POM, TestNG expert.
Rules:
- package com.qa.tests;
- Page class: private By fields + public action methods
- Test class: @BeforeMethod ChromeDriver setup, @AfterMethod quit
- Minimum 3 @Test methods: happy path, negative, edge case
- {waits_note}
- {testng_note}
- Real code only — NO placeholder comments
- Output TWO complete code blocks: Page class then Test class"""

    user = f"""Generate complete Java Selenium code for: {memory['url']}
{fix_section}

ELEMENT ANALYSIS (use these locators):
{memory['element_analysis']}

Include all imports. POM pattern. {waits_note}"""

    result = call_llm(client, model_name, system, user)
    log_trace(memory, "Test Architect", thought, f"call_llm(generate_code, iter={iteration+1})", f"Generated {len(result)} chars.")
    return result


def agent_qa_reviewer(client, model_name, memory: dict) -> tuple:
    code    = memory["raw_code"]
    thought = "Validate with tools, score, then fix any issues."

    validation   = tool_validate_java_syntax(code)
    issues       = validation["issues"]
    score_result = tool_score_code(code, issues)
    score        = score_result["score"]

    log_trace(memory, "QA Reviewer", thought, "tool_validate_java_syntax() + tool_score_code()", f"Issues: {len(issues)}. Score: {score}/10.")

    system = """You are a strict QA Lead Reviewer. Fix ALL issues in this Java Selenium code.
Output ONLY the corrected Java code. No explanation. No markdown fences."""

    issue_list = "\n".join(f"  - {i}" for i in issues) if issues else "  - No critical issues. Improve robustness."
    user = f"""Fix this Java Selenium TestNG code for {memory['url']}.
ISSUES:
{issue_list}
CODE:
{code}
Output final production-ready code:"""

    fixed_code  = call_llm(client, model_name, system, user)
    re_val      = tool_validate_java_syntax(fixed_code)
    re_score    = tool_score_code(fixed_code, re_val["issues"])
    final_score = re_score["score"]

    log_trace(memory, "QA Reviewer", "Re-validating fixed code.",
              "tool_validate_java_syntax(fixed) + tool_score_code(fixed)",
              f"Final score: {final_score}/10. Remaining issues: {re_val['issues']}")

    memory["issues_history"].append(re_val["issues"])
    memory["scores"].append(final_score)
    return fixed_code, final_score, re_val["issues"]


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — GitHub Impact Analyst (NEW in v3.2)
# ══════════════════════════════════════════════════════════════════════════════

def agent_github_impact(client, model_name, memory: dict, gh_token: str, gh_repo: str, gh_path: str) -> dict:
    """
    Fetches existing test files via GitHub API (MCP integration),
    then uses LLM to compare against newly generated code and produce an impact report.
    """
    thought = f"Fetching existing tests from GitHub {gh_repo}/{gh_path} for impact analysis."

    # Step 1: Fetch existing tests from GitHub
    gh_result = tool_github_fetch_tests(gh_token, gh_repo, gh_path)
    memory["github_data"] = gh_result

    if gh_result["status"] != "success" or not gh_result["files"]:
        status_msg = gh_result.get("message", "No Java test files found in the specified path.")
        log_trace(memory, "GitHub Impact Agent", thought,
                  f"tool_github_fetch_tests({gh_repo}, {gh_path})",
                  f"Status: {gh_result['status']} — {status_msg}")
        return {
            "status": gh_result["status"],
            "message": status_msg,
            "files_scanned": 0,
            "overlaps": [],
            "gaps": [],
            "new_coverage": [],
            "recommendation": "Could not fetch GitHub data. Skipping impact analysis.",
            "raw_analysis": "",
        }

    files_summary = "\n\n".join(
        f"=== FILE: {f['path']} ===\n{f['content'][:1500]}"
        for f in gh_result["files"]
    )

    log_trace(memory, "GitHub Impact Agent", thought,
              f"tool_github_fetch_tests({gh_repo}, {gh_path})",
              f"Fetched {gh_result['count']} Java files from GitHub.")

    # Step 2: LLM impact analysis
    thought2 = "Comparing new generated code against existing repo tests — finding overlaps, gaps, new coverage."

    system = """You are a QA Impact Analyst. Compare newly generated Selenium tests against existing tests in a GitHub repository.

Respond ONLY in this exact JSON format (no markdown, no extra text):
{
  "overlaps": ["list of duplicate/overlapping test scenarios (string each)"],
  "gaps": ["list of test scenarios in the existing repo NOT covered by new code"],
  "new_coverage": ["list of new scenarios in generated code not in existing repo"],
  "recommendation": "one of: MERGE | REPLACE | EXTEND | NO_CHANGE",
  "recommendation_reason": "one paragraph explanation",
  "risk_level": "LOW | MEDIUM | HIGH",
  "risk_reason": "brief explanation"
}"""

    user = f"""Target URL: {memory['url']}

=== NEWLY GENERATED TEST CODE ===
{memory['final_code'][:2500]}

=== EXISTING TESTS IN GITHUB REPO ({gh_repo}) ===
{files_summary[:3000]}

Analyse and return JSON impact report:"""

    raw = call_llm(client, model_name, system, user)
    log_trace(memory, "GitHub Impact Agent", thought2,
              "call_llm(impact_analysis)",
              f"LLM returned {len(raw)} chars. Parsing impact report.")

    try:
        parsed = json.loads(raw.replace("```json","").replace("```","").strip())
    except Exception:
        # Graceful fallback
        parsed = {
            "overlaps": [],
            "gaps": [],
            "new_coverage": ["Analysis parsing failed — see raw output below"],
            "recommendation": "EXTEND",
            "recommendation_reason": "Could not parse LLM response. Recommend manual review.",
            "risk_level": "MEDIUM",
            "risk_reason": "Parse failure — manual review needed.",
        }

    return {
        "status": "success",
        "files_scanned": gh_result["count"],
        "repo": gh_repo,
        "path": gh_path,
        "files": [{"name": f["name"], "path": f["path"], "url": f["url"]} for f in gh_result["files"]],
        "overlaps":            parsed.get("overlaps", []),
        "gaps":                parsed.get("gaps", []),
        "new_coverage":        parsed.get("new_coverage", []),
        "recommendation":      parsed.get("recommendation", "EXTEND"),
        "recommendation_reason": parsed.get("recommendation_reason", ""),
        "risk_level":          parsed.get("risk_level", "MEDIUM"),
        "risk_reason":         parsed.get("risk_reason", ""),
        "raw_analysis":        raw,
    }


# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def render_trace(log: dict):
    color_map = {"Orchestrator":"yellow","Element Finder":"blue","Test Architect":"green","QA Reviewer":"orange","GitHub Impact Agent":"purple"}
    color      = color_map.get(log["agent"], "blue")
    card_class = "github" if log["agent"] == "GitHub Impact Agent" else ""
    iter_badge = f'<span class="iter-badge">iter {log["iteration"]+1}</span>' if log["iteration"] > 0 else ""
    st.markdown(f"""
<div class="react-card {card_class}">
  <div class="agent-name {color}">⬡ {log['agent']}{iter_badge}</div>
  <div class="trace-row"><span class="trace-label">THOUGHT</span><span class="trace-val">{log['thought']}</span></div>
  <div class="trace-row"><span class="trace-label">ACTION</span><span class="trace-val green">{log['action']}</span></div>
  <div class="trace-row"><span class="trace-label">OBSERVATION</span><span class="trace-val">{log['observation']}</span></div>
</div>""", unsafe_allow_html=True)


def score_badge_html(score: float) -> str:
    cls = "score-high" if score >= 7 else ("score-mid" if score >= 5 else "score-low")
    return f'<span class="score-badge {cls}">{score}/10</span>'


def priority_badge(p: str) -> str:
    cls = {"HIGH":"badge-high","MED":"badge-med","LOW":"badge-low"}.get(p,"badge-low")
    return f'<span class="badge {cls}">{p}</span>'


def loctype_badge(t: str) -> str:
    cls = {"ID":"badge-id","NAME":"badge-name","CSS":"badge-css","CLASS":"badge-css","LINK":"badge-css"}.get(t,"badge-xpath")
    return f'<span class="badge {cls}">{t}</span>'


def render_locator_table(rows: list):
    if not rows:
        st.warning("No locators extracted. The page may block scraping.")
        return
    high = sum(1 for r in rows if r["priority"]=="HIGH")
    ids  = sum(1 for r in rows if r["loc_type"]=="ID")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Elements",      len(rows))
    c2.metric("HIGH Priority", high)
    c3.metric("ID Locators",   ids)
    c4.metric("CSS/XPath",     len(rows)-ids)
    header = '<div class="table-scroll"><table class="loc-table"><thead><tr><th>#</th><th>Tag</th><th>Purpose</th><th>Type</th><th>Locator</th><th>Priority</th></tr></thead><tbody>'
    body_rows = []
    for i,r in enumerate(rows,1):
        body_rows.append(f'<tr><td style="color:var(--muted)">{i}</td><td style="color:var(--muted)">&lt;{r["tag"]}&gt;</td><td style="color:var(--text)">{r["purpose"]}</td><td>{loctype_badge(r["loc_type"])}</td><td class="locator-val">{r["locator"]}</td><td>{priority_badge(r["priority"])}</td></tr>')
    st.markdown(header+"".join(body_rows)+"</tbody></table></div>", unsafe_allow_html=True)
    csv_lines = ["#,Tag,Purpose,Locator Type,Locator,Priority"]
    for i,r in enumerate(rows,1):
        csv_lines.append(f'{i},{r["tag"]},"{r["purpose"]}",{r["loc_type"]},"{r["locator"]}",{r["priority"]}')
    st.download_button("⬇️ Download Locators CSV", data="\n".join(csv_lines), file_name="locators.csv", mime="text/csv", use_container_width=True)


def render_impact_report(impact: dict):
    """Renders the GitHub impact analysis tab."""
    if not impact or impact.get("status") != "success":
        msg = impact.get("message","GitHub impact analysis was not run or failed.") if impact else "GitHub integration not configured."
        st.info(f"ℹ️ {msg}")
        st.caption("To enable: add GitHub Token + repo in the sidebar.")
        return

    # Header metrics
    rec   = impact.get("recommendation","EXTEND")
    risk  = impact.get("risk_level","MEDIUM")
    risk_colors = {"LOW":"var(--green)","MEDIUM":"var(--yellow)","HIGH":"var(--red)"}
    rec_colors  = {"MERGE":"var(--blue)","REPLACE":"var(--red)","EXTEND":"var(--green)","NO_CHANGE":"var(--muted)"}

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Files Scanned",  impact.get("files_scanned",0))
    c2.metric("Overlaps Found", len(impact.get("overlaps",[])))
    c3.metric("Coverage Gaps",  len(impact.get("gaps",[])))
    c4.metric("New Scenarios",  len(impact.get("new_coverage",[])))

    st.markdown(f"""
<div style="display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0">
  <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.8rem 1.2rem;flex:1;min-width:160px">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:.68rem;color:var(--muted);margin-bottom:.3rem">RECOMMENDATION</div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:1.1rem;font-weight:700;color:{rec_colors.get(rec,'var(--text)')}">
      {rec}
    </div>
    <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem">{impact.get('recommendation_reason','')[:120]}…</div>
  </div>
  <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.8rem 1.2rem;flex:1;min-width:160px">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:.68rem;color:var(--muted);margin-bottom:.3rem">RISK LEVEL</div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:1.1rem;font-weight:700;color:{risk_colors.get(risk,'var(--text)')}">
      {risk}
    </div>
    <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem">{impact.get('risk_reason','')[:120]}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    def impact_section(title, items, css_class, icon, empty_msg):
        items_html = "".join(f'<div class="impact-item"><span>{icon}</span>{item}</div>' for item in items) if items else f'<div class="impact-item" style="color:var(--muted)">{empty_msg}</div>'
        st.markdown(f'<div class="impact-section"><div class="impact-title {css_class}">{title} ({len(items)})</div>{items_html}</div>', unsafe_allow_html=True)

    impact_section("⚠ Overlapping Coverage",  impact.get("overlaps",[]),      "overlap", "⚠", "No overlapping test scenarios found")
    impact_section("🔴 Coverage Gaps in Repo", impact.get("gaps",[]),          "gap",     "❌", "No gaps — new code covers all repo scenarios")
    impact_section("✅ New Coverage Added",     impact.get("new_coverage",[]), "new",     "✅", "No new unique coverage detected")

    # Files scanned list
    if impact.get("files"):
        with st.expander(f"📁 Scanned GitHub Files ({len(impact['files'])})", expanded=False):
            for f in impact["files"]:
                url = f.get("url","")
                st.markdown(f'🔗 [`{f["name"]}`]({url}) — `{f["path"]}`' if url else f'📄 `{f["path"]}`')

    with st.expander("📄 Raw LLM Impact Analysis", expanded=False):
        st.text_area("", value=impact.get("raw_analysis",""), height=200, label_visibility="collapsed")

    # Download report
    report_lines = [
        f"GitHub Impact Analysis Report",
        f"Repository: {impact.get('repo','')}",
        f"Path: {impact.get('path','')}",
        f"Files Scanned: {impact.get('files_scanned',0)}",
        f"Recommendation: {rec}",
        f"Risk Level: {risk}",
        "",
        "OVERLAPPING COVERAGE:",
        *[f"  - {o}" for o in impact.get("overlaps",[])],
        "",
        "COVERAGE GAPS:",
        *[f"  - {g}" for g in impact.get("gaps",[])],
        "",
        "NEW COVERAGE ADDED:",
        *[f"  + {n}" for n in impact.get("new_coverage",[])],
        "",
        f"Recommendation Reason: {impact.get('recommendation_reason','')}",
        f"Risk Reason: {impact.get('risk_reason','')}",
    ]
    st.download_button(
        "⬇️ Download Impact Report",
        data="\n".join(report_lines),
        file_name="github_impact_report.txt",
        mime="text/plain",
        use_container_width=True,
    )


def is_valid_url(url: str) -> bool:
    return bool(re.match(r'^https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:\d+)?(/[^\s]*)?$', url.strip()))


# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════════════════

url_input = st.text_input("🌐 Target Website URL", placeholder="https://example.com/login")
run_btn   = st.button("🚀 Run QA Agent Pipeline", use_container_width=True, type="primary")

if run_btn:
    if not groq_api_key or not groq_api_key.startswith("gsk_"):
        st.error("❌ Groq API key missing. Add GROQ_API_KEY to Streamlit Secrets or enter in the sidebar.")
        st.stop()
    if not url_input or not is_valid_url(url_input):
        st.error("❌ Enter a valid URL (https:// or http://)")
        st.stop()

    reset_results()
    client = Groq(api_key=groq_api_key)
    memory = init_memory(url_input)

    with st.expander("🤖 Agent Execution Log", expanded=False):
        trace_container = st.container()

    # STEP 0: Scrape
    with st.spinner("🌐 Scraping page…"):
        page_data = tool_scrape_page(url_input, max_elements)
        memory["page_data"] = page_data
    log_trace(memory, "Orchestrator", f"Pipeline started for {url_input}. Running scraper.",
              "tool_scrape_page(url)", f"Scraped {len(page_data.get('elements',[]))} elements. Status: {page_data['status']}")
    with trace_container: render_trace(memory["agent_logs"][-1])
    time.sleep(delay_secs)

    # Orchestrator Plan
    with st.spinner("🧠 Orchestrator planning…"):
        orch_notes = orchestrator_plan(client, model, memory)
        memory["orchestrator_plan"] = orch_notes
        log_trace(memory, "Orchestrator", "Analysing memory state for execution plan.",
                  "orchestrator_plan(memory)", f"Plan: {orch_notes}")
    with trace_container: render_trace(memory["agent_logs"][-1])
    time.sleep(delay_secs)

    # Agent 1: Element Finder
    with st.spinner("🔍 Agent 1: Finding elements & locators…"):
        try:
            a1_out = agent_element_finder(client, model, memory, max_elements)
            memory["element_analysis"] = a1_out
            memory["locator_rows"]     = parse_locator_rows(a1_out, page_data.get("elements",[]))
        except Exception as e:
            st.error(f"Agent 1 failed: {e}"); st.stop()
    with trace_container: render_trace(memory["agent_logs"][-1])
    time.sleep(delay_secs)

    # Agents 2–3: Feedback Loop
    final_code  = ""
    final_score = 0.0
    for iteration in range(max_iterations):
        memory["iterations"] = iteration

        with st.spinner(f"☕ Agent 2: Writing Java code (iter {iteration+1})…"):
            try:
                a2_out = agent_test_architect(client, model, memory, include_waits, include_testng)
                memory["raw_code"] = a2_out
            except Exception as e:
                st.error(f"Agent 2 failed: {e}"); st.stop()
        with trace_container: render_trace(memory["agent_logs"][-1])
        time.sleep(delay_secs)

        with st.spinner(f"🔎 Agent 3: Reviewing & scoring (iter {iteration+1})…"):
            try:
                fixed_code, score, issues = agent_qa_reviewer(client, model, memory)
                memory["final_code"] = fixed_code
                final_code  = fixed_code
                final_score = score
            except Exception as e:
                st.error(f"Agent 3 failed: {e}"); st.stop()
        with trace_container:
            render_trace(memory["agent_logs"][-1])
            score_html  = score_badge_html(score)
            issues_html = "<br>".join(f"• {i}" for i in issues) if issues else "✅ No issues"
            st.markdown(f'<div class="react-card {\"done\" if score >= score_threshold else \"loop\"}"><div class="agent-name orange">🔎 QA Reviewer — {score_html}</div><div class="trace-val" style="margin-top:.35rem">{issues_html}</div></div>', unsafe_allow_html=True)

        if score >= score_threshold:
            log_trace(memory, "Orchestrator", f"Score {score} ≥ {score_threshold}. Accepted.",
                      "orchestrator_should_loop() → False", "Pipeline complete.")
            with trace_container:
                render_trace(memory["agent_logs"][-1])
                st.markdown(f'<div class="react-card done"><div class="agent-name yellow">✅ Orchestrator — Code Accepted</div><div class="trace-val green" style="margin-top:.35rem">Score {score}/10 accepted after {iteration+1} iteration(s). Proceeding to GitHub analysis.</div></div>', unsafe_allow_html=True)
            break
        else:
            should_loop = orchestrator_should_loop(client, model, memory, score, score_threshold)
            if should_loop and iteration < max_iterations - 1:
                log_trace(memory, "Orchestrator", f"Score {score} < {score_threshold}. Looping.",
                          f"orchestrator_should_loop() → True (iter {iteration+2})", f"Issues → Agent 2: {issues}")
                with trace_container:
                    render_trace(memory["agent_logs"][-1])
                    st.markdown(f'<div class="react-card loop"><div class="agent-name yellow">♻️ Feedback Loop — Iteration {iteration+2}</div><div class="trace-val orange" style="margin-top:.35rem">Score {score}/10 below {score_threshold}. Re-running Agent 2 → Agent 3.</div></div>', unsafe_allow_html=True)
                time.sleep(delay_secs)
            else:
                log_trace(memory, "Orchestrator", f"Max iterations reached. Accepting {score}.",
                          "orchestrator_should_loop() → False (cap)", "Exiting with best code.")
                with trace_container: render_trace(memory["agent_logs"][-1])
                break

    # Agent 4: GitHub Impact Analysis
    impact_report = None
    if gh_enabled:
        with st.spinner("🐙 Agent 4: GitHub Impact Analysis…"):
            try:
                impact_report = agent_github_impact(client, model, memory, gh_token, gh_repo, gh_path)
                memory["impact_report"] = impact_report
            except Exception as e:
                impact_report = {"status":"error","message":str(e),"files_scanned":0}
        with trace_container:
            for log in [l for l in memory["agent_logs"] if l["agent"] == "GitHub Impact Agent"]:
                render_trace(log)
            if impact_report and impact_report.get("status") == "success":
                rec   = impact_report.get("recommendation","EXTEND")
                risk  = impact_report.get("risk_level","MEDIUM")
                st.markdown(f'<div class="react-card github"><div class="agent-name purple">🐙 GitHub Impact Agent — Done</div><div class="trace-val purple" style="margin-top:.35rem">Scanned {impact_report["files_scanned"]} files · Recommendation: {rec} · Risk: {risk}</div></div>', unsafe_allow_html=True)
    else:
        with trace_container:
            st.markdown('<div class="react-card" style="border-left-color:var(--muted)"><div class="agent-name" style="color:var(--muted)">🐙 GitHub Impact Agent — Skipped</div><div class="trace-val" style="margin-top:.35rem;color:var(--muted)">GitHub token/repo not configured. Add in sidebar to enable.</div></div>', unsafe_allow_html=True)

    # Save to session state
    st.session_state["result_memory"]      = memory
    st.session_state["result_final_code"]  = final_code
    st.session_state["result_final_score"] = final_score
    st.session_state["result_page_data"]   = page_data
    st.session_state["result_url"]         = url_input
    st.session_state["result_impact"]      = impact_report
    st.session_state["pipeline_done"]      = True


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.get("pipeline_done"):
    memory      = st.session_state["result_memory"]
    final_code  = st.session_state["result_final_code"]
    final_score = st.session_state["result_final_score"]
    page_data   = st.session_state["result_page_data"]
    impact      = st.session_state.get("result_impact")

    gh_label = ""
    if impact and impact.get("status") == "success":
        gh_label = f" · GitHub: {impact.get('recommendation','?')} ({impact.get('files_scanned',0)} files)"

    st.success(
        f"✅ Pipeline complete — Score: **{final_score}/10** — "
        f"{memory['iterations']+1} iteration(s) — "
        f"{len(memory['locator_rows'])} locators found{gh_label}"
    )

    tab_loc, tab_code, tab_impact = st.tabs(["🔍 Locators", "☕ Java Test Cases", "🐙 GitHub Impact"])

    with tab_loc:
        st.markdown("### Element Locators")
        st.caption(f"Page: **{page_data.get('title', memory['url'])}** · {len(memory['locator_rows'])} elements · Locator strategy: ID > name > CSS > XPath")
        render_locator_table(memory["locator_rows"])
        with st.expander("📄 Raw Agent 1 Output", expanded=False):
            st.text_area("", value=memory["element_analysis"], height=250, label_visibility="collapsed")

    with tab_code:
        st.markdown("### Java Selenium TestNG Test Cases")
        col_score, col_dl = st.columns([1, 1])
        with col_score:
            st.markdown(f"**Quality Score:** {score_badge_html(final_score)}", unsafe_allow_html=True)
        with col_dl:
            st.download_button("⬇️ Download .java", data=final_code, file_name="SeleniumTestNG_Generated.java", mime="text/plain", use_container_width=True)
        st.code(final_code, language="java")

    with tab_impact:
        st.markdown("### GitHub Impact Analysis")
        st.caption("Compares newly generated tests against existing tests in your GitHub repo — finds overlaps, gaps, and new coverage.")
        render_impact_report(impact)

# ── Empty state ───────────────────────────────────────────────────────────────
elif not run_btn:
    st.markdown("""
<div style="display:flex;flex-direction:column;gap:.7rem;margin-top:1.5rem">
  <div class="react-card">
    <div class="agent-name blue">🔍 What this does</div>
    <div class="trace-val" style="margin-top:.3rem">
      1. Scrapes your URL and finds every interactive element<br>
      2. Assigns the best Selenium locator (ID → name → CSS → XPath)<br>
      3. Generates complete Java Selenium TestNG code (POM pattern)<br>
      4. Reviews and scores the code — loops to fix if score &lt; threshold<br>
      5. 🐙 <strong>NEW:</strong> Fetches your existing GitHub test files and performs impact analysis
    </div>
  </div>
  <div class="react-card github">
    <div class="agent-name purple">🐙 GitHub MCP Integration</div>
    <div class="trace-val" style="margin-top:.3rem">
      Connects to your GitHub repo · Scans existing .java test files<br>
      Finds: overlapping coverage · coverage gaps · new scenarios added<br>
      Recommends: MERGE / REPLACE / EXTEND / NO_CHANGE<br>
      Outputs risk level: LOW / MEDIUM / HIGH
    </div>
  </div>
  <div class="react-card orch">
    <div class="agent-name yellow">⬡ Active Agent Patterns</div>
    <div style="display:flex;gap:.8rem;flex-wrap:wrap;margin-top:.4rem;font-family:'IBM Plex Mono',monospace;font-size:.78rem;color:#00ff9d">
      <span>✅ ReAct Loop</span>
      <span>✅ Tool Use</span>
      <span>✅ Agent Memory</span>
      <span>✅ Feedback Loop</span>
      <span>✅ Orchestrator</span>
      <span>✅ GitHub MCP</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.info("👈 Configure Groq + GitHub in the sidebar, enter a URL above, and hit Run.")
