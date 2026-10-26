# 🤖 Multi-Agent Report Writer with LangGraph

A **multi-agent AI system** for collaborative report writing, featuring 5 specialized agents orchestrated by LangGraph, with a **real-time visual dashboard** that showcases each agent working.

Built with **LangGraph** × **Gemini** × **Tavily Search** × **FastAPI**.

---

## ✨ Features

- **5 Specialized AI Agents** — each with a distinct role in the report writing pipeline
- **Real-Time Visual Dashboard** — watch each agent activate, process, and complete in a beautiful dark-mode UI
- **Live Workflow Graph** — interactive pipeline showing active/completed agents with animations
- **Agent Activity Log** — collapsible, color-coded log of every agent's output
- **Live Report Display** — see the report evolve with each revision
- **WebSocket Streaming** — real-time updates from backend to frontend

---

## 🏗️ Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │             LangGraph Workflow               │
                    │                                              │
  User Topic ──►   │  📋 Planner ──► 🔍 Researcher ──► ✍️ Writer │
                    │                                    │        │
                    │                     ◄── 🧪 Research ◄── 🪞  │
                    │                        Critique     Reflect │
                    │                                              │
                    └──────────────────────────────────────────────┘
                              │  WebSocket (real-time)  │
                    ┌─────────▼─────────────────────────▼──────────┐
                    │          FastAPI + Static Frontend            │
                    │  ┌────────┐ ┌──────────┐ ┌───────────────┐   │
                    │  │ Graph  │ │ Activity │ │   Report      │   │
                    │  │  View  │ │   Log    │ │   Display     │   │
                    │  └────────┘ └──────────┘ └───────────────┘   │
                    └──────────────────────────────────────────────┘
```

### Agent Roles

| # | Agent | Icon | Role |
|---|-------|------|------|
| 1 | **Planning Agent** | 📋 | Creates the report outline and structure |
| 2 | **Research Agent** | 🔍 | Generates search queries and gathers info via Tavily |
| 3 | **Generation Agent** | ✍️ | Writes and revises the report draft |
| 4 | **Reflection Agent** | 🪞 | Critiques the draft and suggests improvements |
| 5 | **Research Critique Agent** | 🧪 | Finds additional research based on critique feedback |

### Workflow

1. **Planning Agent** receives the topic → produces a structured outline
2. **Research Agent** generates search queries → gathers web content via Tavily
3. **Generation Agent** writes the initial draft using the plan + research
4. **Conditional check**: if `revision_number > max_revisions` → **END**, otherwise → continue
5. **Reflection Agent** reviews the draft → produces detailed critique
6. **Research Critique Agent** finds additional info based on the critique
7. **Generation Agent** revises the draft → back to step 4

---

## 📁 Project Structure

```
├── app.py                    # FastAPI server (WebSocket + static files)
├── main.py                   # Original CLI script (preserved)
├── agents/
│   ├── __init__.py
│   ├── state.py              # Shared AgentState definition
│   ├── prompts.py            # All agent system prompts
│   ├── planner.py            # Planning Agent
│   ├── researcher.py         # Research Agent
│   ├── generator.py          # Generation Agent
│   ├── reflector.py          # Reflection Agent
│   ├── research_critic.py    # Research Critique Agent
│   └── graph_builder.py      # LangGraph workflow builder
├── static/
│   ├── index.html            # Frontend page
│   ├── style.css             # Design system & styles
│   └── app.js                # Frontend application logic
├── .env                      # API keys (not committed)
├── .env.example              # Template for API keys
├── requirements.txt          # Python dependencies
└── readme.md                 # This file
```

---

## 🚀 Setup & Run

### 1. Clone & enter the project

```bash
git clone <repo-url>
cd ai-langgraph-multi-agent-main
```

### 2. Create & activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your keys:
- **Google API Key** — [Get one here](https://aistudio.google.com/apikey)
- **Tavily API Key** — [Get a free key here](https://app.tavily.com/sign-in)

### 5. Run the application

```bash
python app.py
```

Open **http://localhost:8000** in your browser.

### Alternative: Run the original CLI version

```bash
python main.py
```

---

## 🖥️ Visual Interface

The dashboard features:

- **Workflow Pipeline Graph** — shows all 5 agents in sequence with real-time active/completed state indicators and animations
- **Agent Activity Log** — color-coded, expandable entries for each agent's output with detailed content
- **Generated Report** — live-updating report display with revision tracking

---

## 🔧 Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `max_revisions` | 2 | Number of revision loops (reflect → research → rewrite) |
| Model | `gemini-2.0-flash` | Google Gemini model used by all agents |
| Search results | 2 per query | Tavily search results per query (max 3 queries per research step) |

---

## 📦 Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Orchestration | LangGraph |
| LLM | Google Gemini (via LangChain) |
| Web Search | Tavily |
| Backend | FastAPI + WebSocket |
| Frontend | Vanilla HTML/CSS/JS |
| State Persistence | SQLite (in-memory) |

---

## 📜 License

MIT
