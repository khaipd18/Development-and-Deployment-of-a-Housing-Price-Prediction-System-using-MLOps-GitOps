# Development and Deployment of a Housing Price Prediction System using MLOps & GitOps

Dự án xây dựng hệ thống dự đoán giá nhà, triển khai tự động lên AWS EKS thông qua Argo CD theo mô hình MLOps + GitOps.

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

Apply cấu hình root để Argo CD tự quét và triển khai toàn bộ hệ thống (Controller, Load Balancer, API, UI):

```bash
kubectl apply -k argocd/root/
```