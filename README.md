# Cyberpunk DevOps — Kubernetes Deployment







<img width="780" height="309" alt="Screenshot 2026-07-06 at 21 37 36" src="https://github.com/user-attachments/assets/d6ef5f31-d4ca-4175-828a-1f55de27d97a" />









Deployment of the [cyberpunk-devops](https://github.com/AnastasiyaGapochkina01/cyberpunk-devops) application (FastAPI backend + MariaDB) on Kubernetes.

## Status: ✅ Deployed and verified on a real cluster

The project was deployed on a single-node kubeadm cluster (control-plane), with the backend image built and published to Docker Hub: `docker.io/vaiz82/cyberpunk-backend:1.0`.

## Project structure

```
.
├── Dockerfile                        # builds the backend image (api/ + static/)
├── .gitignore
├── README.md
└── k8s/
    ├── 00-namespace.yaml             # namespace "cyberpunk"
    ├── 01-secret-db.yaml             # Secret with DB credentials
    ├── 02-configmap-db-init.yaml     # init.sql for MariaDB (schema + seed data)
    ├── 03-mariadb-statefulset.yaml   # headless Service + StatefulSet + PVC 1Gi (RWO)
    └── 04-backend-deployment.yaml    # Deployment (3 replicas, liveness/readiness) + Service
```

## Environment requirements

- A Kubernetes cluster (minikube / kind / k3s / kubeadm / managed EKS-GKE-AKS)
- `kubectl` configured against the right context
- Docker for building the image
- Access to a container registry (Docker Hub, GHCR, private registry)
- **A StorageClass with a dynamic provisioner.** A bare kubeadm cluster doesn't have one by default — see "Gotchas encountered" below.
- Recommended node size: **2 vCPU / 4 GiB RAM** (managed worker node) or **4 vCPU / 8 GiB RAM** (all-in-one cluster where the control plane and workloads share the same node)

## Step 1. Build and push the backend image

```bash
git clone https://github.com/AnastasiyaGapochkina01/cyberpunk-devops
cd cyberpunk-devops

# copy the Dockerfile from this project into the repo root
cp /path/to/this/project/Dockerfile .

docker build -t <your_dockerhub_username>/cyberpunk-backend:1.0 .
docker push <your_dockerhub_username>/cyberpunk-backend:1.0
```

⚠️ Important: reference the image in the manifest **with a fully-qualified registry name**, e.g. `docker.io/<username>/cyberpunk-backend:1.0`, rather than the short form — on some nodes containerd can resolve short image names against a different default registry (e.g. `quay.io`) instead of Docker Hub, causing `ErrImagePull: unauthorized`.

## Step 2. Set up the DB credentials secret

By default, `k8s/01-secret-db.yaml` contains test passwords. For a real environment, create the Secret imperatively instead of committing passwords to git:

```bash
kubectl create namespace cyberpunk

kubectl create secret generic db-credentials -n cyberpunk \
  --from-literal=DB_HOST=mariadb \
  --from-literal=DB_USER=cyberpunk \
  --from-literal=DB_PASSWORD='SecurePass2025!' \
  --from-literal=DB_NAME=cyberpunk_db \
  --from-literal=MYSQL_ROOT_PASSWORD='RootSecurePass2025!'
```

## Step 3. (Bare kubeadm clusters only) Install a StorageClass provisioner

Managed clusters (EKS/GKE/AKS) and local ones (minikube/kind) already ship with a default StorageClass. A plain kubeadm cluster doesn't — without one, the MariaDB PVC will sit in `Pending` forever. Install `local-path-provisioner`:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

## Step 4. Apply the manifests

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-secret-db.yaml
kubectl apply -f k8s/02-configmap-db-init.yaml
kubectl apply -f k8s/03-mariadb-statefulset.yaml
kubectl apply -f k8s/04-backend-deployment.yaml
```

Or all at once:
```bash
kubectl apply -f k8s/
```

## Verification

```bash
kubectl -n cyberpunk get all
kubectl -n cyberpunk get pvc
kubectl -n cyberpunk get pods -w        # wait until all pods are Running
```

Port-forward and check the app:
```bash
kubectl -n cyberpunk port-forward svc/cyberpunk-backend 8080:80
curl -s localhost:8080/health
curl -s localhost:8080/courses
```

---

## ✅ Goals achieved and how they were proven

### 1. Backend runs with 3 replicas

```bash
kubectl -n cyberpunk get deployment cyberpunk-backend
```
**Result:** `READY 3/3`, `AVAILABLE 3` — all three pods are `Running`, none crashing or restarting.

### 2. Liveness probe implemented for the backend

Configured in `04-backend-deployment.yaml`:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
```
**Verified live:**
```bash
kubectl -n cyberpunk port-forward svc/cyberpunk-backend 8080:80
curl -s localhost:8080/health
# → {"server":"Linux","status":"OK"}
```
`RESTARTS: 0` across all pods for the entire uptime confirms the probe passes consistently (otherwise kubelet would be restarting the containers).

### 3. Database runs as a StatefulSet with a 1Gi PVC, ReadWriteOnce

```bash
kubectl -n cyberpunk get statefulset mariadb
kubectl -n cyberpunk get pvc
```
**Result:**
- `statefulset.apps/mariadb` → `READY 1/1`
- `mariadb-data-mariadb-0` → `STATUS Bound`, `CAPACITY 1Gi`, `ACCESS MODES RWO`

**Verified live** — data is actually written to and persisted in the volume:
```bash
kubectl -n cyberpunk exec -it mariadb-0 -- mysql -ucyberpunk -p'SecurePass2025!' cyberpunk_db -e "SELECT * FROM courses;"
```
Returns the 4 seed rows created by the init script from the ConfigMap on first container start.

Persistence was also confirmed: `mariadb-0` was forcibly deleted and recreated by the StatefulSet — no data was lost, proving state is stored in the PVC and not in the container's ephemeral layer.

### 4. DB connection credentials are sourced from a Secret

```bash
kubectl -n cyberpunk get secret db-credentials
```
The `db-credentials` Secret holds `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `MYSQL_ROOT_PASSWORD`.

- The backend receives its variables via:
  ```yaml
  envFrom:
    - secretRef:
        name: db-credentials
  ```
- The MariaDB StatefulSet receives its variables via individual `secretKeyRef` entries (`MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`).

**Verified live** — an end-to-end test proving the whole chain (Secret → env → application → DB connection) actually works:
```bash
curl -s localhost:8080/courses
```
Returns a JSON payload with real data from MariaDB — meaning the backend successfully connected to the database using credentials sourced entirely from the Secret, with nothing hardcoded in the backend's code or manifests.

---

## Gotchas encountered along the way (useful for a report)

| Issue | Root cause | Fix |
|---|---|---|
| `ErrImagePull` (tried pulling from `quay.io`) | containerd resolved the short image name against a non-Docker-Hub default registry | Used the fully-qualified path `docker.io/vaiz82/cyberpunk-backend:...` in the manifest |
| `ErrImagePull: manifest unknown` | Manifest referenced a nonexistent tag (`latest`), while the image was actually pushed under tag `1.0` | Fixed `image:` to the real tag `docker.io/vaiz82/cyberpunk-backend:1.0` |
| `mariadb-0` stuck in `Pending` forever | No default StorageClass on the bare kubeadm cluster → PVC couldn't bind | Installed `local-path-provisioner`, set it as the default StorageClass, recreated the PVC and pod |
| `curl: command not found` inside the backend pod | Image is based on `python:3.11-slim`, which doesn't ship `curl` | For manual in-pod checks, used `python3 -c "import urllib.request; ..."`, or checked from outside via `port-forward` + `curl` on the host |

## Notes

- Passwords in `01-secret-db.yaml` are for testing only; for production, use an external secret store (Vault, Sealed Secrets, SOPS) or create the Secret imperatively (see Step 2).
- The `02-configmap-db-init.yaml` ConfigMap contains the init SQL that creates the `courses` table with 4 seed rows — these are the exact records visible via `/courses` in the verification above.
- Resource `requests/limits` are set for the backend; the MariaDB StatefulSet should also have limits tuned to your environment's load.





<img width="1540" height="770" alt="Screenshot 2026-07-06 at 21 11 28" src="https://github.com/user-attachments/assets/bd426cb8-3b0a-4ad8-8267-dfd03899538e" />



<img width="1362" height="249" alt="Screenshot 2026-07-06 at 21 12 43" src="https://github.com/user-attachments/assets/e8696dd6-0b57-4c42-937b-309bd2127eb5" />



<img width="1242" height="411" alt="Screenshot 2026-07-06 at 21 15 42" src="https://github.com/user-attachments/assets/f8acdc75-a606-483e-b83c-cf6430ff0b92" />



<img width="1307" height="392" alt="Screenshot 2026-07-06 at 21 16 39" src="https://github.com/user-attachments/assets/b80601db-5830-447f-b5c9-99548eb2352b" />




<img width="1538" height="397" alt="Screenshot 2026-07-06 at 21 18 16" src="https://github.com/user-attachments/assets/d2f928d0-bc20-4dc0-b3e3-914e24ebf588" />




<img width="1564" height="221" alt="Screenshot 2026-07-06 at 21 21 23" src="https://github.com/user-attachments/assets/a378e9bf-253f-4901-a669-20db11fce17d" />




<img width="811" height="802" alt="Screenshot 2026-07-06 at 21 31 30" src="https://github.com/user-attachments/assets/d02eba95-4ed8-467b-b155-96350bb45257" />





<img width="1552" height="680" alt="Screenshot 2026-07-06 at 21 10 57" src="https://github.com/user-attachments/assets/cc08fd25-3617-4133-a9cd-830b3e41a75e" />

