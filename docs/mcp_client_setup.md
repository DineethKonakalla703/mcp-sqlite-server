# MCP Client Integration Guide

This guide details how to integrate the **Natural Language SQLite MCP Server** with MCP-compatible AI clients such as Claude Desktop, Cursor, or the official MCP Inspector.

---

## 1. Environment Setup

### 1.1 Create and Activate a Virtual Environment

#### On Windows (PowerShell):
```powershell
# Navigate to the project root
cd "d:\dineth lakshmi\Documents\projects_\mcp_server_project"

# Create virtual environment with Python 3.11+
py -3.12 -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1
```

*(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

#### On Linux / macOS:
```bash
# Navigate to the project root
cd /path/to/mcp_server_project

# Create virtual environment with Python 3.11+
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

---

### 1.2 Install Dependencies

Install all pinned runtime and testing dependencies:
```bash
pip install -r requirements.txt
```

---

### 1.3 Initialize and Seed the Database

Before running the server, initialize the SQLite schema and seed the initial fictional dataset:

```bash
# Initialize schema (tables, foreign keys, indexes)
python scripts/init_db.py

# Seed initial sample data idempotently
python scripts/seed_db.py
```

*Note: The seed script is idempotent; running it multiple times will not insert duplicate records.*

---

## 2. Locating System Paths

When configuring an MCP client, you must provide the absolute paths to:
1. The Python virtual environment executable.
2. The server script entrypoint.
3. The project working directory.

On this system, the verified paths are:

| Component | Path |
| :--- | :--- |
| **Python Executable** | `D:\dineth lakshmi\Documents\projects_\mcp_server_project\.venv\Scripts\python.exe` |
| **Server Entrypoint** | `D:\dineth lakshmi\Documents\projects_\mcp_server_project\server.py` |
| **Project Directory** | `D:\dineth lakshmi\Documents\projects_\mcp_server_project` |

---

## 3. Configuring Claude Desktop

Claude Desktop connects to local MCP servers via standard input/output (`stdio`).

### 3.1 Configuration File Location

* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
  *(Usually `C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json`)*
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Linux:** `~/.config/Claude/claude_desktop_config.json`

### 3.2 Configuration JSON

Add the server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sqlite-task-manager": {
      "command": "D:\\dineth lakshmi\\Documents\\projects_\\mcp_server_project\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\dineth lakshmi\\Documents\\projects_\\mcp_server_project\\server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

*(On macOS/Linux, replace `command` and `args` with the appropriate POSIX paths to `python3` and `server.py`).*

### 3.3 Restart Claude Desktop

Completely quit and restart Claude Desktop. When restarted, look for the hammer icon (🔨) indicating that the 8 tools are available.

---

## 4. Testing with the MCP Inspector

The official Model Context Protocol Inspector allows developers to inspect tools, prompts, and resources without requiring Claude Desktop:

```bash
npx @modelcontextprotocol/inspector "D:\dineth lakshmi\Documents\projects_\mcp_server_project\.venv\Scripts\python.exe" "D:\dineth lakshmi\Documents\projects_\mcp_server_project\server.py"
```

The inspector will open a browser UI at `http://localhost:5173` where you can:
- List all 8 registered tools.
- Inspect JSON schemas for each parameter.
- Execute tools with custom inputs and view returned JSON-RPC responses.

---

## 5. Natural Language Prompt Examples

Once connected to an AI client, test tool execution using natural language queries:

| Natural Language Request | Target Tool Invoked | Parameter Mapping |
| :--- | :--- | :--- |
| *"Show me all high-priority tasks."* | `list_tasks` | `{"priority": "high"}` |
| *"Find tasks related to Kubernetes."* | `search_tasks` | `{"query": "Kubernetes"}` |
| *"What tasks belong to the Customer Portal project?"* | `get_project_tasks` | `{"project_id": 2}` |
| *"Mark task 2 as completed."* | `update_task_status` | `{"task_id": 2, "status": "completed"}` |
| *"How many tasks are pending or overdue?"* | `get_task_summary` | `{}` |
| *"Create a high-priority task for writing project documentation."* | `create_task` | `{"title": "Write project documentation", "priority": "high"}` |

---

## 6. Troubleshooting Common Issues

### Issue 1: Server fails to start / Claude Desktop shows connection error
* **Cause:** Incorrect Python executable path or missing dependencies.
* **Fix:** Verify you are pointing to `.venv\Scripts\python.exe` and not global Python. Run `python -m pip list` inside `.venv` to verify `mcp` is installed.

### Issue 2: Tool call outputs malformed JSON or times out
* **Cause:** Standard output (`stdout`) contamination. If any code calls `print()` or logs to `sys.stdout`, the JSON-RPC parser breaks.
* **Fix:** The server directs all logging to `sys.stderr` specifically to keep `stdout` pristine for JSON-RPC transport. Verify third-party libraries do not emit unformatted stdout text.

### Issue 3: Database locked error (`sqlite3.OperationalError: database is locked`)
* **Cause:** Multiple concurrent write processes or an uncommitted interactive SQLite shell.
* **Fix:** Close external SQLite GUI tools (DB Browser, SQLite Studio) or verify that timeout is set to at least 10 seconds (as configured in `src/database.py`).
