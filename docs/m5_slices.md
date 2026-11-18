# M5 — Eval set v2 và slice gate

Đây là phần cài đặt M5 và kết quả kiểm tra trên dữ liệu/variant được cung cấp.
**Chưa chạy `instructor/grade_hidden.py`**: script/key/variant ẩn thuộc repo
giảng viên, không có ở đây. Theo README phần Advanced/Expert, giảng viên dùng
variant/trap ẩn để chấm; vượt các kiểm tra dưới đây không bảo đảm điểm hidden.
Slice gate chỉ đọc rule, metric, item và seed; không có nhánh điều kiện theo tên
variant công khai. Tên variant chỉ xuất hiện trong script kiểm chứng test fixture.

## Eval set và mapping

`config/fm_map.yaml` map đầy đủ 8 cơ chế sang taxonomy cố định:

| Mechanism | FM | Số item v2 phủ FM (gồm v1) |
|---|---|---:|
| ticket_over_db | FM-03 | 3 |
| stale_policy | FM-06 | 3 |
| clause_sum | FM-04 | 10 |
| double_deduct | FM-05 | 6 |
| sibling_refund | FM-07 | 5 |
| denied_ignored | FM-02 | 4 |
| reply_ledger_mismatch | FM-08 | 4 |
| cross_principal | FM-09 | 4 |

V2 giữ 14 item v1 và thêm toàn bộ 14 claim adversarial: **28 item × 5 seed**,
SHA `a7b022d996d3`. Không thêm nhãn inline; `labels_v2.json` tách riêng. Mỗi FM
được pack tấn công có ≥3 item trên tập v2 đúng theo validator; không đồng nghĩa
mỗi FM có ≥3 item mới trong pack. FM-01 còn 14 canary case v1, không phải cơ chế
riêng trong pack. Nguồn/provenance do builder giữ nguyên; không đổi fixture Lab 8.
FM-09 vẫn là kiểm tra boundary phòng vệ; không tự tuyên bố đã quan sát thấy
vi phạm cross-principal chỉ vì adversarial pack có lời yêu cầu vượt quyền.

Slices lấy từ expected label/split, không từ output agent:
`money_movement` khi refund kỳ vọng >0 (12 item), `adversarial` khi thuộc pack
(14 item), `denial` khi status kỳ vọng denied (11 item). Các slice có thể chồng
nhau; không cộng số lượng slice để tính tổng item.

## Quy tắc gate

Spec v2.1 dùng `pass_rate` theo item, min 0.90 và `no_significant_drop=true`
cho money_movement/adversarial/denial; cả ba blocking. Tỷ lệ hoàn tiền đúng và
pass_rate toàn tập vẫn có floors 0.90/0.85 theo spec v2 starter, không sửa sàn
v1. Ngưỡng slice 0.90 là tiêu chí chất lượng cho nhóm quan trọng; kết quả kiểm
chứng riêng cho thấy fixed/honest_refactor đều đạt 1.0.

`slice_check` lấy mean qua seed của từng item trước, rồi mean qua item. Khi so
CI, ghép đúng item ID và resample cặp bằng cùng bootstrap config của gate toàn
cục; CI hoàn toàn dưới 0 thì fail. Rớt floor cũng fail dù CI chạm 0. Slice thiếu,
khác tập item hoặc không tính được CI sẽ fail nếu rule blocking; rule theo dõi
chỉ warn. Không dùng giao tập item âm thầm để bỏ item xấu.

Baseline v2 sinh mới bằng swarm, không dùng baseline v1 vì tập item/SHA đã đổi.
`pass_at_k`/`pass_hat_k` còn None ở report M5 do TODO M6, chưa dùng làm điều kiện
blocking. Integrity/ratchet là M7 và chưa cài; không tuyên bố gate hiện chống được
report bị sửa, missing row/seed hoặc spec bị nới trong cùng PR.

## Kết quả công khai

Nguồn report được sinh bằng script:
[`baseline_v2.json`](../src/reports/baseline_v2.json),
[`m5_eval_slice_regression.json`](../src/reports/m5_eval_slice_regression.json),
[`m5_eval_fixed.json`](../src/reports/m5_eval_fixed.json),
[`m5_eval_honest_refactor.json`](../src/reports/m5_eval_honest_refactor.json).
Mỗi report có 140 rows, không có evaluator failure.

| Shape | Global pass_rate | Money pass_rate | Adversarial pass_rate | Gate |
|---|---:|---:|---:|---|
| swarm baseline | 0.9786 | 1.0000 | 0.9714 | baseline |
| slice_regression | 0.9357 | 0.8500 | 0.9143 | exit 1, chỉ money_movement |
| fixed | 1.0000 | 1.0000 | 1.0000 | exit 0 |
| honest_refactor | 1.0000 | 1.0000 | 1.0000 | exit 0 |

Run IDs: `E-swarm-20261118-a7b0`, `E-slice_regression-20261118-a7b0`,
`E-fixed-20261118-a7b0`, `E-honest_refactor-20261118-a7b0`.

Slice regression có Δ pass_rate toàn cục −0.043, CI [−0.121,+0.029]: không
giảm có ý nghĩa và vẫn trên floor 0.85. Tắt slices trên cùng report thì gate
**không chặn**. Money slice có Δ −0.150, CI [−0.300,0.000] và tỷ lệ 0.85 dưới
floor 0.90: bị chặn ở **`slice:money_movement/pass_rate`**. Điều này tái hiện đúng
hiện tượng checkpoint M5: trung bình toàn tập che regression nhóm hoàn tiền.
Cost honest_refactor tăng do extra lookup, tạo warn nhưng không false block.

[`m5_verification.json`](../src/reports/m5_verification.json) ghi CLI stdout,
exit code, các slice mean/CI, coverage và kết quả gate khi bỏ slices. Script
verification không phải hidden grader và không tham gia quyết định production.

## Tái hiện

Chạy từ `src/` với environment M0:

```bash
python -m lab9.evalset --v2 --build
python -m lab9.evalset --v2 --check
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/m5_eval_slice_regression.json
python -m lab9.eval --shape fixed --spec config/metric_spec_v2.yaml --out reports/m5_eval_fixed.json
python -m lab9.eval --shape honest_refactor --spec config/metric_spec_v2.yaml --out reports/m5_eval_honest_refactor.json
python -m lab9.m5_verify
python -m pytest -q -m student -o addopts= -k 'lab9 and (not advanced or slice_check)'
```

Kết quả: evalset 0 problem; 45 tests pass (core + M5 slice tests). Bộ advanced
đầy đủ còn có TODO M6/M7 nên chưa được tuyên bố xanh. Tests bổ sung kiểm slice
name bất kỳ, pair theo item dù rows đổi thứ tự, floor equality, CI âm khi vẫn
trên sàn, rule nonblocking, và slice thiếu/unpaired. Không viết test phụ thuộc
key private hoặc khớp cứng tên variant trong gate.
