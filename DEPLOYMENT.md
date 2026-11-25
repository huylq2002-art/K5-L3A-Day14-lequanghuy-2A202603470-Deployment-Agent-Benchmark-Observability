# Triển khai Day 14

## URL công khai

https://agent-production-78024061.up.railway.app

## Nền tảng

Railway. Service agent triển khai từ thư mục `06-lab-complete/` bằng Dockerfile và [cấu hình Railway](06-lab-complete/railway.toml). Redis được kết nối qua biến môi trường; Railway kiểm tra khởi động bằng `/health`.

## Lệnh kiểm tra

Đặt `AGENT_API_KEY` trong môi trường terminal bằng giá trị trong Railway trước khi chạy lệnh cuối.

```bash
BASE='https://agent-production-78024061.up.railway.app'

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'
```

| Kiểm tra | HTTP | Bằng chứng |
|---|---:|---|
| `GET /health` | 200 | Đã kiểm tra lại từ URL công khai |
| `GET /ready` | 200 | Đã kiểm tra lại từ URL công khai |
| `POST /ask` thiếu API key | 401 | Đã kiểm tra lại từ URL công khai |
| `POST /ask` có API key | 200 | Kết quả xác nhận tại CP6 |

## Biến môi trường

| Tên | Nguồn hoặc vai trò |
|---|---|
| `PORT` | Railway cấp cho service; Dockerfile đọc lúc khởi động |
| `REDIS_URL` | Biến riêng của service, trỏ đến Redis trên Railway |
| `AGENT_API_KEY` | Biến bí mật của service, dùng để xác thực `X-API-Key` |
| `LOG_LEVEL` | Agent mặc định `INFO` khi Railway không đặt biến |

## Ảnh minh chứng

- [Dashboard triển khai Railway](screenshots/dashboard.png)
- [Service Railway đang chạy](screenshots/running.png)
- [Kết quả bốn lệnh kiểm tra HTTP](screenshots/test.png)
