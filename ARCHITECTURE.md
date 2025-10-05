# Agentic Workflows Platform - Architecture Specification

> **Technical architecture specification for creating detailed architectural drawings and system documentation.**

## System Overview

The Agentic Workflows Platform is a cloud-native, AI-powered orchestration system that combines Model Context Protocol (MCP) servers with intelligent agents to execute autonomous workflows on Amazon EKS.

## High-Level Architecture Layers

### Layer 1: External Access & Load Balancing
- **Internet Gateway**: Public internet access point
- **Application Load Balancer (ALB)**: AWS-managed Layer 7 load balancer
  - **Hostname**: `agentic-dashboard-<random>.us-west-2.elb.amazonaws.com`
  - **Listeners**: HTTP:80 (HTTPS:443 optional)
  - **Target Groups**: EKS worker nodes (IP targets)
  - **Health Checks**: `/health` endpoints on backend services

### Layer 2: Kubernetes Ingress & Routing
- **ALB Ingress Controller**: Kubernetes controller managing ALB configuration
- **Ingress Resource**: `agentic-ingress`
  - **Path Routing**:
    - `/` → Frontend Service (Dashboard UI)
    - `/api` → Agent Core Service (Orchestration API)
  - **Annotations**:
    - `kubernetes.io/ingress.class: alb`
    - `alb.ingress.kubernetes.io/scheme: internet-facing`
    - `alb.ingress.kubernetes.io/target-type: ip`

### Layer 3: Application Services Layer
- **Frontend Service** (`agentic-frontend-service`)
  - **Type**: ClusterIP
  - **Port**: 80 → 80 (container)
  - **Purpose**: Serves interactive dashboard UI
  
- **Agent Core Service** (`agent-core-service`)
  - **Type**: ClusterIP  
  - **Port**: 80 → 8000 (container)
  - **Purpose**: AI orchestration and workflow execution

- **MCP Services** (Internal ClusterIP services)
  - `aws-mcp-service`: Port 80 → 8000
  - `database-mcp-service`: Port 80 → 8000
  - `custom-mcp-service`: Port 80 → 8000

### Layer 4: Container Orchestration (Kubernetes)
- **Default Namespace**: Application services
  - `agentic-frontend`: 1 replica (Nginx + static files)
  - `agent-core`: 2 replicas (Python HTTP server)
  - `aws-mcp`: 1 replica (Python HTTP server)
  - `database-mcp`: 1 replica (Python + SQLite)
  - `custom-mcp`: 1 replica (Python HTTP server)
- **K8s-Admin Namespace**: Cluster management
  - `k8s-mcp`: 1 replica (Python + Kubernetes client)

### Layer 5: Infrastructure Layer (Amazon EKS)
- **EKS Control Plane**: Managed Kubernetes API server
- **Worker Nodes**: EC2 instances in private subnets
- **Node Groups**: 
  - **Managed Node Group**: 2x t3.medium (initial capacity)
  - **Karpenter Nodes**: Dynamic provisioning (t3.medium to t3.xlarge)

## Network Architecture

### VPC Configuration
```
VPC: 10.0.0.0/16 (agentic-cluster-vpc)
├── Availability Zone A (us-west-2a)
│   ├── Public Subnet: 10.0.4.0/20
│   └── Private Subnet: 10.0.0.0/20
├── Availability Zone B (us-west-2b)
│   ├── Public Subnet: 10.0.5.0/20
│   └── Private Subnet: 10.0.1.0/20
└── Availability Zone C (us-west-2c)
    ├── Public Subnet: 10.0.6.0/20
    └── Private Subnet: 10.0.2.0/20
```

### Network Components
- **Internet Gateway**: Attached to VPC for public internet access
- **NAT Gateway**: In public subnet for private subnet outbound access
- **Route Tables**:
  - **Public**: 0.0.0.0/0 → Internet Gateway
  - **Private**: 0.0.0.0/0 → NAT Gateway
- **Security Groups**: EKS-managed + custom rules for ALB

### Subnet Tagging (Critical for AWS Controllers)
```yaml
Public Subnets:
  kubernetes.io/role/elb: "1"
  kubernetes.io/cluster/agentic-cluster: "owned"

Private Subnets:
  kubernetes.io/role/internal-elb: "1"
  kubernetes.io/cluster/agentic-cluster: "owned"
  karpenter.sh/discovery: "agentic-cluster"
  karpenter.k8s.aws/cluster: "agentic-cluster"
```

