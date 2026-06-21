# Expense Tracker MCP Server

A production-ready **Model Context Protocol (MCP)** server that lets AI assistants (Claude Desktop, Cursor, VS Code, etc.) manage personal finances — add transactions, analyze spending, track budgets, and generate reports.

---

## Table of Contents

1. [What Is This?](#what-is-this)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Available MCP Tools](#available-mcp-tools)
5. [Local Setup](#local-setup)
6. [Running the Server](#running-the-server)
7. [Connect to Claude Desktop](#connect-to-claude-desktop)
8. [Running Tests](#running-tests)
9. [Docker Deployment (Web/Production)](#docker-deployment-webproduction)
10. [Deploying to a Cloud Server](#deploying-to-a-cloud-server)
11. [Database Migration](#database-migration)
12. [Environment Variables](#environment-variables)
13. [Example Conversations](#example-conversations)

---

## What Is This?

This is an MCP server — a backend that exposes **tools** that any MCP-compatible AI client can call. Think of it as an API layer between your AI assistant and your financial data.

```
You (in Claude) → "I spent ₹450 on lunch"
Claude → calls add_transaction() tool
Server → saves to SQLite/PostgreSQL
Claude → "Added ₹450 under Food → Restaurant"
```

---

## Architecture

```
AI Client (Claude Desktop / Cursor / VS Code)
          │
          │  MCP Protocol (stdio or SSE)
          ▼
    FastMCP Server  (app/server.py)
          │
    ┌─────┴──────┐
    │  Tool Layer │  (app/tools/)       ← thin wrappers, no logic
    └─────┬──────┘
          │
    ┌─────┴──────────┐
    │ Service Layer   │  (app/services/) ← all business logic
    └─────┬──────────┘
          │
    ┌─────┴────────────────┐
    │  Repository Layer     │  (app/repositories/) ← pure DB CRUD
    └─────┬────────────────┘
          │
    ┌─────┴──────┐
    │  Database   │  SQLite (dev) / PostgreSQL (prod)
    └────────────┘
```

**Rule:** Business logic lives only in services. Tools only call services and return results.

---

## Project Structure

```
expense-mcp/
├── app/
│   ├── server.py               # FastMCP entry point — registers all tools/prompts/resources
│   ├── config.py               # Settings from environment variables
│   ├── database/
│   │   ├── models.py           # SQLAlchemy models: Transaction, Category, Subcategory, Budget
│   │   ├── session.py          # Async engine + session factory
│   │   └── base.py             # DeclarativeBase
│   ├── repositories/           # Database CRUD (no business logic)
│   │   ├── transaction_repository.py
│   │   ├── category_repository.py
│   │   └── budget_repository.py
│   ├── services/               # Business logic
│   │   ├── transaction_service.py   # Auto-categorization, CRUD orchestration
│   │   ├── analytics_service.py     # Pandas-based reports and trends
│   │   ├── category_service.py      # Category/subcategory management + seeding
│   │   └── budget_service.py        # Budget tracking and alerts
│   ├── tools/                  # MCP tool definitions (thin wrappers)
│   │   ├── transaction_tools.py
│   │   ├── analytics_tools.py
│   │   ├── category_tools.py
│   │   └── budget_tools.py
│   ├── prompts/
│   │   └── prompts.py          # MCP prompts: analyze_expenses, monthly_review, budget_advisor
│   ├── resources/
│   │   └── resources.py        # MCP resources: expense://categories, etc.
│   └── schemas/
│       └── schemas.py          # Pydantic v2 input/output schemas
├── tests/
│   ├── conftest.py             # Pytest fixtures (in-memory SQLite)
│   ├── test_transactions.py
│   ├── test_analytics.py
│   ├── test_categories.py
│   └── test_budgets.py
├── alembic/                    # Database migrations
├── alembic.ini
├── docker-compose.yml          # App + PostgreSQL
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Available MCP Tools

### Transaction Tools
| Tool | Description |
|---|---|
| `add_transaction` | Add an expense or income with auto-categorization |
| `update_transaction` | Update any field of an existing transaction |
| `delete_transaction` | Delete a transaction by ID |
| `get_transaction` | Retrieve a single transaction |
| `search_transactions` | Filter by date, category, merchant, amount range |
| `bulk_import_transactions` | Import multiple transactions from JSON |
| `suggest_category` | Get AI-powered category suggestion for a description |

### Analytics Tools
| Tool | Description |
|---|---|
| `monthly_summary` | Income, expenses, savings for a month |
| `category_breakdown` | Spending by category for a date range |
| `top_spending_categories` | Ranked list of top N categories |
| `spending_trend` | Month-by-month trend for last N months |
| `merchant_analysis` | Spending grouped by merchant |
| `average_daily_spend` | Average daily spend for a month |
| `income_vs_expense` | Income vs expense comparison |

### Category Tools
| Tool | Description |
|---|---|
| `create_category` | Create a new spending category |
| `list_categories` | List all categories with subcategories |
| `update_category` | Update category name/icon/color |
| `delete_category` | Delete a category |
| `create_subcategory` | Add subcategory under a category |
| `list_subcategories` | List subcategories for a category |

### Budget Tools
| Tool | Description |
|---|---|
| `set_budget` | Set monthly budget for a category |
| `get_budget_status` | Check spending vs budget for current month |
| `get_over_budget_alerts` | Get categories exceeding budget |
| `update_budget` | Update budget amount |
| `delete_budget` | Remove a budget |
| `list_budgets` | List all budgets |

### MCP Prompts
| Prompt | Description |
|---|---|
| `analyze_expenses` | Deep analysis of spending patterns |
| `monthly_review` | Complete monthly financial review |
| `budget_advisor` | Personalized budgeting recommendations |

### MCP Resources
| Resource | Description |
|---|---|
| `expense://categories` | All categories with subcategories |
| `expense://budgets` | All active budgets |
| `expense://monthly-summary` | Current month summary |
| `expense://recent-transactions` | Latest 20 transactions |

---

## Local Setup

### Prerequisites
- Python 3.12+
- pip

### Step 1 — Clone and navigate

```bash
cd expense-mcp
```

### Step 2 — Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

Or install as a package (recommended):

```bash
pip install -e ".[dev]"
```

### Step 4 — Configure environment

```bash
cp .env.example .env
```

For local development, the default `.env` uses SQLite — no additional setup needed:

```env
DATABASE_URL=sqlite+aiosqlite:///./expense.db
API_KEY=your-secret-key
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Running the Server

### Run directly (stdio mode — for MCP clients)

```bash
python -m app.server
```

Or if installed as a package:

```bash
expense-mcp
```

The server runs in **stdio mode** by default — this is how MCP clients (Claude Desktop, Cursor) connect to it.

### Run with MCP CLI (for debugging)

```bash
mcp dev app/server.py
```

This opens the MCP Inspector in your browser where you can test tools interactively.

---

## Connect to Claude Desktop

1. Open Claude Desktop settings → **Developer** → **Edit Config**

2. Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "C:/Users/adrash/Desktop/MCP Expense Tracker/expense-mcp",
      "env": {
        "DATABASE_URL": "sqlite+aiosqlite:///./expense.db"
      }
    }
  }
}
```

> **Tip:** If you used `pip install -e .`, you can simplify `args` to `["expense-mcp"]` and use `"command": "expense-mcp"` directly.

3. Restart Claude Desktop. You should see the Expense Tracker tools in the tool list.

### Connect to Cursor / VS Code

Add to `.cursor/mcp.json` or `.vscode/mcp.json`:

```json
{
  "servers": {
    "expense-tracker": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/path/to/expense-mcp"
    }
  }
}
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_transactions.py -v

# Run a specific test
pytest tests/test_transactions.py::TestAddTransaction::test_add_basic_expense -v
```

Tests use an **in-memory SQLite database** — no setup needed, fully isolated per test.

Expected output:
```
68 passed in ~7s
```

---

## Docker Deployment (Web/Production)

This runs the server with **PostgreSQL** via Docker Compose.

### Step 1 — Set your API key

```bash
# Windows
set API_KEY=your-strong-secret-key

# macOS/Linux
export API_KEY=your-strong-secret-key
```

### Step 2 — Build and start

```bash
docker-compose up --build
```

This starts:
- **app** — the MCP server on port `8000`
- **db** — PostgreSQL 16 on port `5432`

### Step 3 — Verify it's running

```bash
docker-compose ps
docker-compose logs app
```

### Stop the services

```bash
docker-compose down

# Also remove database volume (destructive)
docker-compose down -v
```

### Running in detached mode (background)

```bash
docker-compose up -d --build
```

---

## Deploying to a Cloud Server

### Option A — VPS (Ubuntu/Debian)

```bash
# On your server
sudo apt update && sudo apt install python3.12 python3.12-venv git -y

git clone <your-repo> expense-mcp
cd expense-mcp

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment
cp .env.example .env
nano .env  # set DATABASE_URL to your PostgreSQL URL

# Run with systemd (create /etc/systemd/system/expense-mcp.service)
```

Sample systemd service (`/etc/systemd/system/expense-mcp.service`):

```ini
[Unit]
Description=Expense MCP Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/expense-mcp
ExecStart=/home/ubuntu/expense-mcp/.venv/bin/python -m app.server
Restart=always
EnvironmentFile=/home/ubuntu/expense-mcp/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable expense-mcp
sudo systemctl start expense-mcp
sudo systemctl status expense-mcp
```

### Option B — Docker on Cloud (Railway / Render / Fly.io)

1. Push your code to GitHub
2. Connect the repo to Railway / Render
3. Set environment variables in the dashboard:
   - `DATABASE_URL` — use the platform's PostgreSQL addon URL
   - `API_KEY` — your secret key
   - `ENVIRONMENT=production`
4. The `Dockerfile` is already configured — the platform will detect and use it

### Option C — SSE Mode (HTTP transport for web clients)

To expose the server over HTTP (SSE transport) instead of stdio:

```python
# In app/server.py, change:
mcp.run()

# To:
mcp.run(transport="sse", host="0.0.0.0", port=8000)
```

Then connect remote MCP clients to `http://your-server:8000/sse`.

---

## Database Migration

When you change models, use Alembic to create and apply migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View migration history
alembic history
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./expense.db` | Database connection string |
| `API_KEY` | `""` | API key for authentication (future use) |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Database URL formats

```bash
# SQLite (development)
DATABASE_URL=sqlite+aiosqlite:///./expense.db

# PostgreSQL (production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# PostgreSQL via Docker Compose
DATABASE_URL=postgresql+asyncpg://expense_user:expense_pass@db:5432/expense_db
```

---

## Example Conversations

Once connected to Claude Desktop, you can have these conversations:

**Adding transactions:**
```
You: I spent ₹450 on lunch at a restaurant today
Claude: [calls add_transaction] Added ₹450 under Food → Restaurant
```

**Checking monthly spending:**
```
You: How much did I spend this month?
Claude: [calls monthly_summary] June 2026 — Income: ₹0, Expenses: ₹12,450, Savings: -₹12,450
```

**Budget check:**
```
You: Am I over budget anywhere?
Claude: [calls get_over_budget_alerts] Entertainment is at 110% (₹1,100 over). Food is at 92%.
```

**Category analysis:**
```
You: What are my top 3 spending categories?
Claude: [calls top_spending_categories] 1. Food ₹8,300 (66%), 2. Transport ₹2,800 (22%), 3. Shopping ₹1,350 (11%)
```

**Auto-categorization in action:**
```
You: Paid ₹299 to Swiggy
Claude: [calls add_transaction with merchant="Swiggy"] Auto-categorized as Food → Delivery
```

---

## Auto-Categorization Rules

The server automatically detects category from merchant name or description:

| Keyword | Category | Subcategory |
|---|---|---|
| uber, ola, rapido | Transport | Taxi |
| irctc, train | Transport | Train |
| petrol, diesel, fuel | Transport | Fuel |
| swiggy, zomato, dunzo | Food | Delivery |
| bigbasket, grofers, blinkit | Food | Groceries |
| amazon, flipkart | Shopping | — |
| netflix, spotify | Entertainment | — |
| electricity, wifi | Bills | — |
| hospital, pharmacy, medicine | Healthcare | — |

Priority: Merchant name match (confidence 0.9) > Description keyword match (confidence 0.7) > Default "Other"

---

## Default Categories Seeded on Startup

| Category | Subcategories |
|---|---|
| Food | Restaurant, Groceries, Delivery |
| Transport | Taxi, Fuel, Train |
| Shopping | Clothing, Electronics, Online |
| Entertainment | Movies, Streaming, Events |
| Bills | Electricity, Internet, Rent |
| Healthcare | Doctor, Pharmacy, Insurance |
| Other | — |
