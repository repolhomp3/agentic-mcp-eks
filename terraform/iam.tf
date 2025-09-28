resource "aws_iam_role" "agentic_pod_role" {
  name = "agentic-pod-role"

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

resource "aws_iam_policy" "agentic_policy" {
  name = "agentic-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:ListFoundationModels",
          "s3:ListAllMyBuckets",
          "s3:GetObject",
          "s3:PutObject",
          "ec2:DescribeRegions",
          "ec2:DescribeInstances",
          "sts:GetCallerIdentity",
          "glue:GetJobs",
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "agentic_policy_attachment" {
  role       = aws_iam_role.agentic_pod_role.name
  policy_arn = aws_iam_policy.agentic_policy.arn
}

resource "aws_eks_pod_identity_association" "agentic_pod_identity" {
  cluster_name    = module.eks.cluster_name
  namespace       = "default"
  service_account = "agentic-service-account"
  role_arn        = aws_iam_role.agentic_pod_role.arn
}