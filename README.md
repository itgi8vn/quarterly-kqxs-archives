# API KQXS – Kho dữ liệu xổ số SQLite theo quý

Đây là kho công khai chứa **dữ liệu xổ số lịch sử cho API KQXS** dưới dạng SQLite theo quý. System A phục vụ API nóng/hiện tại từ năm 2026; C1 lưu trữ tĩnh toàn bộ lịch sử đã hoàn tất để tải xuống, kiểm tra và truy vấn cục bộ.

Kho bao gồm kết quả xổ số miền Bắc, xổ số miền Trung, xổ số miền Nam, XSMB ký hiệu đặc biệt, xổ số điện toán 1*2*3, Thần Tài 4 và xổ số điện toán 6x36. Đây không phải API trực tiếp và không cung cấp kết quả đang quay.

## Repo này dùng để làm gì?

Sử dụng kho này khi cần tra cứu, phân tích, đồng bộ hoặc xây dựng dịch vụ đọc **kết quả xổ số lịch sử**. Mỗi tệp là một cơ sở dữ liệu độc lập, có khóa logic, checksum và các bảng chuẩn hóa.

Repository: <https://github.com/itgi8vn/api-kqxs-archives-quarterly>

## Tải dữ liệu như thế nào?

Tải V1 quý 2 năm 2026:

```sh
curl -LO https://raw.githubusercontent.com/itgi8vn/api-kqxs-archives-quarterly/main/archives/2026/Q2/kqxs_2026_Q2.sqlite
```

Tải V2 cùng quý:

```sh
curl -LO https://raw.githubusercontent.com/itgi8vn/api-kqxs-archives-quarterly/main/archives/2026/Q2/kqxs_2026_Q2_v2.sqlite
```

Hoặc clone toàn bộ kho:

```sh
git clone --depth 1 https://github.com/itgi8vn/api-kqxs-archives-quarterly.git
```

## Cấu trúc file theo quý

```text
archives/YYYY/QN/kqxs_YYYY_QN.sqlite
archives/YYYY/QN/kqxs_YYYY_QN_v2.sqlite
```

`YYYY` là năm; `QN` là `Q1` đến `Q4`. Phạm vi lịch sử bắt đầu từ `2009-02-01`. Chỉ các quý đã hoàn tất được xuất bản.

## V1 và V2 khác nhau ra sao?

- **V1** chứa KQXS truyền thống: danh mục miền/tỉnh, lịch quay, cơ cấu giải, kỳ quay và kết quả.
- **V2** giữ nguyên dữ liệu KQXS canonical của V1 và bổ sung XSMB ký hiệu đặc biệt cùng ba sản phẩm điện toán.
- V1 dùng tên không hậu tố; V2 dùng hậu tố `_v2.sqlite`.
- V2 có `PRAGMA user_version=2` và marker `api_kqxs_archive_schema_v2`.

Ứng dụng nên kiểm tra marker trong file, không suy đoán phiên bản chỉ từ tên.

```sql
PRAGMA user_version;
SELECT version, name FROM archive_schema_version;
```

## Các bảng dữ liệu

KQXS truyền thống:

- `regions`, `lottery_provinces`, `lottery_schedules`
- `prize_specs`, `lottery_draws`, `lottery_results`

V2 bổ sung:

- `xsmb_special_series_draws`, `xsmb_special_series_items`
- `electronic_products`, `electronic_schedules`
- `electronic_draws`, `electronic_results`

Các bảng `archive_schema_version`, `archive_manifest`, `archive_checksums` phục vụ nhận diện và kiểm tra nội dung. Giá trị kết quả là `TEXT` để giữ nguyên số 0 ở đầu.

## Ví dụ SQL đọc dữ liệu

### Kết quả KQXS

```sql
SELECT d.draw_date, d.province_code,
       r.prize_code, r.prize_order, r.result_number
FROM lottery_draws d
JOIN lottery_results r ON r.draw_key=d.draw_key
JOIN prize_specs p
  ON p.region_code=d.region_code AND p.prize_code=r.prize_code
WHERE d.draw_date='2026-04-01' AND d.province_code='BN'
ORDER BY p.sort_order, r.prize_order;
```

### XSMB ký hiệu đặc biệt

```sql
SELECT d.draw_date, i.item_order,
       i.number_text || i.suffix AS token
FROM xsmb_special_series_draws d
JOIN xsmb_special_series_items i USING(series_key)
WHERE d.draw_date='2026-04-01'
ORDER BY i.item_order;
```

### Xổ số điện toán

```sql
SELECT d.draw_date, d.product_code, d.normalization_kind,
       r.result_order, r.result_number
FROM electronic_draws d
JOIN electronic_results r USING(electronic_draw_key)
WHERE d.draw_date='2026-04-01'
ORDER BY d.product_code, r.result_order;
```

## Khi nào dùng System A API, khi nào dùng C1 archive?

**Dùng System A API** khi cần dữ liệu nóng/hiện tại từ `2026-01-01`, phản hồi HTTP hoặc trạng thái mới nhất.

**Dùng C1 archive** khi cần lịch sử đầy đủ, tải theo lô, truy vấn ngoại tuyến, đối soát hoặc lưu bản dữ liệu ổn định theo quý. C1 là kho tĩnh; không thay thế API thời gian thực.

## Quy tắc dữ liệu và giới hạn

- V1 được giữ nguyên; V2 là file sidecar riêng.
- XSMB ký hiệu đặc biệt chỉ chứa dòng sạch có đúng sáu token theo thứ tự, cùng hậu tố và không trùng phần số.
- Điện toán 1*2*3 có độ rộng `1,2,3`; Thần Tài 4 có độ rộng `4`; điện toán 6x36 có sáu giá trị rộng `2` và chỉ có lịch thứ Tư/thứ Bảy.
- Không có bảng cơ cấu giải mới cho sản phẩm V2; contract độ rộng/thứ tự được cố định theo schema V2.
- Không chứa `d6x45`, `d6x55` hoặc sản phẩm khác.
- Chín dòng electronic bị quarantine đã được loại, không tự sửa hoặc tự điền số 0.
- Các dòng ngày nghỉ được phê duyệt giữ tuple số 0 đúng độ rộng và có `normalization_kind='holiday_zero'`.
- Không chứa nguồn riêng tư, URL nguồn, provenance, host nội bộ, token hoặc credential.

## Kiểm tra file SQLite

```sql
PRAGMA quick_check;
PRAGMA integrity_check;
PRAGMA foreign_key_check;

SELECT * FROM archive_manifest;
SELECT artifact, row_count, sha256
FROM archive_checksums
ORDER BY artifact;
```

`quick_check` và `integrity_check` phải trả `ok`; `foreign_key_check` không trả dòng lỗi.

## Câu hỏi thường gặp

### Kho này có phải API KQXS trực tiếp không?

Không. Đây là kho SQLite theo quý để ứng dụng tải và tự truy vấn. API nóng/hiện tại thuộc System A.

### Dữ liệu có đủ ba miền không?

Có. KQXS canonical bao gồm xổ số miền Bắc, xổ số miền Trung và xổ số miền Nam trong phạm vi lịch sử đã công bố.

### Vì sao kết quả dùng kiểu TEXT?

Kiểu `TEXT` bảo toàn số 0 ở đầu và độ rộng chính xác của từng kết quả.

### Có thể ghi đè file quý đã xuất bản không?

Không. Cùng SHA là thao tác no-op; khác SHA là xung đột và phải được xem xét riêng.
