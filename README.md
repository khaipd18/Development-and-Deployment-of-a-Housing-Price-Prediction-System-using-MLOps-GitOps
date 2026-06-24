*Read this in other languages: [Tiếng Việt](README-vi.md)*
# Development and Deployment of a Housing Price Prediction System using MLOps & GitOps

A housing price prediction system deployed automatically to AWS EKS via Argo CD, following MLOps and GitOps principles.

> **Note:** This is the GitOps repository — it only contains Kubernetes and Argo CD configuration. Source code, model training pipelines, and Terraform infrastructure live in the main repo:
> 🔗 [Development-and-Deployment-of-a-Housing-Price-Prediction-System-using-MLOps](https://github.com/LeChanhAn/Development-and-Deployment-of-a-Housing-Price-Prediction-System-using-MLOps)

---

## 🌟 1. Technical Highlights

### 1.1. App of Apps & ApplicationSet

Instead of manually creating each application in Argo CD, the project uses the **App of Apps** pattern — applying a single root directory (`argocd/root`) is enough to bootstrap the entire system. **ApplicationSet** is also used to automatically discover and generate Dev/Prod environments based on the directory structure.

### 1.2. Kustomize + Helm (Hybrid Approach)

The project ships a custom **Local Helm Chart** (`standard-microservice`) with standardized templates for microservices. Rather than using `helm install`, Kustomize's **`helmCharts`** feature injects environment-specific values (Base → Dev/Prod) — combining Helm's templating power with Kustomize's overlay flexibility.

### 1.3. Canary Deployment with Argo Rollouts (Prod)

The Production environment uses `Rollout` instead of a standard Kubernetes `Deployment`. When a new version is released, traffic shifts gradually: **20% → wait 10 min for error check → 50% → manual approval → 100%**.

---

## 📂 2. Repository Structure

```text
📦 GitOps-Repository
 ┣ 📂 app                      # Deployment config for API & UI
 ┃ ┣ 📂 base                   # Shared base config for all environments
 ┃ ┃ ┣ 📜 ingress.yaml         # AWS ALB Ingress
 ┃ ┃ ┣ 📂 api & 📂 ui          # Base values.yaml for Helm chart
 ┃ ┗ 📂 overlays               # Environment-specific overrides
 ┃   ┣ 📂 dev                  # Dev: 1 replica, low resource limits
 ┃   ┗ 📂 prod                 # Prod: 3 replicas + Canary strategy
 ┣ 📂 argocd
 ┃ ┣ 📂 applications           # ApplicationSet — auto-generates apps from overlays
 ┃ ┣ 📂 infrastructure         # AWS LB Controller, Argo Rollouts
 ┃ ┗ 📂 root                   # App of Apps — system bootstrap entry point
 ┣ 📂 helm-charts
 ┃ ┗ 📂 standard-microservice  # Shared template: Deployment, Service, Ingress, HPA...
 ┗ 📜 README.md
```

---

## 🚀 3. Bootstrapping the System

Once Terraform has provisioned the infrastructure and EKS cluster, follow the steps below.

### Step 3.1 — Connect to the EKS Cluster

```bash
aws eks update-kubeconfig --region ap-southeast-1 --name housing-mlops-eks-cluster
```

Check and switch context if needed:

```bash
kubectl config get-contexts
kubectl config use-context <context-name>
```

---

### Step 3.2 — Install Argo CD

```bash
kubectl create namespace argocd

kubectl apply -n argocd --server-side --force-conflicts -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait until all pods are `Running`:

```bash
kubectl get pods -n argocd
```

---

### Step 3.3 — Access the Argo CD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Keep the terminal running and open: **https://localhost:8080**

- **Username:** `admin`
- **Password:** Run this in another terminal:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

---

### Step 3.4 — Trigger the App of Apps

```bash
kubectl apply -k argocd/root/
```

> **Important:** The root config enables `--enable-helm` for Kustomize. Restart the Repo Server so Argo CD picks up the new configuration:
> ```bash
> kubectl rollout restart deployment argocd-repo-server -n argocd
> ```

---

### Step 3.5 — Get the Application URL (Ingress)

The system provisions a separate ALB for each environment. Run the commands below and copy the value from the `ADDRESS` column:

```bash
# Dev
kubectl get ingress housing-ingress -n housing-dev

# Prod
kubectl get ingress housing-ingress -n housing-prod
```

---

## 🦅 4. Operating Canary Deployments (Prod)

### Step 4.1 — Install the Argo Rollouts Plugin (Linux / WSL)

```bash
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x ./kubectl-argo-rollouts-linux-amd64
sudo mv ./kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts
kubectl argo rollouts version
```

---

### Step 4.2 — Monitor and Promote

When a new image is pushed to `main`, Argo CD deploys it automatically but pauses at 20% traffic. Watch the rollout in real time:

```bash
kubectl argo rollouts get rollout housing-api -n housing-prod --watch
```

Once the new version looks stable, promote to the next step:

```bash
kubectl argo rollouts promote housing-api -n housing-prod
```

---

### Step 4.3 — Rollouts Dashboard (Optional)

```bash
kubectl argo rollouts dashboard -n housing-prod
```

Keep the terminal running and open: **http://localhost:3100**

---

## 🧹 5. Teardown

> **Read this before running `terraform destroy`**

When shutting down the system to save costs, **you must remove all Kubernetes application resources (especially Ingresses) before running `terraform destroy` in the infrastructure repo.**

**Why?**

> The ALBs in this project are created automatically by the **AWS Load Balancer Controller** inside EKS — not by Terraform. If you run `terraform destroy` right away, Terraform will fail to delete the VPC because these ALBs are still holding Network Interfaces (ENIs) inside the Subnet.
>
> **Important:** Do not use `kubectl delete ingress` manually — Argo CD has `selfHeal` enabled and will immediately recreate the ALB as soon as you delete it. The only clean way is to delete the Argo CD Applications entirely.

**Correct teardown order (Cascade Delete):**

**1. Remove all applications via Argo CD (App of Apps):**

Thanks to the `finalizers` configured in the root app, deleting it will cause Argo CD to automatically clean up all child resources — including Ingresses and ALBs:

```bash
kubectl delete -k argocd/root/
```

**2. Wait for the ALBs to be fully removed:**

Go to AWS Console → EC2 → Load Balancers and wait 2–3 minutes until the Dev and Prod ALBs disappear.

**3. Run terraform destroy:**

```bash
terraform destroy
```