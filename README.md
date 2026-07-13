# API KQXS Archives Quarterly - Dữ liệu kết quả xổ số Việt Nam theo quý

Đây là kho SQLite tĩnh, công khai dành cho ứng dụng và dịch vụ cần xây dựng API KQXS từ dữ liệu lịch sử. Bộ dữ liệu bao phủ từ **01/02/2009 đến 30/06/2026**, gồm kết quả xổ số miền Bắc, xổ số miền Trung và xổ số miền Nam.

## Tổng quan dữ liệu API KQXS

| Thuộc tính | Giá trị |
| --- | --- |
| Định dạng | SQLite theo quý |
| Phạm vi | 01/02/2009 - 30/06/2026 |
| Khu vực | Miền Bắc, miền Trung, miền Nam |
| Đơn vị cập nhật | Một tệp cho mỗi quý |
| Phiên bản lược đồ | `system_a_kqxs_archive_schema_v1` |
| Tổng số kỳ quay | 41.787 |
| Tổng số kết quả giải | 809.397 |

Kho dữ liệu KQXS này là nguồn lưu trữ lịch sử dạng tệp, không phải dịch vụ API trực tiếp.

## Tải dữ liệu KQXS SQLite theo quý

Đường dẫn mỗi quý được xác định theo năm và quý. Ví dụ tải dữ liệu quý 2 năm 2026:

```sh
curl -LO https://raw.githubusercontent.com/itgi8vn/api-kqxs-archives-quarterly/main/archives/2026/Q2/kqxs_2026_Q2.sqlite
```

Tải toàn bộ 70 tệp SQLite bằng bản sao nông:

```sh
git clone --depth 1 https://github.com/itgi8vn/api-kqxs-archives-quarterly.git
```

## Cấu trúc thư mục archive

Kho chỉ dùng một mẫu đường dẫn ổn định:

```text
archives/YYYY/QN/kqxs_YYYY_QN.sqlite
```

Trong đó `YYYY` là năm và `QN` là quý từ `Q1` đến `Q4`. Quý 1 năm 2009 là quý đầu tiên và bắt đầu từ ngày 01/02/2009.

## Cấu trúc database SQLite

Mỗi tệp có các bảng công khai sau:

- `archive_schema_version`: phiên bản lược đồ.
- `archive_manifest`: phạm vi ngày, số dòng và thông tin kiểm tra nội bộ.
- `archive_checksums`: SHA-256 của nội dung logic theo bảng.
- `regions`: danh mục miền xổ số.
- `lottery_provinces`: danh mục tỉnh, thành phố và miền tương ứng.
- `lottery_schedules`: lịch quay theo tỉnh và thứ trong tuần.
- `prize_specs`: số lượng giải, độ rộng chuỗi số và thứ tự giải.
- `lottery_draws`: kỳ quay với khóa logic `YYYY-MM-DD:PROVINCE_CODE`.
- `lottery_results`: kết quả với khóa logic `draw_key:PRIZE_CODE:PRIZE_ORDER`.

`result_number` luôn có kiểu `TEXT`. Số 0 ở đầu là một phần của kết quả và phải được giữ nguyên khi đọc, xuất hoặc chuyển đổi dữ liệu.

## Ví dụ truy vấn dữ liệu KQXS

Lấy kết quả của Bắc Ninh ngày 01/04/2026 theo đúng thứ tự giải:

```sql
SELECT
  d.draw_date,
  d.province_code,
  r.prize_code,
  r.prize_order,
  r.result_number
FROM lottery_draws AS d
JOIN lottery_results AS r ON r.draw_key = d.draw_key
JOIN prize_specs AS p
  ON p.region_code = d.region_code
 AND p.prize_code = r.prize_code
WHERE d.draw_date = '2026-04-01'
  AND d.province_code = 'BN'
ORDER BY p.sort_order, r.prize_order;
```

Kiểm tra phạm vi và số kỳ quay trong một tệp quý:

```sql
SELECT
  MIN(draw_date) AS ngay_dau,
  MAX(draw_date) AS ngay_cuoi,
  COUNT(*) AS so_ky_quay
FROM lottery_draws;
```

Đếm số kết quả theo miền:

```sql
SELECT d.region_code, COUNT(*) AS so_ket_qua
FROM lottery_results AS r
JOIN lottery_draws AS d ON d.draw_key = r.draw_key
GROUP BY d.region_code
ORDER BY d.region_code;
```

## Tích hợp archive với API KQXS

Chủ ứng dụng có thể tải tệp SQLite cần thiết, mở ở chế độ chỉ đọc, truy vấn các bảng chuẩn hóa và cung cấp API KQXS của riêng mình. Cách này phù hợp cho tra cứu kết quả xổ số lịch sử, nhập dữ liệu theo lô hoặc làm nguồn dữ liệu cục bộ.

Kho này **không phải endpoint HTTP API trực tiếp**, không cung cấp dữ liệu thời gian thực và không cam kết thời gian hoạt động của một dịch vụ mạng.

## Kiểm tra tính toàn vẹn

Mở một tệp:

```sh
sqlite3 kqxs_2026_Q2.sqlite
```

Chạy các kiểm tra SQLite:

```sql
PRAGMA quick_check;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

`quick_check` và `integrity_check` phải trả về `ok`; `foreign_key_check` không được trả về dòng lỗi.

Kiểm tra phiên bản, thông tin quý và checksum logic:

```sql
SELECT * FROM archive_schema_version;
SELECT * FROM archive_manifest;
SELECT artifact, row_count, sha256
FROM archive_checksums
ORDER BY artifact;
```

## Phạm vi và lưu ý dữ liệu

- Chỉ gồm kết quả xổ số đã hoàn tất và dữ liệu KQXS lịch sử.
- Không có kết quả trực tiếp, dữ liệu đang quay hoặc hình ảnh vé số.
- Không nên diễn giải thứ tự thuộc tính JSON thay cho `sort_order` và `prize_order` trong SQLite.
- Các kỳ có toàn bộ giá trị bằng 0 biểu thị ngày không quay thưởng hoặc không có nguồn dữ liệu, đã được chuẩn hóa để giữ cấu trúc đầy đủ và nhất quán.
- Kho công khai không chứa mã thu thập dữ liệu, thông tin đăng nhập hoặc bằng chứng nguồn riêng tư.

## Câu hỏi thường gặp về API KQXS

### API KQXS là gì?

API KQXS là giao diện do một ứng dụng cung cấp để hệ thống khác truy vấn kết quả xổ số. Bộ SQLite theo quý trong kho này có thể làm nguồn dữ liệu lịch sử cho ứng dụng đó.

### Kho này có cung cấp API trực tiếp không?

Không. Đây là kho tệp SQLite tĩnh. Người dùng tải dữ liệu và tự xây dựng endpoint phù hợp với ứng dụng của mình.

### Làm thế nào để tải một quý?

Chọn năm và quý theo mẫu `archives/YYYY/QN/kqxs_YYYY_QN.sqlite`, sau đó tải tệp bằng đường dẫn raw của GitHub.

### Vì sao phải giữ kết quả ở kiểu TEXT?

Một số kết quả có số 0 ở đầu. Kiểu số có thể làm mất các số 0 này, còn `TEXT` bảo toàn chính xác độ rộng của kết quả.

### Dữ liệu có đủ cả ba miền không?

Có. Bộ dữ liệu bao gồm xổ số miền Bắc, xổ số miền Trung và xổ số miền Nam trong phạm vi ngày đã công bố.
