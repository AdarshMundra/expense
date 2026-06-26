# EC2 Deployment Guide — Expense MCP Server

## What's already done
- Neon PostgreSQL database created + all tables migrated
- AWS ECR repository created
- AWS Secrets Manager secrets stored
- EC2 instance launched: `13.212.227.57`
- Security group open on ports 22 (SSH) and 8000 (MCP)
- SSH key saved at: `C:\Users\adrash\Desktop\expense-mcp-key.pem`

---

## Step 1 — Fix SSH Key Permissions
Open **PowerShell** and run:
```powershell
icacls "C:\Users\adrash\Desktop\expense-mcp-key.pem" /inheritance:r
icacls "C:\Users\adrash\Desktop\expense-mcp-key.pem" /grant:r "$env:USERNAME:(R)"
```

---

## Step 2 — Copy Project Files to EC2
In **PowerShell**, from any directory:
```powershell
scp -i "C:\Users\adrash\Desktop\expense-mcp-key.pem" -r "C:\Users\adrash\Desktop\MCP Expense Tracker\expense-mcp" ec2-user@13.212.227.57:/opt/expense-mcp
```

---

## Step 3 — SSH Into the Instance
```powershell
ssh -i "C:\Users\adrash\Desktop\expense-mcp-key.pem" ec2-user@13.212.227.57
```

---

## Step 4 — Install Python and System Dependencies
Run on the EC2 instance:
```bash
sudo dnf update -y
sudo dnf install -y python3.12 python3.12-pip python3.12-devel gcc libpq-devel
```

Verify:
```bash
python3.12 --version
```

---

## Step 5 — Set Up Python Virtual Environment
```bash
cd /opt/expense-mcp
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 6 — Create Production Environment File
```bash
cat > /opt/expense-mcp/.env.prod << 'EOF'
DATABASE_URL=postgresql+asyncpg://neondb_owner:npg_emENPQOx7M9C@ep-odd-sound-aouw81vi-pooler.c-2.ap-southeast-1.aws.neon.tech/Expense?sslmode=require
API_KEY=bf8679bcba75105138ba21d0988a544392cfc0e496d6276a8ebd28981c73ab4e
ENVIRONMENT=production
LOG_LEVEL=INFO
MCP_TRANSPORT=sse
PORT=8000
HOST=0.0.0.0
EOF
```

---

## Step 7 — Run Database Migrations
```bash
cd /opt/expense-mcp
source .venv/bin/activate
export $(cat .env.prod | xargs)
python -m alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

---

## Step 8 — Create Systemd Service (Auto-start on Reboot)
```bash
sudo tee /etc/systemd/system/expense-mcp.service > /dev/null << 'EOF'
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
```

---

## Step 9 — Verify the Server is Running
```bash
# Check service status
sudo systemctl status expense-mcp

# Watch live logs
sudo journalctl -u expense-mcp -f

# Test the SSE endpoint
curl http://localhost:8000/sse
```

You should see the service as `active (running)` and logs like:
```
Starting Expense MCP server...
Database initialized.
Default categories seeded.
```

---

## Step 10 — Configure Claude to Use the Remote MCP Server

Open your Claude Desktop config file:
- **Windows**: `C:\Users\adrash\AppData\Roaming\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Replace your existing expense-mcp entry with:
```json
{
  "mcpServers": {
    "expense-tracker": {
      "transport": {
        "type": "sse",
        "url": "http://13.212.227.57:8000/sse"
      }
    }
  }
}
```

Restart Claude Desktop. The MCP server icon should appear connected.

---

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u expense-mcp -n 50 --no-pager
```

### Port 8000 not reachable
```bash
# Check the process is listening
ss -tlnp | grep 8000
```

### Restart the service after any code change
```bash
sudo systemctl restart expense-mcp
sudo systemctl status expense-mcp
```

### Re-deploy updated code (from your Windows machine)
```powershell
scp -i "C:\Users\adrash\Desktop\expense-mcp-key.pem" -r "C:\Users\adrash\Desktop\MCP Expense Tracker\expense-mcp\app" ec2-user@13.212.227.57:/opt/expense-mcp/
ssh -i "C:\Users\adrash\Desktop\expense-mcp-key.pem" ec2-user@13.212.227.57 "sudo systemctl restart expense-mcp"
```

---

## Summary of Resources

| Resource         | Value                                              |
|------------------|----------------------------------------------------|
| EC2 Instance     | `13.212.227.57` (ap-southeast-1)                   |
| EC2 Instance ID  | `i-03fe7b1e5110dba3d`                              |
| SSH Key          | `C:\Users\adrash\Desktop\expense-mcp-key.pem`      |
| MCP Server URL   | `http://13.212.227.57:8000/sse`                    |
| Database         | Neon PostgreSQL (ap-southeast-1)                   |
| ECR Repo         | `031788956343.dkr.ecr.ap-southeast-1.amazonaws.com/expense-mcp` |
