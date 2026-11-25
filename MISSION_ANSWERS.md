# Day 14 Lab – Mission Answers

## Part 1 – Localhost và production

### Exercise 1.1 – Anti-pattern trong bản develop

1. API key nằm trong mã nguồn. Đưa một key thật vào vị trí đó sẽ lưu nó trong lịch sử Git.
2. Chuỗi kết nối cơ sở dữ liệu chứa thông tin đăng nhập và cố định `localhost`. Cơ sở dữ liệu của container khác cần địa chỉ riêng.
3. `DEBUG = True` và `reload=True` được đặt cố định. Tự reload phù hợp khi sửa code cục bộ, còn production cần cấu hình ổn định.
4. Route dùng `print()` và in cả API key. Log cần định dạng nhất quán và lọc dữ liệu nhạy cảm.
5. Bản develop thiếu `/health` và `/ready`. Điều phối viên thiếu tín hiệu để quyết định restart process hoặc ngừng chuyển traffic.
6. Host `localhost` và port `8000` nằm trong code. Bên ngoài container không thể đến loopback của container, và nền tảng có thể cấp port khác.
7. App thiếu lifecycle để dọn tài nguyên khi dừng. Thoát đột ngột có thể cắt ngang request.

### Exercise 1.2 – Chạy bản develop

`POST /ask?question=Hello` nhận kết quả sau.

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:41:22 GMT
server: uvicorn
content-length: 103
content-type: application/json