## Component Architecture

### Agent Core (Orchestration Engine)
```python
# Core Components
├── AgentCore Class
│   ├── Bedrock Client (AI Reasoning)
│   ├── MCP Endpoints Registry
│   ├── Workflow Execution Engine
│   └── Error Handling & Retry Logic
├── AgentHandler Class (HTTP Server)
│   ├── POST /api (Workflow Execution)
│   ├── GET /health (Health Checks)
│   └── OPTIONS (CORS Support)
└── Workflow Types
    ├── AI Reasoning Workflows
    ├── Multi-Step Orchestration
    ├── Error Recovery Workflows
    └── State Management
```

**Key Responsibilities**:
- Receive workflow requests via HTTP API
- Use Amazon Bedrock for AI reasoning and decision making
- Coordinate multiple MCP servers for complex workflows
- Maintain workflow state and handle failures
- Provide structured responses with step-by-step execution details

### MCP Server Architecture
Each MCP server follows standardized protocol:

```python
# MCP Protocol Structure
├── HTTP Server (Port 8000)
├── Request Handler
│   ├── tools/list (Capability Discovery)
│   └── tools/call (Tool Execution)
├── Tool Implementation
│   ├── Input Validation
│   ├── Business Logic
│   └── Response Formatting
└── Health Endpoint (/health)
```

**AWS MCP Server**:
- **Tools**: `list_s3_buckets`, `invoke_bedrock_model`, `list_glue_jobs`, `start_glue_job`, `get_glue_job_status`
- **AWS Clients**: S3, Bedrock Runtime, Glue
- **Authentication**: Pod Identity (credential-less)

**Database MCP Server**:
- **Tools**: `execute_query`, `get_schema`
- **Database**: SQLite with sample data
- **Features**: Parameterized queries, schema introspection

**Custom MCP Server**:
- **Tools**: `get_weather`, `store_data`, `get_data`
- **External APIs**: wttr.in weather service
- **Storage**: In-memory key-value store

**Kubernetes MCP Server**:
- **Tools**: `list_pods`, `scale_deployment`, `get_cluster_status`, `troubleshoot_pod`
- **Kubernetes APIs**: Core V1, Apps V1, Autoscaling V1
- **Authentication**: In-cluster config with RBAC
- **Namespace**: Deployed in `k8s-admin` with ClusterRole permissions

### Frontend Dashboard
```html
# Frontend Architecture
├── Static HTML/CSS/JavaScript
├── API Integration Layer
│   ├── Agent Core API Client
│   ├── Error Handling
│   └── Response Formatting
├── UI Components
│   ├── Workflow Execution Forms
│   ├── Real-time Result Display
│   ├── System Health Monitoring
│   └── Interactive Controls
└── Responsive Design (Mobile-friendly)
```

## Data Flow Architecture

### Workflow Execution Flow
```
1. User Request
   Browser → ALB → Ingress → Agent Core Service

2. AI Reasoning
   Agent Core → Amazon Bedrock → AI Decision

3. Tool Orchestration
   Agent Core → MCP Service(s) → External APIs/Databases

4. Response Assembly
   Agent Core ← MCP Services ← Results
   Agent Core → Bedrock → Analysis/Insights

5. User Response
   Agent Core → Ingress → ALB → Browser
```

### Service-to-Service Communication
```yaml
# Internal Kubernetes Service Mesh
Agent Core:
  - Outbound: aws-mcp-service:80, database-mcp-service:80, custom-mcp-service:80
  - Outbound: k8s-mcp-service.k8s-admin:80
  - Outbound: bedrock-runtime.us-west-2.amazonaws.com:443

MCP Servers:
  - Inbound: Agent Core only
  - Outbound: External APIs (weather, AWS services)
  
Kubernetes MCP:
  - Inbound: Agent Core (cross-namespace)
  - Outbound: Kubernetes API server
  - RBAC: ClusterRole with pod/deployment management

Frontend:
  - Inbound: ALB Ingress only
  - Outbound: None (static content)
```

