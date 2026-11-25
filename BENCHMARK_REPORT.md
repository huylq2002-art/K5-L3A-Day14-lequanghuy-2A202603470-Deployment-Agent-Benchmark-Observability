# Benchmark & Observability Report — Day 14

**Họ tên:** Lê Quang Huy (2A202603470)

**Ngày chạy:** 25/11/2026 (GMT+7)

**Môi trường:** Windows 11, 8 CPU logic, Python 3.13.4 cho CP7.
CP8 chạy trong Docker Desktop Linux. Mỗi container agent được giới hạn 0,5 CPU và 256 MiB.

## 1. SLO của agent

| SLI | SLO | Lý do |
|---|---:|---|
| p95 của `POST /ask` | ≤ 500 ms | Giới hạn thời gian chờ của ít nhất 95% request thành công. |
| Error rate của `POST /ask` | ≤ 2% | Giới hạn tỷ lệ request thất bại, kể cả lỗi upstream. |
| Accuracy trên golden dataset | ≥ 85% trong CI, 100% và 0 regression cho Exercise 7.3 | Chặn giảm chất lượng trước khi merge, đồng thời xác minh đủ 23 câu của bài. |

Ngưỡng alert CP8 là cấu hình của stack production. Latency alarm dùng p95 > 1 giây và error alarm dùng tỷ lệ 5xx > 5%. Điều kiện phải duy trì trong khoảng `for` tương ứng.

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

Mỗi phép thử gửi 300 request với `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`. Latency trong JSON chỉ tính trên HTTP 200.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 3.77 | 204.7 | 239.7 | 1712.5 | 0.33% | PASS |
| 10 | 36.80 | 217.8 | 360.9 | 1694.4 | 1.00% | PASS |
| 50 | 89.79 | 279.3 | 525.0 | 1809.1 | 1.00% | FAIL |
| 100 | 40.83 | 944.0 | 5065.1 | 5376.9 | 1.00% | FAIL |

RPS tăng từ 3.77 lên 89.79 khi tăng đến concurrency 50, rồi giảm còn 40.83 ở concurrency 100. Ở 50 và 100, p95 vượt 500 ms. Kết quả phù hợp với việc request xếp hàng khi một tiến trình phục vụ bị quá tải. Phép đo này chưa tách riêng giới hạn của client HTTP, hệ điều hành và agent.

### 2.2 Tail latency

Mỗi phép thử gửi 300 request ở concurrency 20, giữ `MOCK_ERROR_RATE=0.01` và chỉ đổi `MOCK_SLOW_RATE`.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---:|---:|---:|---:|
| 0 | 203.7 | 235.8 | 247.9 |
| 0.03 | 243.3 | 237.4 | 1721.9 |
| 0.1 | 352.2 | 1704.1 | 1761.3 |

Ở 3%, p99 tăng từ 247.9 lên 1721.9 ms, trong khi p95 chỉ đổi từ 235.8 lên 237.4 ms. Ở 10%, p95 lên 1704.1 ms còn trung bình là 352.2 ms. Trung bình bị chi phối bởi nhóm request nhanh và không thể hiện đầy đủ phần đuôi. p99 phát hiện nhóm chậm hiếm sớm hơn. p95 lệch mạnh khi nhóm chậm chiếm hơn khoảng 5%.

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Eval dùng cùng golden dataset và tắt mô phỏng lỗi ngẫu nhiên. Bản v2 ban đầu chạy bằng knowledge base từ commit gốc trong thư mục tạm. Bản v2 đã sửa đối chiếu trực tiếp với JSON của v2 ban đầu.

| Chỉ số | Agent v1 | Agent v2 | Agent v2 sau sửa KB |
|---|---:|---:|---:|
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100.00% (23/23) |
| Avg tokens / câu | 57.6 | 109.1 | 114.7 |
| Tổng cost (USD) | 0.000411 | 0.000762 | 0.000799 |
| Cost / câu đúng (USD) | 0.00041055 | 0.00003627 | 0.00003475 |
| Latency p95 (ms) | 189.8 | 223.0 | 232.0 |
| Quality gate | FAIL (80%) | PASS (80%) | PASS (100%) |

| ID sai ban đầu | Keyword bị thiếu trong JSON | Thay đổi |
|---|---|---|
| `security-02` | token, hết hạn, chữ ký | Thêm JWT, chữ ký, claim thời hạn và đối chiếu với API key. |
| `scaling-03` | cpu, memory, custom metrics | Thêm HPA dựa trên CPU, memory và custom metrics. |

Context truy xuất làm tăng token/câu và p95 từ 189.8 lên 232.0 ms. Số câu đúng tăng lên 23 nên chi phí trên mỗi câu đúng giảm khoảng 11.8 lần so với v1. Gate cuối ghi 0 regression. Thử đưa v1 vào gate lấy v2 làm baseline trả exit code `1`. Workflow 85% có thể dùng làm required check trên pull request.

## 4. Observability stack (production)

### 4.1 Ảnh minh chứng

- [ ] [Grafana khi có tải](screenshots/grafana-dashboard.png) với Golden Signals.
- [ ] [Jaeger trace chậm](screenshots/jaeger-slow-trace.png) với span gọi LLM được mở.
- [ ] [Jaeger trace lỗi](screenshots/jaeger-error-trace.png) với event `exception`.
- [ ] [Prometheus Alerts](screenshots/prometheus-alert-firing.png) với ít nhất hai alert firing đồng thời.

