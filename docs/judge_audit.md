# Judge audit — M2

FAIL là positive class: TP = người FAIL / judge FAIL; FP = người PASS / judge
FAIL; FN = người FAIL / judge PASS; TN = cả hai PASS. P đo độ tin cậy của cảnh
báo lỗi; R đo tỷ lệ lỗi thật được tìm thấy. FLOORS: κ≥0.6, P≥0.8, R≥0.7,
phải đạt **cả ba**; κ không xác định thì loại. So floors bằng số chưa làm tròn.

| Tiêu chí | n | TP / FP / FN / TN | κ | Precision | Recall | Đạt FLOORS? | Quyết định |
|---|---:|---|---:|---:|---:|---|---|
| tone_ok | 100 | 24 / 4 / 6 / 66 | 0.757 | 0.857 | 0.800 | Có | Dùng cho tone trong phạm vi replay này |
| helpful | 100 | 9 / 0 / 21 / 70 | 0.375 | 1.000 | 0.300 | Không | Loại khỏi gate helpfulness |

Reproduce từ `src/`:

```bash
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
# exit 0: PASS floors
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
# exit 1: FAIL floors (kết quả đúng của M2)
python -m pytest -q tests/test_lab9_stats.py tests/test_lab9_judge_calibration.py -o addopts= -k 'not paired_bootstrap'
```

## Audit bất đồng và hành động sửa rubric

Đây là audit của người viết bài dựa trên reply và note công khai, không phải
một vòng gán nhãn độc lập mới. Không sửa CSV replay hoặc verdict để làm đẹp điểm.
FN/FP dưới đây luôn tính theo **nhãn CSV hiện tại**, trước adjudication.

| # | Case | Judge | Người | Ai đúng / căn cứ | Hành động sửa rubric hoặc nhãn |
|---|---|---|---|---|---|
| 1 | H-008 | PASS (FN) | FAIL | Người: “Em… anh… nha… check” quá suồng sã theo style LogiX. | Yêu cầu xưng hô anh/chị, giọng CS chuyên nghiệp; thêm negative example này. |
| 2 | H-017 | PASS (FN) | FAIL | Người theo note: “bạn ơi… rồi nha” không phù hợp ngữ cảnh khách lớn tuổi. | Đưa ngữ cảnh người nhận vào rubric; không suy tuổi từ reply nếu thiếu context. |
| 3 | H-029 | PASS (FN) | FAIL | Người: “không cần nhắn thêm” ra lệnh, dù mở đầu có “Dạ, vui lòng”. | Chấm toàn câu; từ lịch sự không bù cho câu chặn khách hỏi tiếp. |
| 4 | H-042 | FAIL (FP) | PASS | Người: câu ngắn vẫn lịch sự, có kết quả và thời gian tiền về. | Không bắt buộc lời xin lỗi trong mọi reply; độ dài không là tiêu chí tone. |
| 5 | H-051 | FAIL (FP) | PASS | Người: note cho phép thuật ngữ “refund”. | Cho phép từ mượn thuộc glossary; không đánh FAIL chỉ vì có tiếng Anh. |
| 6 | H-063 | PASS (FN) | FAIL | Người theo note: hứa “sẽ hoàn thêm” ngoài kết quả hệ thống. | Ghi rõ không hứa thêm ngoài thẩm quyền; tách tone khỏi factuality và dùng code cho tiền. |
| 7 | H-070 | PASS (FN) | FAIL | Người: emoji cười không phù hợp khiếu nại. | Thêm quy tắc không dùng emoji đùa/cười trong phản hồi khiếu nại. |
| 8 | H-081 | FAIL (FP trước sửa nhãn) | PASS | Note CSV nói người đọc nhầm ticket, judge đúng; reply riêng lẻ không đủ xác minh điều này. | Đề xuất người thứ hai xem ticket gốc; nếu xác nhận thì đổi human thành FAIL trong dataset mới có version, không đổi CSV tham chiếu. |
| 9 | H-088 | FAIL (FP) | PASS | Người: lặp “Dạ” là lỗi gõ nhẹ, không đổi giọng hay nội dung. | Phân biệt typo nhẹ với sự thiếu tôn trọng; không tự động FAIL do lặp một từ. |
| 10 | H-094 | PASS (FN) | FAIL | Người theo chuẩn fixture: reply mất dấu tiếng Việt, chất lượng bản địa hóa không đạt. | Quy định rõ yêu cầu tiếng Việt có dấu; chấm lỗi này nhất quán theo style guide. |
| 11 | HL-015 | PASS (FN) | FAIL | Người theo note: nói 55.000đ, ledger 40.000đ. | Factual correctness là điều kiện bắt buộc; so tiền bằng code trước judge ngôn ngữ. |
| 12 | HL-016 | PASS (FN) | FAIL | Người theo note: xin lỗi dài nhưng nói 55.000đ, ledger 35.000đ. | Không thưởng độ dài/lời xin lỗi để bù số tiền sai; thêm cặp ngắn đúng / dài sai. |
| 13 | HL-020 | PASS (FN) | FAIL | Người theo note: nói 90.000đ, ledger 120.000đ. | Kiểm sai tiền cả hướng tăng lẫn giảm; judge không tự đoán ledger. |
| 14 | HL-028 | PASS (FN) | FAIL | Người theo note: nói 50.000đ, ledger 35.000đ, kèm lời xin lỗi lặp. | Chỉ xét helpful sau khi kiểm kết quả; không dùng số lời lịch sự làm proxy. |
| 15 | HL-035 | PASS (FN) | FAIL | Người theo note: nói 50.000đ, ledger 35.000đ dù văn phong lịch sự. | Rubric helpful yêu cầu câu trả lời đúng yêu cầu và đúng kết quả; dùng assertion reply/ledger cho FM-08. |

