#!/bin/bash
set -e

echo "🚀 Deploying Agentic Workflows Platform..."

# Build containers
echo "📦 Building containers..."
./build.sh

# Deploy infrastructure
echo "🏗️ Deploying infrastructure..."
cd terraform
terraform init
terraform apply -auto-approve
cd ..

# Update kubeconfig
echo "⚙️ Configuring kubectl..."
aws eks update-kubeconfig --region us-west-2 --name agentic-cluster

# Wait for cluster
echo "⏳ Waiting for cluster..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Deploy applications
echo "🚀 Deploying applications..."
cd helm
ACCOUNT_ID=$(terraform -chdir=../terraform output -raw account_id)
helm install agentic-platform ./agentic-platform --set awsAccountId=$ACCOUNT_ID
cd ..

# Get URLs
echo "✅ Deployment complete!"
echo "Dashboard URL:"
kubectl get ingress agentic-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
echo ""
echo "Access your dashboard at: http://$(kubectl get ingress agentic-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
echo ""
echo "📊 Monitoring Stack:"
echo "Grafana URL (may take 2-3 minutes to provision):"
kubectl get svc -n monitoring prometheus-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "LoadBalancer provisioning..."
echo ""
echo "Grafana credentials: admin / admin123"
echo ""