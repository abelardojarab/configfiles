#!/bin/bash
# Bootstraps ingress-nginx + cert-manager + ArgoCD on the bare-metal
# kubeadm cluster, wired so host nginx (nginx/default) can front them the
# same way it fronts docker-registry: host nginx terminates TLS via
# Certbot and reverse-proxies plain HTTP to a fixed NodePort.
set -euo pipefail

echo "Installing NGINX Ingress Controller (bare-metal provider)..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/baremetal/deploy.yaml
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=180s
kubectl patch svc ingress-nginx-controller -n ingress-nginx --patch-file ingress-nginx/nodeport-patch.yaml

echo "Installing Cert-Manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml
kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=180s
kubectl apply -f cert-manager/cluster-issuer.yaml

echo "Installing ArgoCD..."
kubectl create namespace argocd || true
# --server-side avoids "metadata.annotations: Too long" on the
# applicationsets.argoproj.io CRD (its schema exceeds the 262144-byte
# limit of the client-side last-applied-configuration annotation).
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml --server-side --force-conflicts
kubectl -n argocd rollout status deployment/argocd-server --timeout=180s
kubectl patch configmap argocd-cmd-params-cm -n argocd --type merge --patch-file argocd/argocd-cmd-params-patch.yaml
kubectl rollout restart deployment argocd-server -n argocd
kubectl apply -f argocd/ingress.yaml

echo "Done! Run 'kubectl get pods -A' to check the status."
echo ""
echo "Still needed by hand:"
echo "  1. Point k8s.jaraberrocal.readmyblog.org's DNS A record at this host."
echo "  2. sudo nginx -t && sudo systemctl reload nginx   (loads the new upstream/server block)"
echo "  3. sudo certbot --nginx -d k8s.jaraberrocal.readmyblog.org"
echo "  4. ArgoCD initial admin password:"
echo "       kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
