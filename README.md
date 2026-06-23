# Development and Deployment of a Housing Price Prediction System using MLOps & GitOps

Dự án xây dựng hệ thống dự đoán giá nhà, triển khai tự động lên AWS EKS thông qua Argo CD theo mô hình MLOps + GitOps.

> **Lưu ý:** Đây là repo GitOps — chỉ chứa cấu hình Kubernetes và Argo CD. Code nguồn, pipeline huấn luyện model, và hạ tầng Terraform nằm ở repo chính:
> [Development-and-Deployment-of-a-Housing-Price-Prediction-System-using-MLOps](https://github.com/LeChanhAn/Development-and-Deployment-of-a-Housing-Price-Prediction-System-using-MLOps)

---

## 1. Cấu hình Cluster và cài đặt Argo CD

Sau khi Terraform đã tạo xong hạ tầng, làm theo các bước dưới đây để kết nối với cluster và cài Argo CD.

### Bước 1.1 — Cập nhật kubeconfig

Chạy lệnh này để `kubectl` có thể nói chuyện với EKS cluster:

```bash
aws eks update-kubeconfig --region ap-southeast-1 --name housing-mlops-eks-cluster
```

Kiểm tra context hiện tại:

```bash
kubectl config get-contexts
```

Nếu đang có nhiều cluster, chuyển sang đúng context của dự án (thay `<tên-context>` bằng ARN cluster vừa xuất hiện ở trên, ví dụ `arn:aws:eks:ap-southeast-1:770353436964:cluster/housing-mlops-eks-cluster`):

```bash
kubectl config use-context <tên-context>
```

---

### Bước 1.2 — Cài Argo CD

Tạo namespace và cài từ manifest chính thức:

```bash
# Tạo namespace
kubectl create namespace argocd

# Cài đặt
kubectl apply -n argocd --server-side --force-conflicts -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

> Quá trình này tạo các CRD và khởi động pods của Argo CD. Chờ đến khi tất cả pods chuyển sang `Running`:
> ```bash
> kubectl get pods -n argocd
> ```

---

### Bước 1.3 — Mở Argo CD UI

Argo CD không expose ra ngoài theo mặc định. Dùng port-forward để truy cập trên máy local:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Giữ terminal này chạy, rồi mở trình duyệt vào: **https://localhost:8080**

---

### Bước 1.4 — Đăng nhập

- **Username:** `admin`
- **Password:** Lấy từ Kubernetes Secret bằng lệnh sau (chạy ở terminal khác):

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

---

### Bước 1.5 — Khởi tạo Applications

Apply cấu hình root để Argo CD tự quét và triển khai toàn bộ hệ thống (AWS Load Balancer Controller, Argo Rollouts, API, UI):

```bash
kubectl apply -k argocd/root/
```

> **Quan trọng:** Bước trên có thay đổi `argocd-cm` để bật Helm build cho Kustomize. Cần restart Argo CD Repo Server để cấu hình có hiệu lực:
> ```bash
> kubectl rollout restart deployment argocd-repo-server -n argocd
> ```

---

## 2. Canary Deployment với Argo Rollouts (môi trường Prod)

Môi trường `housing-prod` dùng Argo Rollouts để triển khai theo kiểu canary — đẩy traffic dần dần sang version mới thay vì chuyển hẳn một lần. Cần cài plugin `kubectl` để thao tác được.

### Bước 2.1 — Cài plugin (Linux / WSL)

```bash
# Tải binary
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64

# Cấp quyền thực thi
chmod +x ./kubectl-argo-rollouts-linux-amd64

# Chuyển vào PATH
sudo mv ./kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts

# Kiểm tra
kubectl argo rollouts version
```

---

### Bước 2.2 — Theo dõi và promote rollout

Khi có image mới được push lên nhánh `main`, Argo CD sẽ tự triển khai nhưng sẽ dừng lại (Pause) ở từng bước canary theo kịch bản đã cấu hình sẵn.

Xem trạng thái traffic đang chuyển như thế nào:

```bash
kubectl argo rollouts get rollout housing-api -n housing-prod --watch
```

Phê duyệt để tăng % traffic lên bước tiếp theo (hoặc lên 100%):

```bash
kubectl argo rollouts promote housing-api -n housing-prod
```

---

### Bước 2.3 — Mở Rollouts Dashboard

Nếu không muốn dùng CLI, có thể bật dashboard để promote bằng nút bấm:

```bash
kubectl argo rollouts dashboard -n housing-prod
```

Giữ terminal chạy, mở trình duyệt vào: **http://localhost:3100**