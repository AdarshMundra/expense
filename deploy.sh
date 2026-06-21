#!/bin/bash
set -e

# ─── Config — fill these in ────────────────────────────────────────────────
AWS_ACCOUNT_ID="YOUR_ACCOUNT_ID"
AWS_REGION="YOUR_REGION"          # e.g. us-east-1
ECR_REPO="expense-mcp"
ECS_CLUSTER="expense-mcp-cluster"
ECS_SERVICE="expense-mcp-service"
# ───────────────────────────────────────────────────────────────────────────

IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"

echo "==> Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "==> Building Docker image..."
docker build -t "$ECR_REPO:latest" .

echo "==> Tagging image..."
docker tag "$ECR_REPO:latest" "$IMAGE_URI"

echo "==> Pushing image to ECR..."
docker push "$IMAGE_URI"

echo "==> Running Alembic migrations..."
# Runs migrations using the same image before updating the service
docker run --rm \
  -e DATABASE_URL="$DATABASE_URL" \
  -e MCP_TRANSPORT="stdio" \
  "$IMAGE_URI" \
  python -m alembic upgrade head

echo "==> Updating ECS service..."
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION"

echo "==> Waiting for deployment to stabilize..."
aws ecs wait services-stable \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION"

echo "==> Deploy complete!"
