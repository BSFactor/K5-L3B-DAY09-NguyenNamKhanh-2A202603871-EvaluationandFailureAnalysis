# M7 — Integrity và ratchet

Phần cài đặt này được kiểm trên tests, traps và variants được cung cấp.
`instructor/grade_hidden.py` không có trong repo và **chưa chạy**; không suy điểm
hidden từ việc các kiểm tra dưới đây pass.

## Integrity trước khi so metric

`lab9.gate.integrity_check` kiểm **cả PR và baseline** trước khi bootstrap:

- Report có manifest/rows/metrics đúng cấu trúc; số item và seeds hợp lệ,
  không lặp seed; số row bằng `items × seeds`.
- Identity `(item_id, seed)` không trùng, có đủ tích Descartes item × seed;
  PR và baseline có cùng tập identity. Kiểm cả set và duplicate, không chỉ
  `len(rows)`: thay row fail bằng bản sao row pass vẫn bị bắt.
- `evaluator_failures` phải là list rỗng, kể cả khi tất cả aggregate đang xanh.
  Giá trị grader row thiếu/None/NaN/inf/khác miền điểm phải bị từ chối, không được
  rơi khỏi mẫu số; tất cả aggregate phải hữu hạn và spec metrics phải có đủ.
- Slice tags nhất quán giữa các seed của mỗi item, và giống baseline. Đổi tất
  cả seed để rút item ra khỏi slice cũng không được phép.
- Cost không âm/hữu hạn; row cost cần có nếu report có cost metric. Aggregate
  của các metric được chấm được tính lại bằng cùng `lab9.eval.aggregate`, gồm
  pass@k/pass^k và cost, rồi so với report. Report không được tự khai aggregate
  đẹp hơn rows. Không recompute để bỏ qua row hỏng: row hỏng đã bị từ chối trước.

Mọi lỗi trả danh sách lý do và gate CLI in `INTEGRITY`, rồi
`exit 1 — blocked: integrity`, không chạy bootstrap trên report hỏng.

## Ratchet và nguồn spec tin cậy

Khi có `--base-spec` và cùng `eval_set_version`, rule cũ không được biến mất,
blocking không được tắt; min không được giảm/mất, max và max_increase không
được tăng/mất; no_significant_drop không được bỏ. Kiểm metrics và slices, với
slice identity `(name, metric)` để không đổi metric rồi lách rule cũ. Metric kind,
level, grader cũ không được đổi âm thầm. Lý do có tiền tố `RATCHET` trong phần
INTEGRITY. Siết ngưỡng vẫn được phép; eval-set version mới có thể khởi tạo bộ
ngưỡng mới, nhưng vẫn cần baseline cùng eval-set SHA để so report.

Workflow `eval-gate-v2` lấy `BASE_SHA` từ PR base SHA và fetch history. Nó trích
`src/config/metric_spec_v2.yaml` **từ base commit** ra `/tmp/lab9-base-spec.yaml`
để truyền `--base-spec` vào mutation scorecard, thay vì dùng spec đã chỉnh trong
PR làm chuẩn. Workflow dispatch dùng commit của run. Nếu base chưa có spec v2
thì đây là lần khởi tạo, không có rule v2 cũ để ratchet. CI cũng chạy source
slice_regression rồi trap suite. YAML đã parse và mọi shell step qua `bash -n`;
GitHub Actions thực chưa được chạy trong phiên này.

## Kết quả và bằng chứng

Commands chạy từ `src/`:

```bash
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/eval_slice_regression.json
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json --base-spec config/metric_spec_v2.yaml --out reports/m7_mutation.json
python -m lab9.m7_verify
python -m pytest -q -m student -o addopts= -k lab9
```

Ở lệnh local scorecard, cùng spec được truyền hai lần để kiểm không có false
alarm khi spec không đổi; đây không thay thế trusted base commit của PR. Unit
tests thay đổi candidate spec trong khi giữ base spec riêng, bao gồm từng cách
hạ ngưỡng/xóa metric/xóa slice/tắt blocking/bỏ CI. Kiểm thêm spec hiện tại so với
spec lấy từ nhánh `main` local cũng không báo vi phạm.

Trap builder exit 0: **4/4 trap bị chặn**. `lab9.m7_verify` chạy lại từng file qua
CLI thật, yêu cầu returncode=1 **và explicit integrity verdict**, không coi Python
exception exit 1 là thành công. Với loosened_spec, còn yêu cầu có lý do RATCHET.

```text
cherry_picked_seeds: exit 1 — blocked: integrity
dropped_failing_rows: exit 1 — blocked: integrity
evaluator_errors_as_nan: exit 1 — blocked: integrity
loosened_spec: exit 1 — blocked: integrity
```

Traps/altered spec được sinh bằng `lab9.traps`, không sửa tay:
[`reports/traps/`](../src/reports/traps/).
[`m7_verification.json`](../src/reports/m7_verification.json) lưu stdout/stderr,
exit code và verdict từng file. [`m7_mutation.json`](../src/reports/m7_mutation.json)
ghi **3/3 regression bị chặn, 0 false alarm**: fixed/honest_refactor merge;
seeded/slice/flaky block. Source report: `E-slice_regression-20261118-a7b0`,
140 rows, eval SHA `a7b022d996d3`, spec 2.2, cùng baseline M6.

**95 student tests Lab 9 pass**, gồm core và advanced, cùng tests bổ sung về
row duplication giữ nguyên count, nonfinite/missing values, aggregate giả,
retag một hoặc tất cả seeds, evaluator_failures trên run xanh, baseline hỏng,
ratchet từng loại rule và chấp nhận spec được siết. Evalset v2: 0 problem.
M4 verification chạy lại vẫn đúng exit 0/0/1 và reference CI không đổi. Không
sửa `src/lab8/`, không nới spec để vượt traps.

## Trap nào có thể còn lọt?

Duplicate rows và evaluator_failures trên run xanh được kiểm trực tiếp, không
còn chỉ dựa vào floor hoặc set identity. Nhưng **consistency không phải chứng
thực nguồn gốc**: người có quyền có thể giả toàn bộ row scores rồi recompute
aggregate đúng, giữ nguyên IDs/seeds/tags. Không có replay độc lập hoặc artifact
được ký/hash từ môi trường tin cậy thì report tự nhất quán vẫn có thể giả.
Tương tự, nếu attacker sửa cả baseline/spec hoặc workflow/grader, chỉ kiểm tra
candidate report không đủ. Cần bảo vệ base branch, review thay đổi eval code và
CI chạy lại từ nguồn tin cậy; repository settings đó không được tự tuyên bố đã
cấu hình ở đây.

Ratchet chỉ so được khi caller cung cấp base spec tin cậy. Quy tắc cho phép
version eval set mới cũng cần review, tránh tăng version chỉ để reset floors.
Gate hiện so slice tags với baseline chứ không xác minh lại từng tag với labels
ở runtime; giả cả hai phía vẫn có thể qua. Những giới hạn này và hidden vectors
chưa thấy cần nêu trong eval card, không khẳng định đã chống mọi cách gian lận.
