#!/bin/bash
set -e

EC2_HOST="13.212.227.57"
EC2_USER="ec2-user"
KEY_PATH="$HOME/Desktop/expense-mcp-key.pem"
APP_DIR="/opt/expense-mcp"

echo "==> Copying app files to EC2..."
rsync -avz --exclude '.venv' --exclude '*.db' --exclude '__pycache__' \
  -e "ssh -i $KEY_PATH -o StrictHostKeyChecking=no" \
  . "$EC2_USER@$EC2_HOST:$APP_DIR/"

echo "==> Restarting service..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" \
  "cd $APP_DIR && source .venv/bin/activate && python -m alembic upgrade head && sudo systemctl restart expense-mcp"

echo "==> Deploy complete!"
