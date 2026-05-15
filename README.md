# Smart Code Assistant

An AI-powered code generation, review, and analysis platform built with FastAPI, React, and LangChain. Combines LLM-driven code intelligence with a code knowledge graph (GraphRAG) for deep structural understanding of your codebase.

## Features

### AI Code Intelligence
- **Code Generation** - Generate code from natural language descriptions using ZhipuAI GLM-4 models
- **Code Review** - Automated code review with scoring, issue detection, and improvement suggestions
- **AI Chat** - Multi-turn conversational assistant for code-related questions with context history
- **Streaming Responses** - Real-time SSE streaming for AI responses with heartbeat and tool events

### LangChain Agent System
- Configurable AI agents ("digital humans") with custom domains and system prompts
- Agents invoke multiple code analysis tools in parallel (structure, smells, complexity, security)
- Persistent conversation history with token tracking and summarization
- Agent lifecycle management: draft, active, inactive, and training states

### Code Knowledge Graph (GraphRAG)
- AST-based code parsing and entity extraction (functions, classes, imports, variables)
- Neo4j-powered dependency graph with relationship types: CALLS, IMPORTS, INHERITS, CONTAINS
- Hybrid retrieval: parallel ChromaDB semantic search + Neo4j graph traversal
- Dependency analysis, impact analysis, path finding, and semantic code search

### Code Analysis
- Structure analysis (line counts, functions, classes, imports)
- Code smell detection
- Cyclomatic complexity calculation
- Security vulnerability scanning
- Run analyses individually or combined

### Document Management
- Full document CRUD with categories and project association
- Version control with change tracking and diff viewing
- PDF-to-Markdown conversion via Datalab Marker API
- Rich text editing with TipTap (images, links, code blocks)

### Project & Code File Management
- User-owned projects with code file organization
- Monaco Editor integration with syntax highlighting
- Multi-language support

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS 4 |
| Backend | Python, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| AI/LLM | LangChain, LangGraph, ZhipuAI GLM-4 |
| Relational DB | MySQL 8.0 (via aiomysql) |
| Graph DB | Neo4j 5.15 (code knowledge graph) |
| Vector DB | ChromaDB (semantic search) |
| Auth | JWT (access + refresh tokens), Argon2 password hashing |
| Observability | OpenTelemetry, Jaeger, Prometheus metrics |
| Deployment | Docker Compose |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│       (Monaco Editor, TipTap, Cyberpunk UI)         │
└──────────────────────┬──────────────────────────────┘
                       │  /api
┌──────────────────────▼──────────────────────────────┐
│                FastAPI Backend                       │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ Auth &   │ │ Code Gen │ │  LangChain Agent    │ │
│  │ Users    │ │ & Review │ │  (parallel tools)   │ │
│  └──────────┘ └──────────┘ └─────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ Document │ │  Code    │ │  Code Knowledge     │ │
│  │ Mgmt     │ │ Analysis │ │  Graph (GraphRAG)   │ │
│  └──────────┘ └──────────┘ └─────────────────────┘ │
└───┬──────────────┬──────────────────┬───────────────┘
    │              │                  │
┌───▼───┐   ┌─────▼─────┐   ┌───────▼───────┐
│ MySQL │   │   Neo4j   │   │   ChromaDB    │
│  8.0  │   │   5.15    │   │  (vectors)    │
└───────┘   └───────────┘   └───────────────┘
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- ZhipuAI API key

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Smart_Code_Assistant.git
cd Smart_Code_Assistant
```

### 2. Start Infrastructure Services

```bash
docker compose up -d
```

This starts MySQL (port 3307), Neo4j (ports 7474, 7687), and ChromaDB (port 8001).

### 3. Configure Backend

```bash
cp backend-fastapi/.env.example backend-fastapi/.env
```

Edit `backend-fastapi/.env` and set your ZhipuAI API key and other configuration values.

### 4. Start the Backend

```bash
cd backend-fastapi
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to the backend.

### 6. Default User

A demo user is seeded on first startup:

| Field | Value |
|-------|-------|
| Username | `demo` |
| Password | `demo123456` |

## API Overview

| Endpoint Group | Path Prefix | Description |
|---------------|-------------|-------------|
| Auth | `/api/v1/auth` | Login, register, token refresh |
| Projects | `/api/v1/projects` | Project CRUD |
| Code Files | `/api/v1/code-files` | Code file management |
| AI Code Gen | `/api/v1/ai` | Code generation, review, chat |
| Agent | `/api/v1/agent` | LangChain agent analysis, generation, chat |
| Agent Stream | `/api/v1/agent/chat/stream` | SSE streaming chat |
| Agents | `/api/v1/agents` | Agent CRUD, conversations, training |
| Code Analysis | `/api/v1/code-analysis` | Structure, smells, complexity, security |
| Code Graph | `/api/v1/code-graph` | Knowledge graph build and queries |
| Documents | `/api/v1/documents` | Document CRUD and PDF parsing |
| Versions | `/api/v1/versions` | Document versioning |
| Health | `/api/v1/health` | Service health check |
| Metrics | `/metrics` | Prometheus metrics |

## Configuration

### Environment Variables

Key configuration options (set in `backend-fastapi/.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ZHIPU_API_KEY` | ZhipuAI API key | - |
| `DATABASE_URL` | MySQL connection string | `mysql+aiomysql://...` |
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://localhost:7687` |
| `CHROMA_HOST` | ChromaDB host | `localhost` |
| `SECRET_KEY` | JWT signing key | - |
| `CODE_GRAPH_EMBEDDING_MODEL` | Embedding model | `BAAI/bge-small-zh-v1.5` |
| `RATE_LIMIT_GENERAL` | General rate limit | `100/minute` |
| `RATE_LIMIT_LOGIN` | Login rate limit | `20/minute` |

## Project Structure

```
Smart_Code_Assistant/
├── backend-fastapi/          # Python/FastAPI backend
│   ├── app/
│   │   ├── api/              # Route handlers
│   │   ├── core/             # Config, security, middleware
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business logic
│   │       ├── langchain_glm_service.py  # LLM integration
│   │       ├── conversation_manager.py   # Chat history management
│   │       └── code_graph/               # GraphRAG subsystem
│   ├── alembic/              # Database migrations
│   ├── tests/                # Test suite
│   └── scripts/              # Utility scripts
├── frontend/                 # React/TypeScript frontend
│   └── src/
│       ├── components/       # UI components
│       ├── contexts/         # React contexts (auth, document, toast)
│       ├── hooks/            # Custom hooks
│       ├── pages/            # Page components
│       ├── services/         # API client services
│       └── types/            # TypeScript type definitions
├── backend-dotnet/           # .NET backend (early stage)
├── docker-compose.yml        # Infrastructure services
└── init-scripts/             # Database initialization SQL
```

## License

This project is licensed under the MIT License.