## Security Architecture

### AWS Security Model
```yaml
Pod Identity Configuration:
  Service Account: agentic-service-account
  IAM Role: agentic-pod-role
  Permissions:
    - bedrock:InvokeModel
    - s3:ListAllMyBuckets, s3:GetObject, s3:PutObject
    - glue:GetJobs, glue:StartJobRun, glue:GetJobRun
    - ec2:DescribeRegions, ec2:DescribeInstances
    - sts:GetCallerIdentity

IRSA (for System Components):
  Karpenter: karpenter-irsa-role
  Load Balancer Controller: load-balancer-controller-irsa-role
```

### Network Security
```yaml
Security Groups:
  EKS Cluster: Managed by EKS
  Worker Nodes: Managed by EKS + custom rules
  ALB: Auto-created by ALB Controller

Network Policies: (Optional - can be added)
  - Deny all by default
  - Allow Agent Core → MCP Services
  - Allow ALB → Frontend/Agent Core
  - Allow MCP → External APIs
```

### Container Security
```yaml
Security Context:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000
  readOnlyRootFilesystem: true (where possible)

Resource Limits:
  CPU: 100m-500m per container
  Memory: 128Mi-512Mi per container
  
Health Checks:
  Liveness Probe: /health endpoint
  Readiness Probe: /health endpoint
  Initial Delay: 5-30 seconds
```

## Scaling Architecture

### Horizontal Pod Autoscaler (HPA)
```yaml
Agent Core HPA:
  Min Replicas: 2
  Max Replicas: 10
  Target CPU: 80%
  Scale Up: 2 pods every 60s
  Scale Down: 1 pod every 300s

MCP Services HPA:
  Min Replicas: 1
  Max Replicas: 5
  Target CPU: 70%
```

### Karpenter Node Provisioning
```yaml
Node Pool Configuration:
  Instance Types: [t3.medium, t3.large, t3.xlarge]
  Capacity Types: [spot, on-demand]
  Architecture: amd64
  OS: linux
  
Provisioning Logic:
  - Bin packing optimization
  - Spot instance preference
  - Automatic right-sizing
  - Fast provisioning (<60s)
  
Deprovisioning:
  - Consolidation after 30s
  - Expiration after 2160h (90 days)
  - Graceful pod eviction
```

### KEDA Event-Driven Autoscaling (Future)
```yaml
Potential Scalers:
  - AWS SQS Queue Length
  - Prometheus Metrics
  - Kafka Consumer Lag
  - Custom HTTP Metrics
```

## Storage Architecture

### Persistent Storage
```yaml
Database MCP:
  Storage Type: EmptyDir (ephemeral)
  Database: SQLite in-memory + file
  Backup: Not implemented (demo setup)
  
Custom MCP:
  Storage Type: In-memory
  Persistence: None (stateless)
  
Future Considerations:
  - EBS volumes for persistent data
  - S3 for backup and archival
  - RDS for production databases
```

### Configuration Storage
```yaml
Kubernetes ConfigMaps:
  - Application configuration
  - Environment variables
  - Feature flags

Kubernetes Secrets:
  - TLS certificates (future)
  - API keys (if needed)
  - Database credentials (if external DB)
```

## Monitoring & Observability Architecture

### Production Monitoring Stack (Deployed)
```yaml
Metrics Server:
  Namespace: kube-system
  Purpose: Resource metrics for HPA/VPA
  Endpoint: Kubernetes metrics API
  
Prometheus Stack:
  Namespace: monitoring
  Components:
    - Prometheus Server (metrics collection)
    - Grafana (visualization dashboard)
    - Node Exporter (system metrics)
    - kube-state-metrics (K8s object metrics)
  Storage: 10Gi persistent volume
  Retention: 7 days
  
Grafana Dashboard:
  Access: LoadBalancer service
  URL: http://<grafana-lb-hostname>
  Credentials: admin / admin123
  Persistence: 5Gi persistent volume
```

### Application Metrics
```yaml
Agent Core Metrics:
  Endpoint: /metrics (Prometheus format)
  Metrics:
    - agent_core_requests_total (counter)
    - agent_core_active_workflows (gauge)
    - agent_core_request_duration (histogram)

ServiceMonitor:
  Namespace: monitoring
  Target: agentic-platform services
  Scrape Interval: 30s
  Path: /metrics
```

