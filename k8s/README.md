# Kubernetes Deployment for Nifty Financial Platform

This directory contains the Kubernetes manifests for deploying the Nifty Financial Platform.

## Prerequisites

- A running Kubernetes cluster.
- `kubectl` configured to communicate with your cluster.
- An Ingress controller (like `nginx-ingress`) installed if you want to use the Ingress.
- Support for `ReadWriteMany` PVCs if you want shared data access across multiple pods.

## Configuration

1. **Secrets**: Update `secrets.yaml` with your actual production passwords and secret keys.
2. **ConfigMap**: Review `configmap.yaml` for environment-specific settings.
3. **Images**: Update the `image` field in `django.yaml`, `celery.yaml` with your actual container image name (e.g., your Docker Hub or ECR repository).

## Deployment Steps

Apply the manifests in the following order:

```bash
# 1. Configuration and Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# 2. Storage
kubectl apply -f postgres.yaml
kubectl apply -f data-pvc.yaml
kubectl apply -f static-media-pvc.yaml

# 3. Cache
kubectl apply -f redis.yaml

# 4. Application
kubectl apply -f django.yaml
kubectl apply -f celery.yaml
kubectl apply -f flower.yaml

# 5. Ingress
kubectl apply -f ingress.yaml
```

## Notes

- **Database**: The PostgreSQL deployment uses a `PersistentVolumeClaim` for data persistence.
- **Shared Data**: The `data-pvc` is mounted to `/app/data` in the Web and Celery pods to share CSV/Excel data. It requires `ReadWriteMany` access mode.
- **Celery Beat**: The beat deployment uses the `Recreate` strategy to ensure only one instance is running at a time.
- **Scaling**: You can scale the `nifty-web` and `celery-worker` deployments by increasing the `replicas` count.
