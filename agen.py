"""
Multi-Agent QA Code Generator v3
----------------------------------
Changes from v2:
  ✅ Sidebar removed → collapsible top config panel (mobile-friendly)
  ✅ Output simplified to 2 tabs:
       Tab 1 — Locators table (element, purpose, locator, priority)
       Tab 2 — Java Selenium TestNG test cases
  ✅ All agent internals (ReAct loop, memory, feedback loop) preserved
  ✅ Mobile-responsive layout

No CrewAI · No LangChain · No paid APIs · Groq free tier only
"""

import streamlit as st
import requests
import time
import re
import json
from bs4 import BeautifulSoup
from groq import Groq

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Agent v3",
    page_icon="🤖",
    layout="centered",   # centered works better on mobile than "wide"
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
  --text:         #d4daf0;
  --muted:        #5a6380;
}

/* ── Global reset ── */
html, body, [class*="css"] {
  font-family: 'Bricolage Grotesque', sans-serif;
  background: var(--bg) !important;
  color: var(--text) !important;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── Mobile-first container ── */
.block-container {
  padding: 1rem !important;
  max-width: 900px !important;
}

/* ── Hero ── */
.hero {
  padding: 1.8rem .5rem 1.4rem;
  text-align: center;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.4rem;
}
.hero-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .68rem;
  color: var(--blue);
  letter-spacing: .18em;
  text-transform: uppercase;
  margin-bottom: .5rem;
}
.hero h1 {
  font-size: clamp(1.6rem, 5vw, 2.4rem);
  font-weight: 800;
  background: linear-gradient(135deg, #00ff9d 0%, #4d79ff 50%, #ff8c42 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 .4rem;
  line-height: 1.15;
}
.hero p { color: var(--muted); font-size: .88rem; margin: 0; }

/* ── Config panel (replaces sidebar) ── */
.config-panel {
  background: var(--card);
  border: 1px solid var(--border-bright);
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 1.2rem;
}
.config-panel h4 {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .75rem;
  color: var(--blue);
  letter-spacing: .12em;
  text-transform: uppercase;
  margin: 0 0 .8rem;
}

/* ── ReAct trace card ── */
.react-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 3px solid var(--blue);
  border-radius: 10px;
  padding: .8rem 1rem;
  margin-bottom: .7rem;
  font-size: .82rem;
  word-break: break-word;
}
.react-card.done  { border-left-color: var(--green); }
.react-card.loop  { border-left-color: var(--orange); }
.react-card.error { border-left-color: var(--red); }
.react-card.orch  { border-left-color: var(--yellow); }

.agent-name {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .72rem;
  font-weight: 600;
  letter-spacing: .1em;
  text-transform: uppercase;
  margin-bottom: .5rem;
}
.agent-name.green  { color: var(--green); }
.agent-name.blue   { color: var(--blue); }
.agent-name.orange { color: var(--orange); }
.agent-name.yellow { color: var(--yellow); }
.agent-name.red    { color: var(--red); }

.trace-row { margin-bottom: .35rem; display: flex; flex-wrap: wrap; gap: 4px; }
.trace-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .7rem;
  color: var(--muted);
  min-width: 85px;
}
.trace-val {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .76rem;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
}
.trace-val.green  { color: var(--green); }
.trace-val.orange { color: var(--orange); }

/* ── Locator table ── */
.loc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: .8rem;
  font-family: 'IBM Plex Mono', monospace;
}
.loc-table th {
  background: var(--surface);
  color: var(--muted);
  font-size: .68rem;
  letter-spacing: .08em;
  text-transform: uppercase;
  padding: .5rem .7rem;
  border-bottom: 1px solid var(--border-bright);
  text-align: left;
  white-space: nowrap;
}
.loc-table td {
  padding: .55rem .7rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  word-break: break-all;
}
.loc-table tr:hover td { background: rgba(77,121,255,.04); }

