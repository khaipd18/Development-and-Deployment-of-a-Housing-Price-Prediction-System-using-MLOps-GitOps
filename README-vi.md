*Đọc bằng ngôn ngữ khác: [English](README.md)*
# Development and Deployment of a Housing Price Prediction System using MLOps & GitOps

Dự án xây dựng hệ thống dự đoán giá nhà, triển khai tự động lên AWS EKS thông qua Argo CD theo mô hình MLOps + GitOps.

> **Lưu ý:** Đây là repo GitOps — chỉ chứa cấu hình Kubernetes và Argo CD. Code nguồn, pipeline huấn luyện model, và hạ tầng Terraform nằm ở repo chính:
> 🔗 [Development-and-Deployment-of-a-Housing-Price-Prediction-System-using-MLOps](https://github.com/LeChanhAn/Development-and-Deployment-of-a-Housing-Price-Prediction-System-using-MLOps)

---

## 🌟 1. Điểm nổi bật về kỹ thuật

### 1.1. App of Apps & ApplicationSet

Thay vì tạo thủ công từng ứng dụng trên Argo CD, dự án dùng mẫu **App of Apps** — chỉ cần apply một thư mục gốc (`argocd/root`), hệ thống tự khởi tạo toàn bộ các thành phần còn lại. **ApplicationSet** được dùng thêm để tự động phát hiện và sinh ra môi trường Dev/Prod dựa trên cấu trúc thư mục.

### 1.2. Kustomize kết hợp Helm

Dự án tự xây một **Local Helm Chart** (`standard-microservice`) chứa các template chuẩn cho microservice. Thay vì `helm install` truyền thống, tính năng **`helmCharts` của Kustomize** được dùng để inject values linh hoạt cho từng môi trường (Base → Dev/Prod) — giữ được sức mạnh template của Helm lẫn khả năng overlay của Kustomize.

### 1.3. Canary Deployment với Argo Rollouts (Prod)

Môi trường Production không dùng `Deployment` tiêu chuẩn mà chuyển sang `Rollout`. Khi có version mới, traffic được chuyển dần theo các bước: **20% → chờ 10 phút kiểm tra lỗi → 50% → chờ duyệt thủ công → 100%**.

---

## 📂 2. Cấu trúc thư mục

```text
📦 GitOps-Repository
 ┣ 📂 app                      # Cấu hình triển khai API & UI
 ┃ ┣ 📂 base                   # Cấu hình gốc dùng chung cho mọi môi trường
 ┃ ┃ ┣ 📜 ingress.yaml         # AWS ALB Ingress
 ┃ ┃ ┣ 📂 api & 📂 ui          # values.yaml cơ sở cho Helm chart
 ┃ ┗ 📂 overlays               # Cấu hình ghi đè theo môi trường
 ┃   ┣ 📂 dev                  # Dev: 1 replica, resource thấp
 ┃   ┗ 📂 prod                 # Prod: 3 replicas + kịch bản Canary
 ┣ 📂 argocd
 ┃ ┣ 📂 applications           # ApplicationSet tự tạo app từ thư mục overlays
 ┃ ┣ 📂 infrastructure         # AWS LB Controller, Argo Rollouts
 ┃ ┗ 📂 root                   # App of Apps — điểm khởi động toàn hệ thống
 ┣ 📂 helm-charts
 ┃ ┗ 📂 standard-microservice  # Template chuẩn: Deployment, Service, Ingress, HPA...
 ┗ 📜 README.md
```

---

## 🚀 3. Hướng dẫn bootstrap hệ thống

Sau khi Terraform tạo xong hạ tầng và cụm EKS, làm theo các bước dưới đây.

### Bước 3.1 — Kết nối với EKS Cluster

```bash
aws eks update-kubeconfig --region ap-southeast-1 --name housing-mlops-eks-cluster
```

Kiểm tra và chuyển context nếu cần:

```bash
kubectl config get-contexts
kubectl config use-context <tên-context>
```

---

### Bước 3.2 — Cài Argo CD

```bash
kubectl create namespace argocd

kubectl apply -n argocd --server-side --force-conflicts -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Chờ đến khi tất cả pods chuyển sang `Running`:

```bash
kubectl get pods -n argocd
```

---

### Bước 3.3 — Truy cập Argo CD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Giữ terminal chạy, mở trình duyệt vào: **https://localhost:8080**

- **Username:** `admin`
- **Password:** Chạy lệnh này ở terminal khác:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

---

### Bước 3.4 — Khởi động App of Apps

```bash
kubectl apply -k argocd/root/
```

> **Quan trọng:** Cấu hình root bật `--enable-helm` cho Kustomize. Cần restart Repo Server để Argo CD nhận cấu hình mới:
> ```bash
> kubectl rollout restart deployment argocd-repo-server -n argocd
> ```

---

### Bước 3.5 — Lấy URL ứng dụng (Ingress)

Hệ thống tự cấp phát 2 ALB riêng cho 2 môi trường. Chạy lệnh bên dưới, lấy giá trị cột `ADDRESS` và dán vào trình duyệt:

```bash
# Dev
kubectl get ingress housing-ingress -n housing-dev

# Prod
kubectl get ingress housing-ingress -n housing-prod
```

---

## 🦅 4. Vận hành Canary Deployment (môi trường Prod)

### Bước 4.1 — Cài plugin Argo Rollouts (Linux / WSL)

```bash
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x ./kubectl-argo-rollouts-linux-amd64
sudo mv ./kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts
kubectl argo rollouts version
```

---

### Bước 4.2 — Theo dõi và promote rollout

Khi có image mới push lên nhánh `main`, Argo CD tự triển khai nhưng dừng ở mức 20% traffic. Xem trạng thái theo thời gian thực:

```bash
kubectl argo rollouts get rollout housing-api -n housing-prod --watch
```

Sau khi xác nhận version mới ổn định, promote lên bước tiếp theo:

```bash
kubectl argo rollouts promote housing-api -n housing-prod
```

---

### Bước 4.3 — Mở Rollouts Dashboard (tùy chọn)

```bash
kubectl argo rollouts dashboard -n housing-prod
```

Giữ terminal chạy, mở trình duyệt vào: **http://localhost:3100**

---

## 🧹 5. Hướng dẫn gỡ bỏ hệ thống (Teardown)

Khi muốn dọn dẹp hệ thống để tiết kiệm chi phí, **bạn bắt buộc phải xóa toàn bộ tài nguyên ứng dụng trên Kubernetes (đặc biệt là Ingress) trước khi chạy `terraform destroy` bên repo hạ tầng.**

**Tại sao phải làm vậy?**

> Các ALB trong dự án được tạo tự động bởi **AWS Load Balancer Controller** bên trong EKS, không phải do Terraform quản lý. Nếu chạy `terraform destroy` ngay, Terraform sẽ không xóa được VPC vì các ALB này vẫn đang giữ Network Interface (ENI) trong Subnet.
>
> **Lưu ý:** Không dùng `kubectl delete ingress` thủ công — Argo CD đang bật `selfHeal` và sẽ lập tức tạo lại ALB ngay khi bạn vừa xóa. Cách duy nhất là xóa toàn bộ Application.

**Quy trình dọn dẹp chuẩn (Cascade Delete):**

**1. Gỡ bỏ toàn bộ ứng dụng qua Argo CD (App of Apps):**

Nhờ `finalizers` đã được cấu hình, khi xóa App gốc, Argo CD tự động dọn sạch toàn bộ tài nguyên con — bao gồm cả Ingress và ALB:

```bash
kubectl delete -k argocd/root/
```

**2. Chờ AWS thu hồi Load Balancer:**

Vào AWS Console → EC2 → Load Balancers, đợi khoảng 2–3 phút cho đến khi các ALB của Dev và Prod biến mất hoàn toàn.

**3. Chạy terraform destroy:**

```bash
terraform destroy
```