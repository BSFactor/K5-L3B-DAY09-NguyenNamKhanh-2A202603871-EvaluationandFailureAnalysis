# M6 — A/A, pass@k và pass^k

Cài đặt và kiểm tra trên dữ liệu/variant được cung cấp; chưa chạy private
`instructor/grade_hidden.py`. Kết quả dưới đây không phải xác nhận điểm hidden.

## Estimator

Với n lượt chạy, c lượt PASS, chọn k lượt **không hoàn lại**:

- `pass_at_k = 1 - C(n-c,k)/C(n,k)`: ít nhất một lượt thành công, phù hợp khi
  được phép retry và chọn một kết quả đúng.
- `pass_hat_k = C(c,k)/C(n,k)`: tất cả k lượt thành công, đo reliability.

Dùng `math.comb`, không hardcode tên shape, claim hoặc seed. Input phải nguyên,
n≥1, 0≤c≤n, 1≤k≤n; sai điều kiện → ValueError. Nếu không đủ lượt fail để chọn k
lượt toàn fail thì pass@k=1; nếu c<k thì pass^k=0. Chẳng hạn n=5,c=4,k=5 cho
pass@5=1 nhưng pass^5=0. Với k=1, cả hai bằng c/n; luôn có
`pass^k ≤ pass@1 ≤ pass@k`. Tests so với mọi tổ hợp draw trên n=1…7, không chỉ
so với cùng công thức đã viết trong implementation.

Harness lấy estimator của từng item rồi mean qua items. Với n=k=5,
`pass_hat_5` là tỷ lệ item có đủ cả 5 trial PASS; không phải `(global pass_rate)^5`.

## A/A trước khi chọn ngưỡng

```bash
cd src
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110 --out reports/m6_aa.json
```

A/A đã chạy khi spec còn version 2.1, trước khi thêm blocking floor. Hai bộ seed:
`[11,22,33,44,55]` và `[66,77,88,99,110]`; cùng swarm, eval SHA `a7b022d996d3`,
28 item × 5 seed mỗi run. [`m6_aa.json`](../src/reports/m6_aa.json) lưu đầy đủ hai
report/manifest/rows và deltas. **Mọi delta đều 0**, kể cả simulated cost.

| Metric | Spec seeds | Alt seeds | Delta |
|---|---:|---:|---:|
| pass_rate / pass_at_1 / pass_hat_1 | 0.9786 | 0.9786 | 0 |
| pass_at_3 | 1.0000 | 1.0000 | 0 |
| pass_hat_3 | 0.9357 | 0.9357 | 0 |
| pass_at_5 | 1.0000 | 1.0000 | 0 |
| pass_hat_5 | 0.8929 | 0.8929 | 0 |

Đây là hai phép đo deterministic, không phải ước lượng đủ của phân phối nhiễu
production. Cả hai seed set đều có một seed chia hết cho 5, nên điểm yếu ticket
trust của swarm ảnh hưởng cùng nhóm 3 item, trong khi seed cụ thể khác nhau.
Không yêu cầu raw (item,seed) giống nhau và không đưa A/A vào gate PR-vs-main.

Spec **2.2** thêm `pass_hat_5`, capability/outcome, **blocking min=0.85**. Baseline
A/A là 25/28≈0.8929; floor thấp hơn 0.0429, lớn hơn độ lệch quan sát bằng 0.
Với 28 item, floor này đòi ≥24 item đều PASS cả 5 lượt, cho phép tối đa 4 item
không ổn định; không chọn floor bằng đúng mức 0.8929 quan sát được. Sàn này là
ngân sách reliability trên bộ lab, không phải mức đã hiệu chuẩn cho LLM thật.
Không thêm CI drop cho `pass_hat_5` vì report hiện chỉ chứa aggregate estimator,
không chứa estimator này trong từng trial row để paired bootstrap.

Baseline v2 được **chạy lại agent** bằng spec 2.2 sau khi thêm metric, nên các
trường reliability trước đó None ở M5 nay có số thật. Không sửa tay baseline.
Lịch sử M5 còn trong Git; các số outcome cũ không đổi. Report A/A giữ provenance
spec 2.1 đã dùng lúc đo, không đổi metadata hồi tố.