/* priority badges */
.badge {
  display: inline-block;
  border-radius: 5px;
  padding: 1px 7px;
  font-size: .68rem;
  font-weight: 700;
  white-space: nowrap;
}
.badge-high   { background: rgba(0,255,157,.1);   color: var(--green);  border: 1px solid var(--green); }
.badge-med    { background: rgba(255,209,102,.1); color: var(--yellow); border: 1px solid var(--yellow); }
.badge-low    { background: rgba(90,99,128,.15);  color: var(--muted);  border: 1px solid var(--border-bright); }
.badge-id     { background: rgba(77,121,255,.1);  color: var(--blue);   border: 1px solid var(--blue); }
.badge-name   { background: rgba(0,255,157,.08);  color: var(--green);  border: 1px solid rgba(0,255,157,.3); }
.badge-css    { background: rgba(255,140,66,.08); color: var(--orange); border: 1px solid rgba(255,140,66,.3); }
.badge-xpath  { background: rgba(255,77,109,.08); color: var(--red);    border: 1px solid rgba(255,77,109,.3); }

.locator-val  { color: var(--green); font-size: .78rem; }

/* ── Score badge ── */
.score-badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 20px;
  font-size: .78rem;
  font-weight: 700;
  font-family: 'IBM Plex Mono', monospace;
}
.score-high { background: rgba(0,255,157,.1);   color: var(--green);  border: 1px solid var(--green); }
.score-mid  { background: rgba(255,209,102,.1); color: var(--yellow); border: 1px solid var(--yellow); }
.score-low  { background: rgba(255,77,109,.1);  color: var(--red);    border: 1px solid var(--red); }

/* ── Iter badge ── */
.iter-badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .7rem;
  color: var(--orange);
  background: rgba(255,140,66,.08);
  border: 1px solid rgba(255,140,66,.3);
  border-radius: 4px;
  padding: 1px 7px;
  margin-left: 7px;
}