### Built-in Health Monitoring
```yaml
Health Checks:
  Endpoint: /health on all services
  Response: HTTP 200 "OK"
  Kubernetes: Liveness + Readiness probes
  ALB Health Checks: /health endpoint

Logging:
  Format: Structured application logs
  Destination: Container stdout/stderr
  Collection: Kubernetes log aggregation
  
Dashboards:
  - Kubernetes cluster overview
  - Application performance metrics
  - AWS service integration status
  - Resource utilization trends
```

## Deployment Architecture

### Infrastructure as Code (Terraform)
```hcl
# Module Structure
├── main.tf (Provider configuration)
├── variables.tf (Input parameters)
├── vpc.tf (Network infrastructure)
├── eks.tf (Kubernetes cluster)
├── iam.tf (Security roles)
├── karpenter.tf (Autoscaling + ALB Controller)
├── addons.tf (Metrics Server + Prometheus/Grafana)
└── outputs.tf (Resource references)

# Monitoring Stack (addons.tf)
├── helm_release.metrics_server
├── helm_release.prometheus (kube-prometheus-stack)
└── Grafana LoadBalancer configuration
```

### Application Deployment (Helm)
```yaml
# Chart Structure
├── Chart.yaml (Metadata)
├── values.yaml (Configuration)
└── templates/
    ├── serviceaccount.yaml
    ├── agent-core.yaml
    ├── aws-mcp.yaml
    ├── database-mcp.yaml
    ├── custom-mcp.yaml
    ├── frontend.yaml
    └── ingress.yaml
```

### Container Build Pipeline
```dockerfile
# Multi-stage builds for optimization
├── Base Image: python:3.11-slim
├── Dependency Installation
├── Application Code Copy
├── Security Hardening
└── Runtime Configuration
```

## Performance Architecture

### Latency Optimization
```yaml
Network:
  - ALB in same region as EKS
  - Private subnets for internal communication
  - Service mesh for optimized routing

Caching:
  - In-memory caching in MCP servers
  - HTTP response caching (future)
  - Database query result caching

Connection Pooling:
  - HTTP keep-alive connections
  - Database connection pooling
  - AWS SDK connection reuse
```

### Throughput Optimization
```yaml
Concurrency:
  - Multi-threaded HTTP servers
  - Async/await patterns (future)
  - Connection pooling

Resource Allocation:
  - CPU limits prevent noisy neighbors
  - Memory limits prevent OOM kills
  - Proper resource requests for scheduling
```

## Disaster Recovery Architecture

### High Availability
```yaml
Multi-AZ Deployment:
  - EKS control plane across 3 AZs
  - Worker nodes distributed across AZs
  - ALB targets in multiple AZs

Pod Distribution:
  - Anti-affinity rules (future)
  - Multiple replicas for critical services
  - Graceful shutdown handling
```

### Backup Strategy (Future)
```yaml
Data Backup:
  - Database snapshots to S3
  - Configuration backup
  - Container image registry backup

Recovery Procedures:
  - Infrastructure recreation via Terraform
  - Application deployment via Helm
  - Data restoration from backups
```

## Integration Architecture

### External Service Integration
```yaml
AWS Services:
  - Amazon Bedrock (AI/ML)
  - Amazon S3 (Storage)
  - AWS Glue (ETL)
  - Amazon EC2 (Compute)

Third-Party APIs:
  - Weather API (wttr.in)
  - Future: Slack, GitHub, etc.

Authentication:
  - Pod Identity for AWS
  - API keys for external services
  - mTLS for service-to-service (future)
```

### API Architecture
```yaml
Agent Core API:
  Protocol: HTTP/1.1 (HTTP/2 future)
  Format: JSON
  Authentication: None (internal)
  Rate Limiting: None (future consideration)

MCP Protocol:
  Standard: Model Context Protocol v1.0
  Transport: HTTP POST
  Format: JSON-RPC 2.0
  Discovery: tools/list method
  Execution: tools/call method
```

This architecture specification provides comprehensive technical details for creating detailed architectural drawings, system documentation, and implementation guides. Each component is designed for scalability, security, and maintainability in production environments.