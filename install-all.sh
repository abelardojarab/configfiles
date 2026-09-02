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
# abelardojara-super-server reports 256 CPUs to the container, and
# "worker-processes: auto" (the default) tries to spawn one nginx worker
# per core -- that many workers starved the controller and made every
# request hang. Pin it to a sane number.
kubectl patch configmap ingress-nginx-controller -n ingress-nginx --type merge --patch-file ingress-nginx/configmap-patch.yaml

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

echo "Installing Kubernetes Dashboard..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
kubectl apply -f kubernetes-dashboard/admin-serviceaccount.yaml
kubectl patch deployment kubernetes-dashboard -n kubernetes-dashboard --patch-file kubernetes-dashboard/deployment-patch.yaml
kubectl patch service kubernetes-dashboard -n kubernetes-dashboard --type merge --patch-file kubernetes-dashboard/service-patch.yaml
kubectl -n kubernetes-dashboard rollout status deployment/kubernetes-dashboard --timeout=120s
kubectl apply -f kubernetes-dashboard/ingress.yaml

echo "Done! Run 'kubectl get pods -A' to check the status."
echo ""
echo "Still needed by hand:"
echo "  1. Point k8s.jaraberrocal.readmyblog.org's DNS A record at this host."
echo "  2. sudo nginx -t && sudo systemctl reload nginx   (loads the new upstream/server block)"
echo "  3. sudo certbot --nginx -d k8s.jaraberrocal.readmyblog.org"
echo "  4. ArgoCD initial admin password:"
echo "       kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
echo "  5. Add the 'Kubernetes Dashboard' ProxyProvider/Application to"
echo "     ~/containers/authentik/blueprints/local/portainer.yaml (or wherever"
echo "     your forward-auth blueprint lives) and 'docker exec authentik-worker"
echo "     ak apply_blueprint <path>', then 'docker restart authentik-server'"
echo "     -- the embedded outpost only picked up new provider host mappings"
echo "     after a restart in testing, not from apply_blueprint alone."
echo "  6. Dashboard login token (generate fresh each time, never store it):"
echo "       kubectl create token dashboard-admin -n kubernetes-dashboard --duration=1h"
