#!/bin/bash
set -e

REGISTRY="your-registry"  # Update with your ECR or Docker Hub

echo "🏗️ Building agentic platform containers..."

# Build Agent Core
echo "Building agent-core..."
docker build -t ${REGISTRY}/agent-core:latest docker/agent-core/

# Build AWS MCP
echo "Building aws-mcp..."
docker build -t ${REGISTRY}/aws-mcp:latest docker/aws-mcp/

# Build Database MCP
echo "Building database-mcp..."
docker build -t ${REGISTRY}/database-mcp:latest docker/database-mcp/

# Build Custom MCP
echo "Building custom-mcp..."
docker build -t ${REGISTRY}/custom-mcp:latest docker/custom-mcp/

# Build K8s MCP
echo "Building k8s-mcp..."
docker build -t ${REGISTRY}/k8s-mcp:latest docker/k8s-mcp/

# Build Frontend
echo "Building frontend..."
docker build -t ${REGISTRY}/agentic-frontend:latest docker/frontend/

# Push images
echo "📤 Pushing images..."
docker push ${REGISTRY}/agent-core:latest
docker push ${REGISTRY}/aws-mcp:latest
docker push ${REGISTRY}/database-mcp:latest
docker push ${REGISTRY}/custom-mcp:latest
docker push ${REGISTRY}/k8s-mcp:latest
docker push ${REGISTRY}/agentic-frontend:latest

echo "✅ Build complete!"