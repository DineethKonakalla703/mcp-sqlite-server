# Architecture and System Design

## 1. System Overview

The **Natural Language SQLite MCP Server** is a modular Model Context Protocol (MCP) server engineered to provide AI clients (such as Claude Desktop or autonomous agents) with safe, structured, and auditable access to a relational SQLite database.

Rather than exposing raw SQL execution to the AI model, the server implements strict domain-specific MCP tools. This ensures that the AI model acts as a natural language semantic planner while the MCP server enforces application invariants, input constraints, and database security.

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["AI Client Layer"]
        User["User Natural Language Prompt"] --> Client["MCP-Compatible AI Client (e.g. Claude Desktop)"]
        Client --> LLM["LLM (Tool Selection & Argument Formulation)"]
        LLM --> Client
    end

    subgraph ProtocolLayer["Transport & Protocol Layer"]
        Client <-->|"JSON-RPC 2.0 (stdio)"| Stdio["Stdio Transport Channel"]
        Stdio <--> MCPServerCore["MCP Server Core (mcp.server.mcpserver)"]
    end

    subgraph AppLayer["Application & Validation Layer"]
        MCPServerCore --> ToolDispatcher["Tool Dispatcher (server.py)"]
        ToolDispatcher --> ValidationLayer["Validation Layer (src/validation.py & src/models.py)"]
        ValidationLayer --> Tools["Tool Business Logic (src/tools.py)"]
    end

    subgraph DataLayer["Persistence & Database Layer"]
        Tools --> DBAccess["Database Access Layer (src/database.py)"]
        DBAccess -->|"Parameterized Queries / ACID Transactions"| SQLite[("SQLite Database (data/tasks.db)")]
    end
```

---

## 3. Tool Invocation Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Client as Claude Desktop (Client)
    participant Server as server.py (MCP Server)
    participant Val as src/validation.py
    participant DB as src/database.py
    participant SQLite as SQLite Database

    User->>Client: "Find high-priority tasks in progress"
    Client->>Client: Model selects 'list_tasks' with status='in_progress', priority='high'
    Client->>Server: JSON-RPC tools/call {name: "list_tasks", arguments: {...}}
    Server->>Val: validate_status('in_progress'), validate_priority('high')
    Val-->>Server: validated values
    Server->>DB: list_tasks(status='in_progress', priority='high')
    DB->>SQLite: SELECT ... WHERE status = ? AND priority = ?
    SQLite-->>DB: Query Result Rows
    DB-->>Server: Formatted Task Dictionaries
    Server-->>Client: JSON-RPC Result {content: [TextContent(json)]}
    Client-->>User: "Here are the high-priority tasks currently in progress..."
```

---

## 4. Key Architectural Decisions

### 4.1 Strict Domain Tools vs. Arbitrary SQL
* **Decision:** We explicitly avoided exposing an arbitrary `execute_sql` tool.
* **Rationale:** Exposing arbitrary SQL execution creates an insurmountable prompt-injection vector, allowing an attacker or hallucinatory prompt to drop tables, exfiltrate metadata, or tamper with system integrity. Providing explicit domain tools (`list_tasks`, `create_task`, etc.) enforces the principle of least privilege.

### 4.2 Parameterized SQL and Pattern Escaping
* **Decision:** Every database query uses parameter placeholders (`?`). LIKE queries escape literal special characters (`%`, `_`, `\`).
* **Rationale:** Completely neutralizes SQL injection attacks while retaining predictable search semantics.

### 4.3 Stdio Protocol Cleanliness
* **Decision:** All diagnostics and errors are routed exclusively to `sys.stderr`.
* **Rationale:** The MCP stdio transport relies on valid JSON-RPC frames arriving over `sys.stdout`. Emitting `print()` statements or unformatted logs to `stdout` corrupts the transport framing and crashes client connections.

### 4.4 Idempotent Database Operations
* **Decision:** Table creation uses `CREATE TABLE IF NOT EXISTS`, and the database seed utility checks for record uniqueness prior to insertion.
* **Rationale:** Allows environments to run initialization scripts on startup without data duplication or disruption of existing workflows.