Các case helpful chỉ có ledger trong note, không có raw ledger/ticket trong CSV;
audit trên đây dựa vào evidence đó và cần kiểm lại nguồn khi có dữ liệu gốc.
Các hành động rubric là đề xuất cho phiên bản judge tiếp theo: replay không chạy
lại model, nên audit này không chứng minh prompt sửa đã tăng chất lượng judge.

## Rogan–Gladen và giới hạn

Công thức: `p_corrected = (p_observed + specificity - 1) /
(sensitivity + specificity - 1)`, với sensitivity=recall, specificity=TN/(TN+FP).
Clip về [0,1]; nếu sensitivity+specificity≤1 thì không dùng phép hiệu chỉnh và
báo không xác định. Input phải là xác suất hữu hạn trong [0,1].

| Tiêu chí | Observed FAIL | Sensitivity | Specificity | Corrected FAIL | Human FAIL |
|---|---:|---:|---:|---:|---:|
| tone_ok | 0.280 | 0.800 | 66/70 ≈ 0.943 | 0.300 | 0.300 |
| helpful | 0.090 | 0.300 | 1.000 | 0.300 | 0.300 |

Hiệu chỉnh ở đây khớp tỷ lệ nhãn người vì dùng cùng tập dữ liệu để ước lượng
sensitivity/specificity và observed rate; đây không phải xác nhận độc lập.
Rogan–Gladen sửa ước lượng tỷ lệ quần thể, không sửa verdict từng item và không
làm helpful đủ điều kiện gate. Helpful có accuracy 79% nhưng bỏ sót 70% lỗi
(21/30), κ=0.375 và R=0.300 dưới sàn: một agent trả lời sai tiền vẫn có thể được
cho PASS nhờ lời xin lỗi dài. Precision=1.0 không giải quyết vấn đề bỏ sót đó.

Tone còn 6 FN và 4 FP; đạt sàn không có nghĩa là đáng tin với tiền/approval.
Tiền và phê duyệt luôn dùng code; tone judge chỉ đánh phong cách. Dữ liệu replay
công khai có nhiều reply mẫu lặp lại, chưa có held-out thật; cần nhãn độc lập mới,
context ticket/ledger đầy đủ, adjudication hai người cho case khó và calibration
lại sau khi sửa rubric/model. Không chuyển các tỷ lệ này sang production nếu
phân phối lỗi hoặc sensitivity/specificity đã thay đổi. H-081 nhắc rằng nhãn
người cũng có thể sai; cần version nhãn và lưu lịch sử sửa thay vì sửa ngầm.

Các TODO bootstrap (M4) và pass@k/pass^k (M6) vẫn dành cho checkpoint sau.
