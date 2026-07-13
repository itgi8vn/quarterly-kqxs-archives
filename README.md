# Kho dữ liệu kết quả xổ số theo quý

Kho công khai này chỉ chứa dữ liệu kết quả xổ số đã hoàn tất ở định dạng SQLite. Phạm vi dữ liệu liên tục từ **01/02/2009 đến 30/06/2026**.

## Cấu trúc thư mục

Mỗi quý có một tệp:

```text
archives/YYYY/QN/kqxs_YYYY_QN.sqlite
```

Ví dụ quý 2 năm 2026:

```text
archives/2026/Q2/kqxs_2026_Q2.sqlite
```

Phiên bản lược đồ: `system_a_kqxs_archive_schema_v1`.

## Tải dữ liệu

Tải một quý:

```sh
curl -LO https://raw.githubusercontent.com/itgi8vn/quarterly-kqxs-archives/main/archives/2026/Q2/kqxs_2026_Q2.sqlite
```

Tải toàn bộ kho bằng Git:

```sh
git clone --depth 1 https://github.com/itgi8vn/quarterly-kqxs-archives.git
```

## Mở và kiểm tra SQLite

```sh
sqlite3 kqxs_2026_Q2.sqlite
```

Trong trình SQLite:

```sql
PRAGMA quick_check;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SELECT * FROM archive_schema_version;
SELECT artifact, row_count, sha256 FROM archive_checksums ORDER BY artifact;
SELECT COUNT(*) FROM lottery_draws;
SELECT COUNT(*) FROM lottery_results;
```

Kết quả của `quick_check` và `integrity_check` phải là `ok`. Truy vấn `foreign_key_check` không được trả về dòng lỗi.

## Các bảng dữ liệu

- `archive_schema_version`: phiên bản lược đồ.
- `archive_manifest`: phạm vi ngày, số lượng dòng và thông tin kiểm tra nội bộ.
- `archive_checksums`: mã SHA-256 của nội dung logic theo bảng.
- `regions`: miền xổ số.
- `lottery_provinces`: tỉnh và thành phố.
- `lottery_schedules`: lịch quay theo thứ.
- `prize_specs`: số lượng giải và độ rộng chuỗi số.
- `lottery_draws`: kỳ quay theo ngày và tỉnh.
- `lottery_results`: kết quả từng giải theo đúng thứ tự.

`result_number` luôn là kiểu `TEXT`. Số 0 ở đầu có ý nghĩa và phải được giữ nguyên khi đọc hoặc chuyển đổi dữ liệu.

Các kỳ có toàn bộ giá trị bằng 0 biểu thị ngày không quay thưởng hoặc không có nguồn dữ liệu, đã được chuẩn hóa để giữ cấu trúc đầy đủ và nhất quán.

Kho này không chứa mã thu thập dữ liệu, thông tin đăng nhập hoặc bằng chứng nguồn riêng tư.
