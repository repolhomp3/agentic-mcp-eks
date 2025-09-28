module "karpenter" {
  source = "terraform-aws-modules/eks/aws//modules/karpenter"

  cluster_name = module.eks.cluster_name

  enable_irsa                     = true
  irsa_oidc_provider_arn         = module.eks.oidc_provider_arn
  irsa_namespace_service_account = "karpenter:karpenter"

  create_pod_identity_association = false

  node_iam_role_additional_policies = {
    AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}

resource "helm_release" "karpenter" {
  namespace        = "karpenter"
  create_namespace = true

  name       = "karpenter"
  repository = "oci://public.ecr.aws/karpenter"
  chart      = "karpenter"
  version    = "1.0.1"

  values = [
    <<-EOT
    settings:
      clusterName: ${module.eks.cluster_name}
      clusterEndpoint: ${module.eks.cluster_endpoint}
      interruptionQueue: ${module.karpenter.queue_name}
    EOT
  ]

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "helm_release" "aws_load_balancer_controller" {
  namespace        = "kube-system"
  create_namespace = false

  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "1.8.1"

  values = [
    <<-EOT
    clusterName: ${module.eks.cluster_name}
    serviceAccount:
      create: true
      name: aws-load-balancer-controller
      annotations:
        eks.amazonaws.com/role-arn: ${module.load_balancer_controller_irsa_role.iam_role_arn}
    region: ${var.region}
    vpcId: ${module.vpc.vpc_id}
    EOT
  ]

  depends_on = [
    module.eks.eks_managed_node_groups,
    module.load_balancer_controller_irsa_role
  ]
}

resource "kubectl_manifest" "karpenter_node_class" {
  yaml_body = <<-YAML
    apiVersion: karpenter.k8s.aws/v1beta1
    kind: EC2NodeClass
    metadata:
      name: default
    spec:
      amiFamily: AL2
      subnetSelectorTerms:
        - tags:
            karpenter.sh/discovery: "${local.cluster_name}"
      securityGroupSelectorTerms:
        - tags:
            karpenter.sh/discovery: "${local.cluster_name}"
      role: "${module.karpenter.node_instance_profile_name}"
      instanceStorePolicy: RAID0
      userData: |
        #!/bin/bash
        /etc/eks/bootstrap.sh ${local.cluster_name}
  YAML

  depends_on = [
    helm_release.karpenter
  ]
}

resource "kubectl_manifest" "karpenter_node_pool" {
  yaml_body = <<-YAML
    apiVersion: karpenter.sh/v1beta1
    kind: NodePool
    metadata:
      name: default
    spec:
      template:
        spec:
          requirements:
            - key: kubernetes.io/arch
              operator: In
              values: ["amd64"]
            - key: kubernetes.io/os
              operator: In
              values: ["linux"]
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot", "on-demand"]
            - key: node.kubernetes.io/instance-type
              operator: In
              values: ["t3.medium", "t3.large", "t3.xlarge"]
          nodeClassRef:
            apiVersion: karpenter.k8s.aws/v1beta1
            kind: EC2NodeClass
            name: default
          # No taints for general workloads
      limits:
        cpu: 1000
      disruption:
        consolidationPolicy: WhenUnderutilized
        consolidateAfter: 30s
        expireAfter: 2160h
  YAML

  depends_on = [
    kubectl_manifest.karpenter_node_class
  ]
}