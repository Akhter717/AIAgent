import streamlit as st
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM  # Imported LLM class
from crewai_tools import ScrapeWebsiteTool
import re

load_dotenv()

st.set_page_config(
    page_title="CrewAI QA Agent — Java Selenium TestNG",
    page_icon="🧪",
    layout="wide",
)

# Custom CSS for the UI styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;800&display=swap');
:root {
    --bg: #0d0f12; --surface: #141720; --accent: #00e5a0; --accent2: #5b6af0;
}
html, body, [class*="css"] { font-family: 'Syne', sans-serif; background-color: var(--bg) !important; color: var(--text) !important; }
#MainMenu, footer, header { visibility: hidden; }
.hero { text-align: center; padding: 2rem; border-bottom: 1px solid #2a2f45; }
.hero h1 { font-size: 2.6rem; background: linear-gradient(135deg, #00e5a0, #5b6af0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.card { background: #141720; border: 1px solid #2a2f45; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; }
.code-block { background: #0a0c0f; border-left: 4px solid #5b6af0; padding: 1rem; border-radius: 8px; font-family: 'JetBrains Mono', monospace; overflow-x: auto; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🧪 CrewAI QA Agent</h1>
    <p>Multi-Agent System • Java + Selenium + TestNG • Production Grade</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    groq_api_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""), placeholder="gsk_...")
    model = st.selectbox("LLM Model", ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"], index=0)
    
    st.markdown("---")
    include_waits = st.checkbox("Include WebDriverWait", value=True)
    include_testng = st.checkbox("Use TestNG", value=True)
    max_elements = st.slider("Analysis Depth", 15, 50, 25)

# Agents Setup
@st.cache_resource
def create_crew_agents(api_key, model_name):
    os.environ["GROQ_API_KEY"] = api_key
    scrape_tool = ScrapeWebsiteTool()

    # Explicitly creating the LLM instance prevents the internal Pydantic/ImportError wrapper crash
    groq_llm = LLM(
        model=f"groq/{model_name}",
        api_key=api_key
    )

    element_finder = Agent(
        role="Senior QA Automation Engineer - Locator Expert",
        goal="Discover and prioritize the best locators (ID > Name > CSS > XPath) for all interactive elements.",
        backstory="12+ years in automation. Expert in robust locator strategies for dynamic UIs.",
        tools=[scrape_tool],
        verbose=True,
        llm=groq_llm
    )

    test_architect = Agent(
        role="Selenium Test Architect",
        goal="Generate clean, maintainable Java Selenium + TestNG tests using Page Object Model.",
        backstory="Expert in writing production-grade test automation frameworks.",
        verbose=True,
        llm=groq_llm
    )

    qa_reviewer = Agent(
        role="QA Lead Reviewer",
        goal="Review and improve test quality, reliability, and best practices.",
        backstory="Strict QA leader focused on maintainability and robustness.",
        verbose=True,
        llm=groq_llm
    )

    return element_finder, test_architect, qa_reviewer

# Main UI
url_input = st.text_input("🌐 Enter Website URL", placeholder="https://example.com/login")

col1, col2 = st.columns([1, 1])
with col1:
    run_btn = st.button("🚀 Run CrewAI QA Agents", use_container_width=True, type="primary")

if run_btn:
    if not groq_api_key:
        st.error("Please provide your Groq API Key")
        st.stop()
    if not url_input:
        st.error("Please enter a valid URL")
        st.stop()

    with st.spinner("🔄 Initializing CrewAI Agents..."):
        element_finder, test_architect, qa_reviewer = create_crew_agents(groq_api_key, model)

    # Tasks
    with st.spinner("🕵️ Agent 1: Analyzing elements..."):
        task1 = Task(
            description=f"Scrape and analyze {url_input}. Provide detailed element analysis with best locators. Analyze up to {max_elements} critical elements.",
            agent=element_finder,
            expected_output="Structured element analysis with recommended locators."
        )

    with st.spinner("🏗️ Agent 2: Generating Java Selenium Tests..."):
        wait_instruction = "Include explicit WebDriverWait commands." if include_waits else "Do not prioritize explicit waits."
        testng_instruction = "Utilize TestNG annotations like @Test, @BeforeMethod, and Assertions." if include_testng else "Write using standard JUnit/Java main framework."
        
        task2 = Task(
            description=f"""Generate complete Java Selenium code for {url_input}.
            Use the Page Object Model (POM) architecture.
            Include separate code blocks for the Page class and the Test class.
            Cover positive paths, negative test assertions, and boundary checks.
            {wait_instruction}
            {testng_instruction}""",
            agent=test_architect,
            context=[task1],
            expected_output="Full Java code structured into Page Object and Test classes."
        )

    with st.spinner("👀 Agent 3: Reviewing & Polishing..."):
        task3 = Task(
            description="Review the generated Java infrastructure for syntax accuracy, formatting cleanliness, locator robustness, and architectural soundness. Output the finalized source text.",
            agent=qa_reviewer,
            context=[task2],
            expected_output="Final polished Java Selenium TestNG production-ready source code."
        )

    crew = Crew(
        agents=[element_finder, test_architect, qa_reviewer],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True
    )

    with st.spinner("🤖 Running Multi-Agent Crew... (This may take 30-90 seconds)"):
        try:
            result = crew.kickoff(inputs={"url": url_input})
            
            st.success("✅ CrewAI Agents Completed Successfully!")

            # Display Results
            tab1, tab2 = st.tabs(["📋 Detailed Output", "☕ Java Test Automation Code"])

            with tab1:
                st.markdown("### Agent Execution Result Summary")
                st.text_area("Log Output Summary", value=str(result), height=400)

            with tab2:
                st.markdown("### Final Java + Selenium Framework Package")
                st.code(str(result), language="java")

                # Download button
                st.download_button(
                    "⬇️ Download Java Test Files",
                    data=str(result),
                    file_name="Selenium_TestNG_Tests.java",
                    mime="text/plain"
                )

        except Exception as e:
            st.error(f"Error running CrewAI engine: {str(e)}")

else:
    st.info("Enter URL and click **Run CrewAI QA Agents** to start the multi-agent workflow.")

st.caption("Built with CrewAI • Groq • Java Selenium TestNG")
