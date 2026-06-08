#!/usr/bin/env bash
# ReqCheck Docker 启动（UniPortal 双数据源：共享卷 + 私有 bind mount）
# 前置：docker volume create uniportal_storage（或由 UniPortal compose 先创建）
set -euo pipefail

cd "$(dirname "$0")"

docker rm -f reqcheck_container 2>/dev/null || true

IMAGE="${IMAGE:-reqcheck:latest}"

docker run -d -p 5000:5000 \
  -v uniportal_storage:/data/uniportal \
  -v "$(pwd)/local_workspaces:/app/local_workspaces" \
  -e UNIPORTAL_STORAGE_PATH=/data/uniportal \
  -e LOCAL_WORKSPACES_DIR=/app/local_workspaces \
  --name reqcheck_container \
  --restart=always \
  "$IMAGE"

echo "ReqCheck 已启动: http://localhost:5000"
echo "验证: docker exec reqcheck_container python scripts/verify_uniportal_integration.py"
