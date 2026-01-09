# AIINTIME Agent 🤖

A professional, FastAPI-based AI Agent Gateway built with the **Model Context Protocol (MCP)** and **Google ADK**. This template provides a robust foundation for building intelligent agents that can interact with various MCP-enabled tools and maintain persistent state using Redis.

---

## 🚀 Features

- **MCP Gateway integration**: Seamlessly connect and orchestrate multiple MCP servers.
- **Persistent Memory & Sessions**: Leverages Redis for long-term memory (RAG) and session management.
- **FastAPI Framework**: High-performance REST API for asynchronous chat interactions.
- **Flexible LLM Support**: Powered by `LiteLlm` and `Google ADK`, compatible with numerous model providers.
- **Automated Dependency Management**: Configured with `uv` for lightning-fast and reproducible environments.

---

## 🛠 Tech Stack

- **Runtime**: [Python 3.12+](https://www.python.org/)
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Agent Framework**: [Google ADK](https://github.com/google/adk)
- **LLM Interface**: [LiteLLM](https://github.com/BerriAI/litellm)
- **Database**: [Redis](https://redis.io/) (Session & Memory)
- **Protocol**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

---

## 📥 Getting Started

### Prerequisites

- **Python 3.12** or higher.
- **uv** package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Redis** server running (local or remote).

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd base-template
    ```

2.  **Sync dependencies**:
    ```bash
    uv sync
    ```

### Configuration

Create a `.env` file in the root directory (refer to the existing template). The application uses nested environment variables:

```env
# MCP GATEWAY CONFIG
GATEWAY__NAME="MCP Gateway"
GATEWAY__JSON_RESPONSE=true
GATEWAY__BACKEND_SERVERS='{"server_name": "http://your-mcp-server/mcp"}'

# AGENT CONFIG
AGENT__NAME="AIIntime_Agent"
AGENT__MODEL__NAME="your-model-name"
AGENT__MODEL__BASE_URL="http://your-llm-base-url/v1"
AGENT__MODEL__API_KEY="your-api-key"

# APP CONFIG
APP__NAME="Your_App_Name"
APP__HOST="0.0.0.0"
APP__PORT=9194
```

---

## 🏁 Usage

### Running the Application

Start the FastAPI server using the `uv` environment:

```bash
uv run python main.py
```

The server will be available at `http://0.0.0.0:9194`.

### API Interaction

**Endpoint**: `POST /chat`

```bash
curl -X POST http://localhost:9194/chat \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": "user123",
           "message": "Hello, what tools can you use?"
         }'
```

---

## 📂 Project Structure

```text
├── aiintime_agent/
│   ├── agent/          # Agent logic and MCP gateway tools
│   ├── config/         # Pydantic-based configuration management
│   ├── runner/         # Runner logic for asynchronous task handling
│   └── services/       # Redis-backed session and memory services
├── main.py             # FastAPI entry point
├── pyproject.toml      # Project metadata and dependencies
└── uv.lock             # Locked dependency versions
```

---
