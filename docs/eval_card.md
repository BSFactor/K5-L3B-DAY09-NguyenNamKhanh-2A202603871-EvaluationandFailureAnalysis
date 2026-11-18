# Eval card — LogiX-VN refund agent

M4, 2026-11-18. Evaluation offline, không phải kết quả production.

- **Baseline / PR swarm:** `E-swarm-20261118-8c3b` — hai lần chạy riêng cho
  `baseline_v1.json` và `eval_pr.json`; run ID hiện chỉ mã hóa shape/ngày/SHA
  nên giống nhau dù chạy riêng. `ci_check` xác nhận metrics bằng nhau.
- **Fixed:** `E-fixed-20261118-8c3b`.
- **Regression:** `E-seeded_regression-20261118-8c3b`.
- **Phiên bản:** eval set v1, SHA `8c3b6f9f4a6c`; metric spec 1.1;
  Python 3.13.18; MockLLM; code/grader là commit M4 chứa card và reports này
  trên nhánh `starter/d09` (tiếp nối M3 `a621bfe`).
- **Eval set:** 14 item × 5 seed `[11,22,33,44,55]`, nguồn `lab8_public`;
  labels tách ở `data/eval/labels_v1.json`; tags tái tạo được từ `lab9.evalset`.

## Metric, ngưỡng và kết quả

Nguồn: [`metric_spec.yaml`](../src/config/metric_spec.yaml), các report
[`baseline_v1.json`](../src/reports/baseline_v1.json),
[`eval_pr.json`](../src/reports/eval_pr.json),
[`eval_fixed.json`](../src/reports/eval_fixed.json),
[`eval_seeded_regression.json`](../src/reports/eval_seeded_regression.json).
Mọi report sinh bằng script, không sửa tay; mỗi report có 70 rows, không có
evaluator failures.

| Metric | Ngưỡng / chặn? | Baseline | Fixed | Seeded regression |
|---|---|---:|---:|---:|
| approval_bypass | max 0, có | 0 | 0 | 0 |
| secret_leak | max 0, có | 0 | 0 | 0 |
| db_fact_kept | min 0.95, theo dõi | 0.9857 | 1.0000 | 0.9286 |
| refund_amount_correct | min 0.95 + paired CI, có | 0.9857 | 1.0000 | 0.8571 |
| pass_rate | min 0.85 + paired CI, có | 0.9857 | 1.0000 | 0.7143 |
| reply_amount_correct | min 1.0 + paired CI, có | 1.0000 | 1.0000 | 0.7857 |
| pass_5 | min 0.80, theo dõi | 0.9286 | 1.0000 | 0.7143 |
| cost_per_success | tăng tối đa 10%, theo dõi | 49.5670 | 48.7157 | 81.2020 |

Cost chỉ là giá mô phỏng, không phải hóa đơn API hay tiền refund.

## Paired CI và quyết định gate

Resampling unit là **item**, lấy trung bình qua 5 seed trước rồi bootstrap cùng
index giữa PR/baseline. Không xem 70 trial là 70 quan sát độc lập. SciPy
`bootstrap(paired=True, method="percentile")`, 1000 resamples,
`rng=numpy.random.default_rng(2027)`, confidence=0.95. Dấu Δ = PR − baseline.
Nếu hai vector bằng nhau thì Δ và CI đều 0. CI có upper bound <0 là giảm có ý
nghĩa; CI chạm 0 không bị chặn bởi điều kiện CI nhưng vẫn có thể rớt sàn.

| Report | Δ pass_rate | 95% CI | Gate CLI |
|---|---:|---|---|
| PR swarm | 0.000 | [0.000, 0.000] | exit 0 |
| fixed | +0.014 | [0.000, +0.043] | exit 0 |
| seeded_regression | −0.271 | [−0.500, −0.057] | exit 1 |

Regression bị chặn ở `refund_amount_correct`, `pass_rate`,
`reply_amount_correct`. Với refund/reply, CI chạm 0 nhưng vẫn rớt sàn tuyệt đối;
riêng `pass_rate` vừa rớt sàn vừa có CI hoàn toàn âm. Approval bypass vẫn 0 vì
host chặn các writes thiếu quyền; agent vẫn có thể nói dối success sau denial.

[`m4_verification.json`](../src/reports/m4_verification.json) giữ stdout và exit
code thực của ba lệnh gate, CI chưa làm tròn, cùng kết quả kiểm baseline/spec.
`python -m lab9.m4_verify` tái kiểm các report đã sinh. Lệnh
`python -m lab9.ci_check --pr reports/eval_pr.json --baseline reports/baseline_v1.json`
trả exit 0. Core student suite: 37 pass; `evalset --check`: 0 problem.

## Judge, trace và vận hành

- **Judge:** tone κ=0.757, P=0.857, R=0.800; helpful bị loại vì κ=0.375,
  R=0.300, bỏ sót 21/30 lỗi. Xem [judge audit](judge_audit.md). Tiền/approval
  luôn chấm bằng code; judge tone không tham gia các metric tiền của gate này.
- **Trace case:** [FM-08 C-008@11](trace_case.md), event 4 reply nói 35000đ,
  ledger ghi 20000đ. Regression test chạy lỗi và fixed; [M3](m3_trajectory.md)
  ghi detection 45/45 và false alarms 0/70 trên bộ kiểm công khai có chủ đích.
- **Gate owner:** Nguyễn Nam Khánh, chủ bài cá nhân. Khi exit 1: đọc metric/trace,
  sửa agent hoặc grader dựa trên bằng chứng, chạy lại cùng spec/baseline trước
  khi merge; không sửa report hoặc hạ sàn để qua gate.
- **Phạm vi pilot:** offline trên public claims LogiX-VN, temp SQLite và MockLLM;
  chỉ mô phỏng refund theo policy/approval fixture, chưa cho phép giao dịch thật.

## Giới hạn và khi nào tăng version

14 item, CI rộng, chỉ chứng minh chặn regression lớn trên các variant công khai;
không chứng minh bắt được lỗi hiếm hay lỗi chỉ thuộc slice nhỏ. 5 seed MockLLM
không đại diện cho biến thiên LLM thật. Judge replay đã công khai, có reply mẫu
lặp, chưa có held-out độc lập và chưa đo người dùng thật.

`reply_amount_correct` kiểm consistency của các assertion VND trong template,
không kiểm completeness: swarm gốc không ghi reply nên không có assertion để
so. Parser chưa xử lý đầy đủ văn tự do/đa tiền tệ. Scope và integrity/ratchet còn
là bài M5–M7; gate core hiện không đủ chống report bị làm đẹp hoặc hạ spec trong
cùng PR. Chưa tuyên bố Advanced/Expert hoàn thành.

Thêm/đổi item, label, split hoặc provenance đáng kể → tăng `eval_set_version`
và sinh baseline mới. Đổi grader/metric/ngưỡng → tăng `metric_spec_version`, ghi
lý do, chạy lại báo cáo; cùng eval set chỉ siết ngưỡng theo quy tắc README. Không
đổi fixture Lab 8 hoặc chỉnh tay report để cải thiện số liệu.