{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

### Exercise 1.3 – So sánh hai phiên bản

| Mục | Develop | Production | Tác dụng |
|---|---|---|---|
| Cấu hình | Giá trị đặt trong source | `config.py` đọc biến môi trường và kiểm tra cấu hình | Cùng code có thể chạy ở các môi trường khác nhau |
| Network | Host và port cố định | `HOST`, `PORT`, mặc định bind `0.0.0.0` | Nền tảng điều phối được kết nối tới app |
| Health | Chỉ có route thông thường | `/health` báo tiến trình còn sống, `/ready` báo khả năng nhận traffic | Quyết định restart và dừng route dựa trên hai tín hiệu riêng |
| Log | In câu hỏi và key bằng `print` | Logger JSON ghi độ dài câu hỏi và câu trả lời | Có thể lọc theo trường và tránh lộ key |
| Shutdown | Thiếu lifecycle ứng dụng | FastAPI lifespan quản lý khởi động và dọn dẹp. Uvicorn điều phối request đang chạy | Giảm lỗi khi cập nhật hoặc dừng container |
| Input | Query `question` | JSON `question`, trả 422 khi thiếu | Hợp đồng gọi API rõ hơn |

Develop cố định key và debug trong source. Production đọc các giá trị này từ môi trường. Bản production đã trả `200` cho `/health`, `/ready` và `POST /ask` với JSON hợp lệ. [develop/app.py, dòng 15](01-localhost-vs-production/develop/app.py#L15), [production/config.py, dòng 18](01-localhost-vs-production/production/config.py#L18)

## Part 2 – Docker

### Exercise 2.1 – Dockerfile cơ bản

1. Base image là `python:3.11`.
2. Working directory là `/app`.
3. Copy `requirements.txt` và cài thư viện trước khi copy code giúp tái sử dụng layer cài thư viện khi chỉ sửa code.
4. `ENTRYPOINT` xác định lệnh chính của container. `CMD` cung cấp lệnh mặc định khi không có `ENTRYPOINT`, hoặc cung cấp tham số mặc định cho `ENTRYPOINT`. Đối số truyền bằng `docker run` có thể thay các mặc định đó.

### Exercise 2.2 – Build và chạy develop

Build context là thư mục gốc. Cả `/health` và `/ask?question=Hello` đều trả `200`.

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:45:20 GMT
server: uvicorn
content-length: 53
content-type: application/json

{"status":"ok","uptime_seconds":0.7,"container":true}
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:45:20 GMT
server: uvicorn
content-length: 95
content-type: application/json

{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 2.3 – Đo kích thước image

| Image | `docker images` | `docker image inspect .Size` |
|---|---:|---:|
| Develop | 1.67 GB | 426,319,958 byte (426.32 MB) |
| Production | 239 MB | 57,248,669 byte (57.25 MB) |

Ảnh production nhỏ hơn 86.57% theo số byte `.Size`. Bảng giữ cả hai số đo theo đúng cách Docker hiển thị.

Stage builder dùng compiler và cài thư viện. Stage runtime dùng `python:3.11-slim`, chỉ copy thư viện đã cài và source cần chạy, rồi chạy bằng user thường.

### Exercise 2.4 – Compose và Nginx

```text
Client → Nginx → agent
                  ├─ Redis
                  └─ Qdrant
```

Nginx công bố cổng HTTP, chuyển request vào mạng nội bộ và giới hạn tốc độ theo IP. Compose cấu hình agent, Redis và Qdrant trên cùng mạng. Agent mẫu trả lời bằng mock. Hai lần curl qua Nginx đều nhận `200`.

```text
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 09:50:39 GMT
Content-Type: application/json
Content-Length: 95
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"status":"ok","uptime_seconds":4.5,"version":"2.0.0","timestamp":"2026-11-25T09:50:39.719750"}
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 09:50:41 GMT
Content-Type: application/json
Content-Length: 126
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

## Part 3 – Triển khai cloud

### Exercise 3.1 – Railway

URL của agent Part 6 là <https://agent-production-78024061.up.railway.app>. Kết quả công khai kiểm tra lại là `200 / 200 / 401`. Lần gọi có key đã được xác nhận `200` tại CP6. [Lệnh xác thực](DEPLOYMENT.md), [Ảnh minh chứng](screenshots/)

### Exercise 3.2 – So sánh Railway và Render

| Mục | Railway Part 6 | Blueprint Render mẫu |
|---|---|---|
| Định dạng | TOML theo các mục `[build]` và `[deploy]` | YAML với danh sách `services` có thể khai báo nhiều dịch vụ |
| Build và start | Builder `DOCKERFILE` với lệnh trong image đọc `PORT` | Dịch vụ `type: web` với `runtime: python` đặt riêng `buildCommand` và `startCommand` |
| Redis và secret | Redis là service trên Railway, ứng dụng nhận `REDIS_URL` và key qua biến môi trường | Blueprint mẫu có mục Redis và `envVars`. Dùng `sync: false` để đặt ngoài Git, hoặc `generateValue` để sinh key. Khi dùng cho Part 6 cần nối URL Redis vào service web |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |

Blueprint mẫu nằm ở [03-cloud-deployment/render/render.yaml](03-cloud-deployment/render/render.yaml).

### Exercise 3.3 – Cloud Run

1. Cloud Build cài dependency và gọi `pytest` trong môi trường Python 3.11.
2. Docker build hai tag `$COMMIT_SHA` và `latest`, dùng cache từ `latest` nếu sẵn có, rồi push cả hai lên registry.
3. Sau bước push, `gcloud run deploy` triển khai tag theo commit vào Cloud Run managed tại `asia-southeast1`, với biến môi trường và tham chiếu Secret Manager.
4. `service.yaml` mô tả service khai báo với cổng 8000, 1–10 instance, concurrency 80, cùng probe `/health` và `/ready`.

## Part 4 – API Security

### Exercise 4.1–4.3 – API key, JWT và rate limit

Bản develop nhận API key qua `X-API-Key`. Bản production của Part 4 cấp JWT từ `POST /auth/token`, rồi nhận qua `Authorization: Bearer [ĐÃ CHE]`. JWT mang danh tính, quyền và thời hạn. Server kiểm tra chữ ký và thời hạn trước khi chấp nhận token.

Thiếu API key.

```text
HTTP/1.1 401 Unauthorized
date: Wed, 25 Nov 2026 09:41:25 GMT
server: uvicorn
content-length: 67
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

API key đúng.

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:41:25 GMT
server: uvicorn
content-length: 132
content-type: application/json

{"question":"What is Docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

Key sai ở demo Part 4 trả 403.

```text
HTTP/1.1 403 Forbidden
date: Wed, 25 Nov 2026 09:41:25 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"detail":"Invalid API key."}
```

JWT nhận được từ endpoint đăng nhập, đã che cả token và phần gợi ý.

```json
{"access_token": "[ĐÃ CHE]", "token_type": "bearer", "expires_in_minutes": 60, "hint": "Authorization: Bearer [ĐÃ CHE]"}
```

Request đầu tiên có JWT hợp lệ.

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:41:29 GMT
server: uvicorn
content-length: 196
content-type: application/json
vary: Origin
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"question":"What is Docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```

Request thứ 11 cùng JWT.

```text
HTTP/1.1 429 Too Many Requests
date: Wed, 25 Nov 2026 09:41:30 GMT
server: uvicorn
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795599751
retry-after: 59
content-length: 98
content-type: application/json
vary: Origin
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

Chuỗi mã HTTP trong vòng lặp là `200 200 200 200 200 200 200 200 200 200 429`.

### Exercise 4.4 – Cost guard

Tính riêng input và output theo số token chia 1.000 rồi nhân đơn giá tương ứng. Cộng tiền theo user và theo kỳ, kiểm tra ngân sách trước khi gọi LLM rồi ghi nhận chi phí sau lần gọi. Demo Part 4 cảnh báo ở 80% ngân sách user, trả `402` khi user hết ngân sách và trả `503` khi chạm trần toàn hệ thống. Khi chạy nhiều worker, bộ đếm dùng chung phải nằm ở Redis hoặc cơ sở dữ liệu. Rate limit bảo vệ thông lượng trong cửa sổ ngắn, cost guard bảo vệ ngân sách dù các request phân bố đều.

## Part 5 – Scaling và độ tin cậy

### Exercise 5.1 – Health và readiness

`/health` trả trạng thái tiến trình. `/ready` kiểm tra app đã sẵn sàng và có thể kết nối Redis. Khi mất Redis, router có thể loại instance khỏi luồng request dựa vào `503` của readiness, trong khi liveness vẫn trả `200`.

### Exercise 5.2 – Graceful shutdown

Uvicorn nhận SIGTERM, ngừng nhận kết nối mới, đợi request đang xử lý hoàn thành, rồi chạy phần cleanup trong lifespan. Kết quả kiểm tra SIGTERM có request đang chạy được ghi ở Part 6.

### Exercise 5.3–5.5 – Stateless, Nginx và kiểm tra khi scale

Nginx phân phối `POST /chat` giữa các replica. Cùng một `session_id` được đọc và cập nhật từ Redis, nên request tiếp theo có thể sang replica khác và vẫn thấy lịch sử. Với bộ nhớ riêng của từng process, các replica sẽ thấy các phần lịch sử khác nhau và restart sẽ làm mất phần lưu cục bộ.

```text
Request 1: [instance-8fcb09]
Request 2: [instance-689618]
Request 3: [instance-4a33bb]
Request 4: [instance-8fcb09]
Request 5: [instance-689618]
Total requests: 5
Instances used: {'instance-689618', 'instance-4a33bb', 'instance-8fcb09'}
Total messages: 10
✅ Session history preserved across all instances via Redis!
```

`test_stateless.py` chạy trên stack 3 replica qua Nginx ở cổng 8080. Lịch sử có 5 lượt user và 5 lượt assistant trong cùng phiên.

## Part 6 – Project production-ready

`python check_production_ready.py` được chạy đầy đủ trong Linux với Docker và Redis.

```text
📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 41/41 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Image đo khoảng 63 MiB. Sau khi restart agent, Redis vẫn giữ rate limit. Khi nhận SIGTERM lúc có request, request trả `200` và tiến trình thoát mã `0`.

## Part 7 – Benchmark và observability

### Exercise 7.1–7.3 – Metrics, latency, eval và quality gate

`/metrics` của bản develop cho phép đọc số request theo status, histogram latency, số token và chi phí. Có thể so một counter trước và sau khi gọi `/ask`. Histogram cần các bucket phù hợp để ước lượng phân vị. p50, p95 và p99 là ngưỡng mà lần lượt 50%, 95% và 99% request trong mẫu hoàn tất bên dưới ngưỡng đó. p95 và p99 cho thấy phần request chậm mà trung bình dễ che khuất. [Kết quả bốn mức concurrency và ba mức slow rate](BENCHMARK_REPORT.md)

Mẫu `GET /metrics` sau một request thành công.

```text
http_requests_total{method="POST",route="/ask",status="200"} 1.0
http_request_duration_seconds_count{method="POST",route="/ask"} 1.0
llm_tokens_total{model="mock-llm-small",type="input"} 81.0
llm_tokens_total{model="mock-llm-small",type="output"} 46.0
```

Eval v1 trả đúng 1/23, v2 ban đầu 21/23, v2 đã sửa 23/23 và 0 regression. Chạy lại v1 với báo cáo v2 làm baseline trả exit code `1`. Workflow [eval.yml](.github/workflows/eval.yml) chạy eval trên pull request với ngưỡng 85%. Nếu dùng job này làm required status check, PR có job fail sẽ bị chặn merge. Lệnh eval có thể fail do thấp hơn ngưỡng hoặc có regression khi truyền baseline.

### Exercise 7.4 – Đọc dashboard

Snapshot Prometheus khi Locust chạy 30 user trên hai replica cho p95 299.0 ms và avg 250.0 ms. Chênh lệch phản ánh nhóm request chậm hơn phần lớn request. Nginx chia tải gần đều. Replica `172.19.0.7:8000` nhận 6.20 req/s và `172.19.0.9:8000` nhận 5.95 req/s. Tốc độ token input là 944.1/s và output 499.8/s.

Input tokens/s bao gồm phần prompt hệ thống, câu hỏi và tài liệu retrieval. Output tokens/s chỉ đếm câu trả lời. Qua Nginx, `GET /metrics` trả `404`; Prometheus đọc trực tiếp endpoint từng agent trong mạng Docker để giữ chi tiết hạ tầng ở nội bộ.

### Exercise 7.5–7.7 – Trace, alert và báo cáo

Trace chậm `4709e0365c5966f3643e1671d2ad0ef7` có span `chat mock-llm-small` kéo dài 1696.292 ms. Trace lỗi `3e3abdb47390992b11c0d531fcb72487` có event `exception`. Hai trace khớp với log JSON theo `trace_id`.

Prometheus quan sát `AgentHighErrorRate` sau 88.2 s và `AgentHighLatencyP95` sau 144.5 s kể từ lúc bắt đầu áp dụng cấu hình fault injection. Rule test bằng `promtool` đã pass. Bảng tải Locust và log đầy đủ nằm trong [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md).

### Câu hỏi thảo luận

1. Metrics hạ tầng đo traffic, latency, error và saturation. Chất lượng nội dung cần golden eval trong CI và kiểm tra định kỳ hoặc canary trong production.
2. Pull cho Prometheus quyền quyết định chu kỳ scrape và quan sát trạng thái `up` của target. Scale-to-zero có thể làm target biến mất. Có thể lấy telemetry từ managed collector hoặc giám sát đường vào và kiểm thử tổng hợp.
3. Label `user_id` làm số time series tăng theo số người dùng và nhân tiếp với route/status. Giữ ID chi tiết trong log hoặc trace, dùng label ít giá trị cho metric.
4. Sampling tiết kiệm lưu trữ và thông lượng xuất trace, nhưng có thể bỏ sót lỗi hoặc ca chậm hiếm. Tail sampling có thể giữ ưu tiên trace lỗi và chậm.
5. `for: 0s` dễ báo động với spike ngắn. `for: 30m` trì hoãn phát hiện sự cố kéo dài. Chọn thời gian dựa trên mức nhiễu và yêu cầu phản ứng.

## AI log

- Yêu cầu hỗ trợ kiểm tra phần triển khai Day 14, chạy lại các phép đo cục bộ và tổng hợp báo cáo. Trợ lý đã chạy các lệnh kiểm thử, đối chiếu JSON/CSV và soạn bản nháp phần giải thích từ code và số liệu đo.
- CP5, CP6 và eval 23/23 đã được học viên xác nhận trước lượt này. Kiểm tra lại Railway trong lượt này chỉ dùng ba endpoint không cần secret. Ảnh và bước tự đối chiếu nội dung trước khi nộp do học viên thực hiện.
