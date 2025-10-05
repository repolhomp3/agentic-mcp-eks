# Kubernetes MCP RBAC Configuration
resource "aws_iam_role" "k8s_mcp_role" {
  name = "k8s-mcp-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "k8s_mcp_policy" {
  name = "k8s-mcp-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "k8s_mcp_policy_attachment" {
  role       = aws_iam_role.k8s_mcp_role.name
  policy_arn = aws_iam_policy.k8s_mcp_policy.arn
}

resource "aws_eks_pod_identity_association" "k8s_mcp_pod_identity" {
  cluster_name    = module.eks.cluster_name
  namespace       = "k8s-admin"
  service_account = "k8s-mcp-service-account"
  role_arn        = aws_iam_role.k8s_mcp_role.arn
}