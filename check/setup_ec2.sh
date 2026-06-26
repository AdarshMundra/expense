#!/bin/bash
set -e

# ── Install Python 3.12 and dependencies ──────────────────────────────────
sudo dnf update -y
sudo dnf install -y python3.12 python3.12-pip python3.12-devel gcc libpq-devel git

# ── Create app directory ───────────────────────────────────────────────────
sudo mkdir -p /opt/expense-mcp
sudo chown ec2-user:ec2-user /opt/expense-mcp

# ── Set up Python virtualenv ───────────────────────────────────────────────
cd /opt/expense-mcp
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ── Run Alembic migrations ─────────────────────────────────────────────────
python -m alembic upgrade head

# ── Create systemd service ─────────────────────────────────────────────────
sudo tee /etc/systemd/system/expense-mcp.service > /dev/null <<'EOF'
[Unit]
Description=Expense MCP Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/expense-mcp
EnvironmentFile=/opt/expense-mcp/.env.prod
ExecStart=/opt/expense-mcp/.venv/bin/python -m app.server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable expense-mcp
sudo systemctl start expense-mcp

echo "==> Setup complete! Service status:"
sudo systemctl status expense-mcp --no-pager