## Flaky regression và giới hạn của phát biểu checkpoint

[`m6_eval_flaky_regression.json`](../src/reports/m6_eval_flaky_regression.json),
run `E-flaky_regression-20261118-a7b0`:

| Metric | Swarm baseline | Flaky |
|---|---:|---:|
| pass_rate | 0.9786 | 0.9143 |
| pass_at_5 | 1.0000 | 1.0000 |
| pass_hat_5 | 0.8929 | 0.5714 |
| refund_amount_correct | 0.9786 | 0.9643 |

`pass_hat_5=0.5714` rớt floor 0.85 nên gate exit 1. Retry metric pass@5 vẫn 1:
variant có thể thành công ít nhất một lần nhưng nhiều item không thành công
nhất quán. `rare` switch ở variant này kích hoạt seed 33 trong 5 seed cố định,
không có nghĩa xác suất production được đo chính xác là 1/5.

**Kết quả thực không khớp hoàn toàn diễn giải “pass_rate không chặn” nếu tính
cả CI:** global pass_rate 0.9143 vẫn qua floor 0.85, nhưng Δ=−0.064 với CI
[−0.114,−0.014] nên full pass_rate gate hiện cũng chặn. Money slice=0.8667 cũng
rớt sàn 0.90. Vì thế danh sách chặn thật là `pass_rate`, `pass_hat_5`,
`slice:money_movement/pass_rate`; không tuyên bố pass_hat_5 là lý do duy nhất.
Không hạ sàn, tắt CI hoặc đổi variant để buộc kết quả giống mô tả checkpoint.
Verification riêng bỏ CI chỉ nhằm kiểm tra rằng **floor trung bình đơn thuần**
không phát hiện, không thay đổi spec được dùng bởi gate thực.

## Scorecard và tái hiện

```bash
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m lab9.eval --shape flaky_regression --spec config/metric_spec_v2.yaml --out reports/m6_eval_flaky_regression.json
python -m lab9.m6_verify
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json --out reports/m6_mutation.json
python -m pytest -q -m student -o addopts= -k 'lab9 and not integrity'
```

[`m6_verification.json`](../src/reports/m6_verification.json) lưu exit code/stdout
của gate thật, A/A margin, kết quả kiểm pass_rate đầy đủ và floor-only tách biệt.
[`m6_mutation.json`](../src/reports/m6_mutation.json) ghi **3/3 regression bị chặn,
0 false alarm**: fixed và honest_refactor merge; seeded/slice/flaky block. Đây là
scorecard variant công khai, chưa phải kiểm trap integrity M7 hoặc hidden grader.
Core + M5/M6 tests: **63 pass**; evalset v2: 0 problem. Hai test integrity M7
chưa thuộc phạm vi M6 và vẫn còn TODO trong code.

## Vì sao LLM thật cần noise band khác

LLM thật có sampling, khác biệt backend/routing và biến động tool/data; cùng
prompt/seed cũng chưa chắc tái lập như MockLLM. Cần nhiều A/A lặp độc lập trên
phân phối đại diện, ghép item đúng, đánh giá cả variation giữa run và bất định
do số item. Floor phải thấp hơn vùng dao động bình thường của **metric level**,
hoặc quy tắc drop phải nằm ngoài dải **delta** A/A, trước khi dùng gate chặn
release. Không lấy delta=0 ở lab rồi coi production có noise=0.

5 seed không bảo đảm thấy lỗi hiếm. Nếu các lượt độc lập và xác suất lỗi thật
là p thì xác suất cả 5 lượt không thấy lỗi là `(1-p)^5`: p=1/3 cho khoảng 13.2%,
p=1/5 cho khoảng 32.8%. Với seed tương quan, công thức độc lập không còn đủ.
Không hạ threshold đến khi bắt được một seed đẹp; cần tăng cỡ mẫu/đa dạng item,
đo lại A/A và ghi giới hạn. Hidden variants/traps vẫn do giảng viên xác nhận.
