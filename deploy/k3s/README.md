# Kubernetes / k3s Upgrade Path

This directory outlines the future k3s containerized pod layout for scaling the Prompt Brain control plane.

## Deploying to k3s
1. **Namespace**: Apply `namespace.yaml`.
2. **Secrets**: Update `secret-template.yaml` with your base64 encoded credentials.
3. **PVC**: Deploy `pvc-evidence.yaml` to request a shared storage mount.
4. **Deployments**: Execute `kubectl apply -f .`
