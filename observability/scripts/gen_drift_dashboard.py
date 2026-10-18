"""Sinh ConfigMap dashboard Grafana cho Data Drift (T11).

Chạy:  python3 gen_drift_dashboard.py > observability/grafana-dashboard-housing-drift.yaml

Mọi metric dùng ở đây đều do API phát ra qua DriftCollector, tên đã chốt với Ân.
Giá trị là TOÀN CỤC (mọi pod đọc cùng một file drift/latest.json trên S3), nên dùng
max() để gộp các replica lại thành một chuỗi thay vì vẽ chồng nhiều đường giống nhau.
"""
import json

DS = {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}


def target(expr, legend=None, instant=False):
    t = {"datasource": DS, "expr": expr, "refId": "A"}
    if legend:
        t["legendFormat"] = legend
    if instant:
        t["instant"] = True
    return t


def stat(title, expr, gx, gy, gw, gh, unit=None, mappings=None, steps=None, text_size=36):
    fc = {"unit": unit} if unit else {}
    if mappings:
        fc["mappings"] = mappings
    if steps:
        fc["thresholds"] = {"mode": "absolute", "steps": steps}
    else:
        fc["thresholds"] = {"mode": "absolute", "steps": [{"color": "text", "value": None}]}
    return {
        "type": "stat", "title": title, "datasource": DS,
        "gridPos": {"x": gx, "y": gy, "w": gw, "h": gh},
        "fieldConfig": {"defaults": fc, "overrides": []},
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "background", "graphMode": "none",
            "textMode": "auto", "text": {"valueSize": text_size},
        },
        "targets": [target(expr, instant=True)],
    }


panels = [
    stat(
        "Trạng thái drift", "max(housing_drift_detected)", 0, 0, 6, 5,
        mappings=[{"type": "value", "options": {
            "0": {"text": "Không drift", "color": "green", "index": 0},
            "1": {"text": "CÓ DRIFT", "color": "red", "index": 1}}}],
        steps=[{"color": "green", "value": None}, {"color": "red", "value": 1}],
    ),
    stat(
        "Đo gần nhất cách đây",
        "time() - max(housing_drift_last_detection_timestamp_seconds)",
        6, 0, 6, 5, unit="s",
        steps=[{"color": "green", "value": None},
               {"color": "yellow", "value": 2592000},   # 30 ngày
               {"color": "red", "value": 3888000}],     # 45 ngày
        text_size=28,
    ),
    stat(
        "Feature bị drift",
        "max(housing_drift_features_drifted)", 12, 0, 6, 5,
        steps=[{"color": "green", "value": None}, {"color": "orange", "value": 1}],
    ),
    stat(
        "PSI target (gia_ty)",
        "max(housing_target_drift_psi)", 18, 0, 6, 5,
        steps=[{"color": "green", "value": None},
               {"color": "yellow", "value": 0.1},
               {"color": "red", "value": 0.2}],
    ),
    {
        "type": "timeseries",
        "title": "PSI của target gia_ty theo thời gian (ngưỡng drift = 0,2)",
        "description": ("Đo trên dữ liệu thật: giá tăng 20% -> PSI 0,0755; 35% -> 0,1878; "
                        "50% -> 0,3540. Tức thị trường phải dịch ~35-40% mới chạm ngưỡng."),
        "datasource": DS, "gridPos": {"x": 0, "y": 5, "w": 12, "h": 9},
        "fieldConfig": {"defaults": {
            "custom": {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 10,
                       "showPoints": "auto", "spanNulls": True},
            "min": 0,
            "thresholds": {"mode": "absolute", "steps": [
                {"color": "green", "value": None}, {"color": "red", "value": 0.2}]},
            "custom.thresholdsStyle": {"mode": "line"},
        }, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"},
                    "tooltip": {"mode": "single"}},
        "targets": [target("max(housing_target_drift_psi)", "PSI gia_ty")],
    },
    {
        "type": "bargauge",
        "title": "PSI theo từng feature (ngưỡng 0,2)",
        "datasource": DS, "gridPos": {"x": 12, "y": 5, "w": 12, "h": 9},
        "fieldConfig": {"defaults": {
            "min": 0, "decimals": 4,
            "thresholds": {"mode": "absolute", "steps": [
                {"color": "green", "value": None},
                {"color": "yellow", "value": 0.1},
                {"color": "red", "value": 0.2}]},
        }, "overrides": []},
        "options": {"displayMode": "gradient", "orientation": "horizontal",
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "showUnfilled": True},
        "targets": [target("max by (feature) (housing_drift_feature_psi)", "{{feature}}")],
    },
    {
        "type": "timeseries",
        "title": "Tỷ lệ feature bị drift (ngưỡng dataset drift = 0,3)",
        "datasource": DS, "gridPos": {"x": 0, "y": 14, "w": 24, "h": 7},
        "fieldConfig": {"defaults": {
            "unit": "percentunit", "min": 0, "max": 1,
            "custom": {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 10,
                       "spanNulls": True},
            "thresholds": {"mode": "absolute", "steps": [
                {"color": "green", "value": None}, {"color": "red", "value": 0.3}]},
            "custom.thresholdsStyle": {"mode": "line"},
        }, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"},
                    "tooltip": {"mode": "single"}},
        "targets": [target("max(housing_drifted_features_ratio)", "tỷ lệ feature drift")],
    },
]

dashboard = {
    "uid": "housing-mlops-drift",
    "title": "Housing MLOps — Data Drift",
    "tags": ["housing", "mlops", "T11", "drift"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "1m",
    "time": {"from": "now-7d", "to": "now"},
    "templating": {"list": [{
        "name": "DS_PROMETHEUS", "type": "datasource", "query": "prometheus",
        "current": {}, "hide": 0, "label": "Datasource",
    }]},
    "panels": panels,
}

body = json.dumps(dashboard, ensure_ascii=False, indent=2)
indented = "\n".join("      " + line for line in body.splitlines())

print(f"""# Dashboard Grafana cho Data Drift (T11). Sidecar của kube-prometheus-stack tự nạp
# mọi ConfigMap mang nhãn grafana_dashboard="1".
#
# Metric do DriftCollector trong API phát ra; nó chỉ ĐỌC drift/latest.json trên S3 chứ
# không tự tính drift. Mọi pod đọc cùng một file nên giá trị là toàn cục — dùng max()
# để gộp replica thay vì vẽ chồng nhiều đường giống hệt nhau.
#
# Tách khỏi dashboard API vì hai thứ trả lời hai câu khác nhau: dashboard kia hỏi
# "dịch vụ có khoẻ không", dashboard này hỏi "dữ liệu còn giống lúc train không".
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-housing-drift
  namespace: observability
  labels:
    grafana_dashboard: "1"
data:
  housing-drift.json: |
{indented}""")
