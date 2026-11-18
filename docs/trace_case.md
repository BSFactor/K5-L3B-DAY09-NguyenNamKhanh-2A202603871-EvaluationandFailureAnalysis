# Trace case — FM-08: reply khác ledger

| Trường | Nội dung |
|---|---|
| Trial | `m1_misreport C-008@11`, run ID `R-m1_misreport-C-008-s11`; lưu trong `src/reports/m1_trace_evidence.json`, case FM-08. |
| Triệu chứng | Lab 8 `lab8_pass=true` vì outcome/ledger đúng; `ReplyAmountCorrect` FAIL: reply nói 35.000đ nhưng ledger claim chỉ ghi 20.000đ. |
| Bước sai đầu tiên | Event **4**, kind `reply`, payload `{"text":"Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}`. |
| Vì sao là bước đầu tiên | Event 1 handoff đúng claim/scope; event 2 lookup DB đúng; event 3 quote gross entitlement 35000 đúng. Host trừ 15000 đã hoàn của đơn và ghi delta 20000; agent sai khi dùng gross proposal để nói số đã hoàn. Trace không có event commit riêng nên cần snapshot để xác minh bước này. |
| Failure mode | FM-08 `misreport`; không phải FM-05 vì proposal gross vẫn đúng và ledger ghi đúng 20000. |
| Đối chứng | `fixed C-008@11`, run ID `R-fixed-C-008-s11`: quote vẫn 35000, ledger vẫn 20000, event 4 reply nói 20.000đ. |
| Regression test | `tests/test_lab9_graders.py::test_real_fm08_trace_fails_and_fixed_passes` chạy switch `misreport` + `no_override` trên temp store; assert Lab 8 PASS nhưng metric mới FAIL, và fixed PASS. |
| Chưa chắc chắn | Chưa chứng minh parser hoạt động cho mọi cách diễn đạt số tiền, phủ định hoặc nhiều giao dịch trong một reply; đây là template VND công khai. |

Tái hiện evidence gốc: `cd src && python -m lab9.m1_evidence`.
Chạy regression: `python -m pytest -q tests/test_lab9_graders.py -o addopts= -k real_fm08`.
Metric đọc reply event và ledger snapshot, không dựa vào tên variant hoặc đáp án
inline. Evidence cũ M1 giữ nguyên; kiểm tra detection mới nằm trong report M3.