Baseline 30 user với hai replica cho p95 299.0 ms, avg 250.0 ms và phân bố `/ask` `172.19.0.7:8000` 6.20 req/s, `172.19.0.9:8000` 5.95 req/s. Token input 944.1/s, output 499.8/s. Nginx trả `404` với `GET /metrics`. Prometheus scrape từng replica nội bộ.

### 4.2 Thí nghiệm fault injection

Thời gian tính từ lúc bắt đầu áp dụng thay đổi tới lần đầu quan sát `firing` qua API Prometheus, polling mỗi khoảng 4 giây. A và B được áp dụng trong cùng đợt cuối để giữ hai alert đồng thời cho ảnh. Stack đã được giữ chạy cho việc chụp ảnh.

| # | Thay đổi | Alert quan sát | Thời gian tới firing | Panel |
|---|---|---|---:|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 88.2 s | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 144.5 s | p95 latency |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | 156.2 s | Cost USD/giờ |
| D | `docker pause` một replica | `AgentInstanceDown` | 44.4 s | Instances up |
| E | `AGENT_VERSION=v1` | Không phát sinh alert do giảm chất lượng | Quan sát 79.6 s | Phiên bản, tokens/s, retrieval |

Burn rate ước tính theo cửa sổ 5 phút là 0.55 USD/giờ ngay trước thí nghiệm C và 17.02 USD/giờ sau khi đổi model. Locust được tăng từ 12 lên 30 user cho thí nghiệm C. Mức tăng phản ánh cả chi phí mỗi request lẫn mức tải.

Pause giữ container trong DNS nên Prometheus thấy `up=0`. Lỗi 504 do timeout ở Nginx có thể không đi qua handler của agent và vắng mặt trong metric HTTP của agent. Quan sát ở cả ingress và app giúp xác định nơi trả lỗi. Để phát hiện giảm chất lượng với v1, chạy golden eval trên phiên bản đang phục vụ, đối chiếu baseline theo phiên bản và chặn rollout nếu accuracy giảm hoặc có regression.

### 4.3 Trace chậm và trace lỗi

**Trace chậm.** `trace_id=4709e0365c5966f3643e1671d2ad0ef7`. Tổng `POST /ask` 1733.010 ms, span `chat mock-llm-small` 1696.292 ms. Span gọi mock LLM chiếm 97.9% thời lượng HTTP. [Mở trong Jaeger](http://localhost:16686/trace/4709e0365c5966f3643e1671d2ad0ef7)

```json
{"ts": "2026-11-25T09:59:26.332024+00:00", "level": "INFO", "service": "observable-agent", "instance": "ea5379129461", "event": "llm_call", "trace_id": "4709e0365c5966f3643e1671d2ad0ef7", "span_id": "015a3f4556222afb", "request_id": "e15e13329c04", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 95, "output_tokens": 55, "cost_usd": 4.7e-05, "llm_ms": 1698.0}
```

**Trace lỗi.** `trace_id=3e3abdb47390992b11c0d531fcb72487`. Tổng `POST /ask` 847.158 ms, span `chat mock-llm-small` 822.408 ms. Span gọi mock LLM chứa event `exception`; endpoint trả HTTP 503. [Mở trong Jaeger](http://localhost:16686/trace/3e3abdb47390992b11c0d531fcb72487)

```json
{"ts": "2026-11-25T10:05:43.643161+00:00", "level": "INFO", "service": "observable-agent", "instance": "74dad524b4b0", "event": "llm_error", "trace_id": "3e3abdb47390992b11c0d531fcb72487", "span_id": "27102717e0e37fbf", "request_id": "5673bb65387a", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling (production, Locust headless)

Mỗi lượt chạy 100 user, ramp-up 10 user/s, thời lượng 2 phút, cùng cấu hình agent v2 mặc định. Bảng lấy dòng `Aggregated` gồm `/ask` và `/health` trong các file `*_stats.csv`.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Error rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 64.13 | 190 | 370 | 1700 | 63/7539 | 0.84% |
| 3 | 65.76 | 190 | 240 | 1700 | 70/7802 | 0.90% |

Scale từ 1 lên 3 replica cho RPS từ 64.13 đến 65.76, p95 giảm từ 370 xuống 240 ms và p99 giữ ở 1700 ms trong cả hai lượt. Thêm replica giảm phần chờ khi xử lý tải, nhưng mỗi Locust user vẫn đợi 0,5–2 giây giữa các lượt gọi. Độ trễ giả lập của LLM vẫn tồn tại ở mỗi replica và hiện rõ ở p99 cùng span gọi LLM.

## 6. Kết luận

1. Chạy nhiều mức concurrency để tìm điểm p95 vượt SLO. Giữ cấu hình tải và mô phỏng nhất quán giữa các phép đo.
2. Tách quality eval khỏi kiểm tra độ sẵn sàng. Một phiên bản có thể chạy khỏe nhưng trả lời sai.
3. Dùng metric để thấy xu hướng, alert để xác nhận vi phạm kéo dài, và ghép trace với log bằng `trace_id` để khoanh vùng.

Nếu đưa lên production, bổ sung error rate và timeout theo ingress, synthetic check từ phía client, tỷ lệ regression của bộ eval định kỳ, cùng alert tốc độ tiêu hao error budget trên cửa sổ ngắn và dài.