/* ── Streamlit widget overrides ── */
.stButton > button {
  background: linear-gradient(135deg, #00ff9d, #4d79ff) !important;
  color: #080a0f !important;
  font-weight: 700 !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Bricolage Grotesque', sans-serif !important;
  width: 100% !important;
}
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input {
  background: var(--card) !important;
  color: var(--text) !important;
  border: 1px solid var(--border-bright) !important;
  border-radius: 8px !important;
  font-family: 'IBM Plex Mono', monospace !important;
}
.stDownloadButton > button {
  background: var(--card) !important;
  color: var(--green) !important;
  border: 1px solid var(--green) !important;
  border-radius: 8px !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: .78rem !important;
}
div[data-testid="stExpander"] {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
/* Make sliders and checkboxes readable on dark bg */
.stSlider label, .stCheckbox label, .stSelectbox label {
  color: var(--muted) !important;
  font-size: .82rem !important;
}

/* ── Responsive table wrapper ── */
.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: 10px;
  border: 1px solid var(--border);
}
</style>
""", unsafe_allow_html=True)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-label">Scrape · Locate · Generate · Review</div>
  <h1>Multi-Agent QA System</h1>
  <p>Element Locators + Java Selenium TestNG · Groq Free Tier</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG PANEL  (replaces sidebar — works on mobile)
# ══════════════════════════════════════════════════════════════════════════════

with st.expander("⚙️ Configuration", expanded=False):
    st.markdown(
        "Get a **free** Groq API key at "
        "[console.groq.com](https://console.groq.com)"
    )
    groq_api_key = st.text_input(
        "Groq API Key", type="password",
        placeholder="gsk_...",
        key="api_key",
    )
    model = st.selectbox(
        "Model",
        ["llama-3.3-70b-versatile", "llama3-8b-8192", "gemma2-9b-it"],
        index=0,
    )
    col_a, col_b = st.columns(2)
    with col_a:
        include_waits  = st.checkbox("WebDriverWait", value=True)
        include_testng = st.checkbox("Use TestNG",    value=True)
    with col_b:
        max_elements   = st.slider("Max elements", 10, 40, 20)
        delay_secs     = st.slider("Agent delay (s)", 2, 10, 4)
    col_c, col_d = st.columns(2)
    with col_c:
        max_iterations = st.slider("Max loop iterations", 1, 5, 3)
    with col_d:
        score_threshold = st.slider("Quality threshold", 5, 9, 7)


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════════════════

def tool_scrape_page(url: str, limit: int) -> dict:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (QA-AgentBot/3.0)"},
            timeout=15, verify=False,
        )
        r.raise_for_status()
        soup  = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "Unknown"
        h1s   = [h.get_text(strip=True) for h in soup.find_all("h1", limit=3)]
        forms = [str(f)[:200] for f in soup.find_all("form", limit=3)]
        elements = []
        for tag in soup.find_all(
            ["input", "button", "a", "select", "textarea", "label"],
            limit=limit * 2,
        ):
            attrs = {
                k: (v if isinstance(v, str) else " ".join(v))
                for k, v in tag.attrs.items()
                if k in ("id", "name", "type", "class", "href",
                         "placeholder", "aria-label", "value", "action")
            }
            elements.append({
                "tag":   tag.name,
                "text":  tag.get_text(strip=True)[:60],
                "attrs": attrs,
            })
            if len(elements) >= limit:
                break
        return {
            "status":   "success",
            "title":    title,
            "h1s":      h1s,
            "url":      url,
            "forms":    forms,
            "elements": elements,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "url": url, "elements": []}


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
    if "//*[" in code or "//div[" in code:
        count = code.count("//*[") + code.count("//div[")
        if count > 3:
            issues.append(f"Excessive absolute XPath ({count} occurrences)")
    if code.count("{") != code.count("}"):
        issues.append(f"Bracket mismatch: {{ {code.count('{')} vs }} {code.count('}')}")
    if "package com.qa" not in code:
        issues.append("Missing package declaration")
    return {"issues": issues, "issue_count": len(issues), "valid": len(issues) == 0}


def tool_score_code(code: str, issues: list) -> dict:
    score = 10
    score -= len(issues) * 1.5
    if len(code) < 500:
        score -= 2
    if "WebDriverWait" in code:
        score += 0.5
    if "PageFactory" in code or "FindBy" in code:
        score += 0.5
    return {"score": max(0, min(10, round(score, 1))), "max": 10}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT MEMORY
# ══════════════════════════════════════════════════════════════════════════════

def init_memory(url: str) -> dict:
    return {
        "url":              url,
        "page_data":        None,
        "element_analysis": None,   # plain-text list from Agent 1
        "locator_rows":     [],     # structured rows for the table
        "raw_code":         None,
        "final_code":       None,
        "iterations":       0,
        "scores":           [],
        "issues_history":   [],
        "agent_logs":       [],
        "orchestrator_plan": None,
    }


def log_trace(memory: dict, agent: str, thought: str, action: str, observation: str):
    memory["agent_logs"].append({
        "agent":      agent,
        "thought":    thought,
        "action":     action,
        "observation":observation,
        "iteration":  memory["iterations"],
        "ts":         time.time(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# LOCATOR TABLE BUILDER  (parses Agent 1 text output into structured rows)
# ══════════════════════════════════════════════════════════════════════════════

def parse_locator_rows(agent1_text: str, page_elements: list) -> list:
    """
    Produces structured rows for the Locators tab table.
    Combines heuristic parsing from the raw page elements with
    the LLM-enriched agent 1 output.
    """
    rows = []
    seen = set()

    # ── 1. Parse the LLM output lines first (highest quality) ─────────────
    # Expected format (from agent prompt):
    #   [N] Tag: <tag> | Purpose: <desc> | Locator: By.xxx("val") | Priority: HIGH/MED/LOW
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

        # Derive locator type from the By.xxx prefix
        loc_type = "XPATH"
        if "By.id(" in loc:         loc_type = "ID"
        elif "By.name(" in loc:     loc_type = "NAME"
        elif "By.cssSelector(" in loc: loc_type = "CSS"
        elif "By.className(" in loc:   loc_type = "CLASS"
        elif "By.linkText(" in loc:    loc_type = "LINK"

        rows.append({
            "tag":      m.group("tag").strip().replace("<", "").replace(">", ""),
            "purpose":  m.group("purpose").strip(),
            "locator":  loc,
            "loc_type": loc_type,
            "priority": m.group("priority").strip().upper(),
        })

    # ── 2. Fall back to raw scraped elements if LLM parse gave few rows ────
    if len(rows) < 3 and page_elements:
        for el in page_elements:
            attrs = el.get("attrs", {})
            tag   = el.get("tag", "?")
            text  = el.get("text", "")

            # Best locator
            if attrs.get("id"):
                loc      = f'By.id("{attrs["id"]}")'
                loc_type = "ID"
            elif attrs.get("name"):
                loc      = f'By.name("{attrs["name"]}")'
                loc_type = "NAME"
            elif attrs.get("class"):
                cls = attrs["class"].split()[0]
                loc      = f'By.cssSelector("{tag}.{cls}")'
                loc_type = "CSS"
            elif attrs.get("href"):
                href_val = attrs["href"][:40]
                loc      = f'By.cssSelector("a[href=\'{href_val}\']")'
                loc_type = "CSS"
            else:
                loc      = f'By.xpath("//{tag}")'
                loc_type = "XPATH"

            if loc in seen:
                continue
            seen.add(loc)

            # Infer purpose
            combined = (text + " " + attrs.get("placeholder", "") + " " + attrs.get("aria-label", "")).lower()
            if "password" in combined or attrs.get("type") == "password":
                purpose, priority = "Password field", "HIGH"
            elif "email" in combined or attrs.get("type") == "email":
                purpose, priority = "Email input", "HIGH"
            elif "login" in combined or "sign in" in combined:
                purpose, priority = "Login action", "HIGH"
            elif "search" in combined:
                purpose, priority = "Search field", "HIGH"
            elif "submit" in combined or attrs.get("type") == "submit":
                purpose, priority = "Form submit", "HIGH"
            elif tag == "select":
                purpose, priority = "Dropdown selector", "MED"
            elif tag == "a":
                purpose, priority = f"Link: {text[:30] or attrs.get('href', '')[:25]}", "MED"
            elif tag == "button":
                purpose, priority = f"Button: {text[:30]}", "MED"
            else:
                purpose, priority = f"<{tag}> element", "LOW"

            rows.append({
                "tag":      tag,
                "purpose":  purpose,
                "locator":  loc,
                "loc_type": loc_type,
                "priority": priority,
            })

    return rows


# ══════════════════════════════════════════════════════════════════════════════
# LLM WRAPPER
# ══════════════════════════════════════════════════════════════════════════════

def call_llm(client: Groq, model_name: str, system: str, user: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
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
Output ONLY valid JSON (no markdown fences):
{"plan":["agent_1","agent_2","agent_3"],"priority":"correctness|speed|coverage","notes":"brief instruction"}"""
    page_summary = (
        f"URL: {memory['url']}, Elements: {len(memory['page_data'].get('elements', []))}"
        if memory['page_data'] and memory['page_data'].get('status') == 'success'
        else f"URL: {memory['url']}, scrape failed"
    )
    user = f"""State: {page_summary}
Iterations: {memory['iterations']}
Last score: {memory['scores'][-1] if memory['scores'] else 'none'}
Issues: {memory['issues_history'][-1] if memory['issues_history'] else 'none'}
Determine execution plan."""
    raw = call_llm(client, model_name, system, user)
    try:
        return json.loads(raw.replace("```json", "").replace("```", "").strip()).get("notes", "Standard pipeline.")
    except Exception:
        return "Standard pipeline."


def orchestrator_should_loop(client, model_name, memory: dict, score: float, threshold: float) -> bool:
    if score >= threshold or memory["iterations"] >= 3:
        return False
    system = 'Answer ONLY with JSON: {"loop":true} or {"loop":false}.'
    user = f"Score {score}/{threshold}. Issues: {memory['issues_history'][-1]}. Iterations: {memory['iterations']}. Loop?"
    raw = call_llm(client, model_name, system, user)
    try:
        return json.loads(raw.replace("```json", "").replace("```", "").strip()).get("loop", False)
    except Exception:
        return score < threshold


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — Element Finder
# ══════════════════════════════════════════════════════════════════════════════

def agent_element_finder(client, model_name, memory: dict, max_el: int) -> str:
    thought = f"Identify testable elements on {memory['url']} using scraped data."
    page = memory["page_data"]
    if page["status"] == "error":
        ctx = f"Scrape failed: {page.get('error')}. URL: {memory['url']}"
    else:
        rows = [f"  <{el['tag']}> text='{el['text']}' attrs={el['attrs']}" for el in page["elements"]]
        ctx = (
            f"Title: {page['title']}\nH1s: {', '.join(page['h1s'])}\n"
            f"URL: {page['url']}\nForms: {len(page['forms'])}\n\n"
            f"Elements ({len(rows)}):\n" + "\n".join(rows)
        )

    system = """You are a Senior QA Automation Engineer. Analyse this page and output elements in EXACTLY this format per line:
[N] Tag: <tag> | Purpose: <what it does> | Locator: By.<TYPE>("<value>") | Priority: HIGH/MED/LOW
Prefer: ID > name > CSS selector > XPath. No preamble."""

    user = f"""Analyse and list up to {max_el} interactive elements with best Selenium locators.

PAGE SNAPSHOT:
{ctx}

Output each element on its own line using the exact format above."""

    result = call_llm(client, model_name, system, user)
    log_trace(memory, "Element Finder", thought, "call_llm(element_analysis)",
              f"Got {result.count('[')  } element entries.")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — Test Architect
# ══════════════════════════════════════════════════════════════════════════════

def agent_test_architect(client, model_name, memory: dict,
                         wait_instr: bool, testng_instr: bool) -> str:
    iteration   = memory["iterations"]
    prev_issues = memory["issues_history"][-1] if memory["issues_history"] else []
    prev_code   = memory["raw_code"]

    thought = (
        "First pass — generating full Java POM test suite."
        if iteration == 0
        else f"Iteration {iteration+1} — fixing: {prev_issues}"
    )

    waits_note = (
        "Use WebDriverWait(driver, Duration.ofSeconds(10)) + ExpectedConditions. NEVER Thread.sleep()."
        if wait_instr else "Implicit waits acceptable."
    )
    testng_note = (
        "Use TestNG: import org.testng.annotations.*; import org.testng.Assert;"
        if testng_instr else
        "Use JUnit 5: import org.junit.jupiter.api.*; import static org.junit.jupiter.api.Assertions.*;"
    )

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
    log_trace(memory, "Test Architect", thought,
              f"call_llm(generate_code, iter={iteration+1})",
              f"Generated {len(result)} chars.")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — QA Reviewer
# ══════════════════════════════════════════════════════════════════════════════

def agent_qa_reviewer(client, model_name, memory: dict) -> tuple:
    code    = memory["raw_code"]
    thought = "Validate with tools, score, then fix any issues."

    validation   = tool_validate_java_syntax(code)
    issues       = validation["issues"]
    score_result = tool_score_code(code, issues)
    score        = score_result["score"]

    log_trace(memory, "QA Reviewer", thought,
              "tool_validate_java_syntax() + tool_score_code()",
              f"Issues: {len(issues)}. Score: {score}/10.")

    system = """You are a strict QA Lead Reviewer. Fix ALL issues in this Java Selenium code.
Output ONLY the corrected Java code. No explanation. No markdown fences."""

    issue_list = "\n".join(f"  - {i}" for i in issues) if issues else "  - No critical issues. Improve robustness."
    user = f"""Fix this Java Selenium TestNG code for {memory['url']}.

ISSUES:
{issue_list}

CODE:
{code}

Output final production-ready code:"""

    fixed_code     = call_llm(client, model_name, system, user)
    re_val         = tool_validate_java_syntax(fixed_code)
    re_score       = tool_score_code(fixed_code, re_val["issues"])
    final_score    = re_score["score"]

    log_trace(memory, "QA Reviewer",
              "Re-validating fixed code.",
              "tool_validate_java_syntax(fixed) + tool_score_code(fixed)",
              f"Final score: {final_score}/10. Remaining issues: {re_val['issues']}")

    memory["issues_history"].append(re_val["issues"])
    memory["scores"].append(final_score)
    return fixed_code, final_score, re_val["issues"]


# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def render_trace(log: dict):
    color_map = {
        "Orchestrator":   "yellow",
        "Element Finder": "blue",
        "Test Architect": "green",
        "QA Reviewer":    "orange",
    }
    color      = color_map.get(log["agent"], "blue")
    iter_badge = f'<span class="iter-badge">iter {log["iteration"]+1}</span>' if log["iteration"] > 0 else ""
    st.markdown(f"""
<div class="react-card">
  <div class="agent-name {color}">⬡ {log['agent']}{iter_badge}</div>
  <div class="trace-row">
    <span class="trace-label">THOUGHT</span>
    <span class="trace-val">{log['thought']}</span>
  </div>
  <div class="trace-row">
    <span class="trace-label">ACTION</span>
    <span class="trace-val green">{log['action']}</span>
  </div>
  <div class="trace-row">
    <span class="trace-label">OBSERVATION</span>
    <span class="trace-val">{log['observation']}</span>
  </div>
</div>""", unsafe_allow_html=True)


def score_badge_html(score: float) -> str:
    cls = "score-high" if score >= 7 else ("score-mid" if score >= 5 else "score-low")
    return f'<span class="score-badge {cls}">{score}/10</span>'


def priority_badge(p: str) -> str:
    cls = {"HIGH": "badge-high", "MED": "badge-med", "LOW": "badge-low"}.get(p, "badge-low")
    return f'<span class="badge {cls}">{p}</span>'


def loctype_badge(t: str) -> str:
    cls = {"ID": "badge-id", "NAME": "badge-name", "CSS": "badge-css",
           "CLASS": "badge-css", "LINK": "badge-css"}.get(t, "badge-xpath")
    return f'<span class="badge {cls}">{t}</span>'


def render_locator_table(rows: list):
    if not rows:
        st.warning("No locators extracted. The page may block scraping — test cases were still generated from URL context.")
        return

    # Stats row
    high = sum(1 for r in rows if r["priority"] == "HIGH")
    ids  = sum(1 for r in rows if r["loc_type"] == "ID")
    css  = sum(1 for r in rows if r["loc_type"] in ("CSS", "CLASS", "LINK"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Elements",    len(rows))
    c2.metric("HIGH priority", high)
    c3.metric("ID locators",  ids)
    c4.metric("CSS/XPath",    len(rows) - ids)

    # Table
    header = """
<div class="table-scroll">
<table class="loc-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Tag</th>
      <th>Purpose</th>
      <th>Type</th>
      <th>Locator</th>
      <th>Priority</th>
    </tr>
  </thead>
  <tbody>"""
    body_rows = []
    for i, r in enumerate(rows, 1):
        body_rows.append(f"""
    <tr>
      <td style="color:var(--muted)">{i}</td>
      <td style="color:var(--muted)">&lt;{r['tag']}&gt;</td>
      <td style="color:var(--text)">{r['purpose']}</td>
      <td>{loctype_badge(r['loc_type'])}</td>
      <td class="locator-val">{r['locator']}</td>
      <td>{priority_badge(r['priority'])}</td>
    </tr>""")
    footer = "\n  </tbody>\n</table>\n</div>"
    st.markdown(header + "".join(body_rows) + footer, unsafe_allow_html=True)

    # Download locators as CSV
    csv_lines = ["#,Tag,Purpose,Locator Type,Locator,Priority"]
    for i, r in enumerate(rows, 1):
        csv_lines.append(f'{i},{r["tag"]},"{r["purpose"]}",{r["loc_type"]},"{r["locator"]}",{r["priority"]}')
    st.download_button(
        "⬇️ Download Locators CSV",
        data="\n".join(csv_lines),
        file_name="locators.csv",
        mime="text/csv",
        use_container_width=True,
    )


def is_valid_url(url: str) -> bool:
    return bool(re.match(
        r'^https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:\d+)?(/[^\s]*)?$',
        url.strip()
    ))


# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════════════════

url_input = st.text_input(
    "🌐 Target Website URL",
    placeholder="https://example.com/login",
)

run_btn = st.button("🚀 Run QA Agent Pipeline", use_container_width=True, type="primary")

if run_btn:
    # ── Validation ────────────────────────────────────────────────────────────
    if not groq_api_key or not groq_api_key.startswith("gsk_"):
        st.error("❌ Open ⚙️ Configuration above and enter your Groq API key.")
        st.stop()
    if not url_input or not is_valid_url(url_input):
        st.error("❌ Enter a valid URL (https:// or http://)")
        st.stop()

    client = Groq(api_key=groq_api_key)
    memory = init_memory(url_input)

    # ── Agent execution log (collapsible) ─────────────────────────────────────
    with st.expander("🤖 Agent Execution Log", expanded=False):
        trace_container = st.container()

    # ── STEP 0: Scraper Tool ─────────────────────────────────────────────────
    with st.spinner("🌐 Scraping page…"):
        page_data = tool_scrape_page(url_input, max_elements)
        memory["page_data"] = page_data

    log_trace(memory, "Orchestrator",
              f"Pipeline started for {url_input}. Running scraper.",
              "tool_scrape_page(url)",
              f"Scraped {len(page_data.get('elements', []))} elements. Status: {page_data['status']}")
    with trace_container:
        render_trace(memory["agent_logs"][-1])

    time.sleep(delay_secs)

    # ── Orchestrator Plan ─────────────────────────────────────────────────────
    with st.spinner("🧠 Orchestrator planning…"):
        orch_notes = orchestrator_plan(client, model, memory)
        memory["orchestrator_plan"] = orch_notes
        log_trace(memory, "Orchestrator",
                  "Analysing memory state for execution plan.",
                  "orchestrator_plan(memory)",
                  f"Plan: {orch_notes}")
    with trace_container:
        render_trace(memory["agent_logs"][-1])

    time.sleep(delay_secs)

    # ── Agent 1: Element Finder ───────────────────────────────────────────────
    with st.spinner("🔍 Agent 1: Finding elements & locators…"):
        try:
            a1_out = agent_element_finder(client, model, memory, max_elements)
            memory["element_analysis"] = a1_out
            # Parse structured rows for the Locators tab
            memory["locator_rows"] = parse_locator_rows(
                a1_out, page_data.get("elements", [])
            )
        except Exception as e:
            st.error(f"Agent 1 failed: {e}")
            st.stop()
    with trace_container:
        render_trace(memory["agent_logs"][-1])

    time.sleep(delay_secs)

    # ── Feedback Loop: Agent 2 → Agent 3 ─────────────────────────────────────
    final_code  = ""
    final_score = 0.0

    for iteration in range(max_iterations):
        memory["iterations"] = iteration

        # Agent 2
        with st.spinner(f"☕ Agent 2: Writing Java code (iter {iteration+1})…"):
            try:
                a2_out = agent_test_architect(client, model, memory, include_waits, include_testng)
                memory["raw_code"] = a2_out
            except Exception as e:
                st.error(f"Agent 2 failed: {e}")
                st.stop()
        with trace_container:
            render_trace(memory["agent_logs"][-1])

        time.sleep(delay_secs)

        # Agent 3
        with st.spinner(f"🔎 Agent 3: Reviewing & scoring (iter {iteration+1})…"):
            try:
                fixed_code, score, issues = agent_qa_reviewer(client, model, memory)
                memory["final_code"] = fixed_code
                final_code  = fixed_code
                final_score = score
            except Exception as e:
                st.error(f"Agent 3 failed: {e}")
                st.stop()
        with trace_container:
            render_trace(memory["agent_logs"][-1])
            score_html   = score_badge_html(score)
            issues_html  = "<br>".join(f"• {i}" for i in issues) if issues else "✅ No issues"
            st.markdown(f"""
<div class="react-card {'done' if score >= score_threshold else 'loop'}">
  <div class="agent-name orange">🔎 QA Reviewer — {score_html}</div>
  <div class="trace-val" style="margin-top:.35rem">{issues_html}</div>
</div>""", unsafe_allow_html=True)

        # Orchestrator decision
        if score >= score_threshold:
            log_trace(memory, "Orchestrator",
                      f"Score {score} ≥ {score_threshold}. Accepted.",
                      "orchestrator_should_loop() → False",
                      "Pipeline complete.")
            with trace_container:
                render_trace(memory["agent_logs"][-1])
                st.markdown(f"""
<div class="react-card done">
  <div class="agent-name yellow">✅ Orchestrator — Pipeline Complete</div>
  <div class="trace-val green" style="margin-top:.35rem">Score {score}/10 accepted after {iteration+1} iteration(s).</div>
</div>""", unsafe_allow_html=True)
            break
        else:
            should_loop = orchestrator_should_loop(client, model, memory, score, score_threshold)
            if should_loop and iteration < max_iterations - 1:
                log_trace(memory, "Orchestrator",
                          f"Score {score} < {score_threshold}. Looping.",
                          f"orchestrator_should_loop() → True (iter {iteration+2})",
                          f"Issues → Agent 2: {issues}")
                with trace_container:
                    render_trace(memory["agent_logs"][-1])
                    st.markdown(f"""
<div class="react-card loop">
  <div class="agent-name yellow">♻️ Feedback Loop — Iteration {iteration+2}</div>
  <div class="trace-val orange" style="margin-top:.35rem">Score {score}/10 below {score_threshold}. Re-running Agent 2 → Agent 3.</div>
</div>""", unsafe_allow_html=True)
                time.sleep(delay_secs)
            else:
                log_trace(memory, "Orchestrator",
                          f"Max iterations or cap reached. Accepting {score}.",
                          "orchestrator_should_loop() → False (cap)",
                          "Exiting with best code.")
                with trace_container:
                    render_trace(memory["agent_logs"][-1])
                break

    # ════════════════════════════════════════════════════════════════════════
    # FINAL OUTPUT — 2 TABS ONLY
    # ════════════════════════════════════════════════════════════════════════
    st.success(
        f"✅ Pipeline complete — Score: **{final_score}/10** — "
        f"{memory['iterations']+1} iteration(s) — "
        f"{len(memory['locator_rows'])} locators found"
    )

    tab_loc, tab_code = st.tabs(["🔍 Locators", "☕ Java Test Cases"])

    # ── Tab 1: Locators ───────────────────────────────────────────────────────
    with tab_loc:
        st.markdown("### Element Locators")
        st.caption(
            f"Page: **{page_data.get('title', url_input)}** · "
            f"{len(memory['locator_rows'])} elements · "
            f"Locator strategy: ID > name > CSS > XPath"
        )
        render_locator_table(memory["locator_rows"])

        # Also show raw Agent 1 output for reference
        with st.expander("📄 Raw Agent 1 Output", expanded=False):
            st.text_area("", value=memory["element_analysis"], height=250, label_visibility="collapsed")

    # ── Tab 2: Java Test Cases ────────────────────────────────────────────────
    with tab_code:
        st.markdown("### Java Selenium TestNG Test Cases")
        col_score, col_dl = st.columns([1, 1])
        with col_score:
            st.markdown(f"**Quality Score:** {score_badge_html(final_score)}", unsafe_allow_html=True)
        with col_dl:
            st.download_button(
                "⬇️ Download .java",
                data=final_code,
                file_name="SeleniumTestNG_Generated.java",
                mime="text/plain",
                use_container_width=True,
            )
        st.code(final_code, language="java")


# ── Empty state ───────────────────────────────────────────────────────────────
else:
    st.markdown("""
<div style="display:flex;flex-direction:column;gap:.7rem;margin-top:1.5rem">
  <div class="react-card">
    <div class="agent-name blue">🔍 What this does</div>
    <div class="trace-val" style="margin-top:.3rem">
      1. Scrapes your URL and finds every interactive element<br>
      2. Assigns the best Selenium locator (ID → name → CSS → XPath)<br>
      3. Generates complete Java Selenium TestNG code (POM pattern)<br>
      4. Reviews and scores the code — loops to fix if score &lt; threshold
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
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.info("👆 Open **⚙️ Configuration**, add your Groq API key, then enter a URL and hit Run.")

st.caption("QA Agent v3 · Groq Free Tier · BeautifulSoup · Streamlit · Zero paid dependencies")
