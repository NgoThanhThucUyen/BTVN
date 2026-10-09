import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "category_853.db")
TABLE = "products"


# ======================= TIỆN ÍCH =======================
def get_conn():
    if not os.path.exists(DB_FILE):
        print(f"Không tìm thấy file CSDL: {DB_FILE}")
        print("Hãy chạy chương trình nhập Excel -> SQLite trước.")
        raise SystemExit(1)
    return sqlite3.connect(DB_FILE)


def resolve_columns(conn):
    """Tìm tên cột thật trong bảng (phòng khi tên cột bị cắt/khác nhẹ)."""
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{TABLE}")')]

    def find(prefix, exact=False):
        for c in cols:
            if (c.lower() == prefix) if exact else c.lower().startswith(prefix):
                return c
        raise SystemExit(f"Không tìm thấy cột bắt đầu bằng '{prefix}' trong bảng. Các cột có: {cols}")

    return {
        "id": find("id", exact=True),
        "name": find("name"),
        "rating": find("rating"),
        "reviews": find("review"),
        "original": find("original"),
        "price": find("price", exact=True),
        "qty": find("quantity"),
        "url": find("url", exact=True),
    }


def money(v):
    return "-" if v is None else f"{int(v):,}".replace(",", ".") + "đ"


def short(text, n=45):
    text = "" if text is None else str(text)
    return text if len(text) <= n else text[: n - 3] + "..."


def input_int(prompt, default=None, min_value=None):
    while True:
        s = input(prompt).strip()
        if s == "" and default is not None:
            return default
        try:
            v = int(s.replace(".", "").replace(",", ""))
            if min_value is not None and v < min_value:
                print(f"  Giá trị phải >= {min_value}.")
                continue
            return v
        except ValueError:
            print("  Vui lòng nhập một số nguyên hợp lệ.")


def print_table(rows, C):
    """In danh sách sản phẩm. rows = (id, name, rating, reviews, original, price, qty)."""
    if not rows:
        print("\n  (Không có kết quả)")
        return
    print()
    header = f"{'ID':>10} | {'Tên sản phẩm':<45} | {'Sao':>4} | {'Đánh giá':>8} | {'Giá gốc':>11} | {'Giá bán':>11} | {'Đã bán':>7}"
    print(header)
    print("-" * len(header))
    for r in rows:
        _id, name, rating, reviews, original, price, qty = r
        print(
            f"{_id:>10} | {short(name):<45} | "
            f"{(rating if rating is not None else 0):>4} | "
            f"{(reviews if reviews is not None else 0):>8} | "
            f"{money(original):>11} | {money(price):>11} | "
            f"{(qty if qty is not None else 0):>7}"
        )
    print(f"\n  => {len(rows)} dòng.")


def select_clause(C):
    return (
        f'SELECT "{C["id"]}", "{C["name"]}", "{C["rating"]}", "{C["reviews"]}", '
        f'"{C["original"]}", "{C["price"]}", "{C["qty"]}" FROM "{TABLE}"'
    )


# ======================= 7 CHỨC NĂNG =======================
def chuc_nang_1(conn, C):
    """Xem danh sách sản phẩm (có phân trang)."""
    page_size = input_int("Số dòng mỗi trang (mặc định 10): ", default=10, min_value=1)
    total = conn.execute(f'SELECT COUNT(*) FROM "{TABLE}"').fetchone()[0]
    pages = max(1, -(-total // page_size))
    page = 1
    while True:
        offset = (page - 1) * page_size
        rows = conn.execute(
            select_clause(C) + f' ORDER BY "{C["id"]}" LIMIT ? OFFSET ?',
            (page_size, offset),
        ).fetchall()
        print(f"\n--- Trang {page}/{pages} (tổng {total} sản phẩm) ---")
        print_table(rows, C)
        cmd = input("[n] trang sau | [p] trang trước | [số] nhảy tới trang | [q] thoát: ").strip().lower()
        if cmd == "n" and page < pages:
            page += 1
        elif cmd == "p" and page > 1:
            page -= 1
        elif cmd.isdigit() and 1 <= int(cmd) <= pages:
            page = int(cmd)
        elif cmd == "q":
            break


def chuc_nang_2(conn, C):
    """Tìm kiếm sản phẩm theo tên."""
    kw = input("Nhập từ khóa trong tên sách: ").strip()
    if not kw:
        print("  Từ khóa không được để trống.")
        return
    rows = conn.execute(
        select_clause(C) + f' WHERE "{C["name"]}" LIKE ? ORDER BY "{C["qty"]}" DESC',
        (f"%{kw}%",),
    ).fetchall()
    print_table(rows, C)


def chuc_nang_3(conn, C):
    """Lọc sản phẩm theo khoảng giá bán."""
    low = input_int("Giá thấp nhất (VNĐ, mặc định 0): ", default=0, min_value=0)
    high = input_int("Giá cao nhất (VNĐ, mặc định 1.000.000): ", default=1_000_000, min_value=0)
    if low > high:
        low, high = high, low
    rows = conn.execute(
        select_clause(C) + f' WHERE "{C["price"]}" BETWEEN ? AND ? ORDER BY "{C["price"]}" ASC',
        (low, high),
    ).fetchall()
    print(f"\nSản phẩm có giá từ {money(low)} đến {money(high)}:")
    print_table(rows, C)


def chuc_nang_4(conn, C):
    """Top N sản phẩm bán chạy nhất."""
    n = input_int("Hiển thị top bao nhiêu (mặc định 10): ", default=10, min_value=1)
    rows = conn.execute(
        select_clause(C) + f' WHERE "{C["qty"]}" IS NOT NULL ORDER BY "{C["qty"]}" DESC LIMIT ?',
        (n,),
    ).fetchall()
    print(f"\nTop {n} sản phẩm bán chạy nhất:")
    print_table(rows, C)


def chuc_nang_5(conn, C):
    """Top N sản phẩm được đánh giá cao nhất."""
    n = input_int("Hiển thị top bao nhiêu (mặc định 10): ", default=10, min_value=1)
    min_rv = input_int("Số lượt đánh giá tối thiểu (mặc định 5): ", default=5, min_value=0)
    rows = conn.execute(
        select_clause(C)
        + f' WHERE "{C["reviews"]}" >= ? ORDER BY "{C["rating"]}" DESC, "{C["reviews"]}" DESC LIMIT ?',
        (min_rv, n),
    ).fetchall()
    print(f"\nTop {n} sản phẩm đánh giá cao nhất (có từ {min_rv} lượt đánh giá trở lên):")
    print_table(rows, C)


def chuc_nang_6(conn, C):
    """Top N sản phẩm giảm giá nhiều nhất (theo %)."""
    n = input_int("Hiển thị top bao nhiêu (mặc định 10): ", default=10, min_value=1)
    rows = conn.execute(
        f'''SELECT "{C["id"]}", "{C["name"]}", "{C["original"]}", "{C["price"]}",
                   ROUND(("{C["original"]}" - "{C["price"]}") * 100.0 / "{C["original"]}", 1) AS pct
            FROM "{TABLE}"
            WHERE "{C["original"]}" > 0 AND "{C["price"]}" IS NOT NULL
            ORDER BY pct DESC LIMIT ?''',
        (n,),
    ).fetchall()
    if not rows:
        print("\n  (Không có kết quả)")
        return
    print(f"\nTop {n} sản phẩm giảm giá nhiều nhất:\n")
    header = f"{'ID':>10} | {'Tên sản phẩm':<45} | {'Giá gốc':>11} | {'Giá bán':>11} | {'Giảm':>6}"
    print(header)
    print("-" * len(header))
    for _id, name, original, price, pct in rows:
        print(f"{_id:>10} | {short(name):<45} | {money(original):>11} | {money(price):>11} | {pct:>5}%")


def chuc_nang_7(conn, C):
    """Thống kê tổng quan."""
    row = conn.execute(
        f'''SELECT COUNT(*),
                   AVG("{C["price"]}"), MIN("{C["price"]}"), MAX("{C["price"]}"),
                   SUM("{C["qty"]}"),
                   AVG(CASE WHEN "{C["reviews"]}" > 0 THEN "{C["rating"]}" END),
                   SUM("{C["reviews"]}"),
                   SUM(CASE WHEN "{C["qty"]}" IS NULL THEN 1 ELSE 0 END)
            FROM "{TABLE}"'''
    ).fetchone()
    total, avg_p, min_p, max_p, sum_q, avg_r, sum_rv, null_q = row

    print("\n========== THỐNG KÊ TỔNG QUAN ==========")
    print(f"  Tổng số sản phẩm        : {total}")
    print(f"  Giá bán trung bình      : {money(avg_p)}")
    print(f"  Giá bán thấp nhất       : {money(min_p)}")
    print(f"  Giá bán cao nhất        : {money(max_p)}")
    print(f"  Tổng số lượng đã bán    : {(sum_q or 0):,}".replace(",", "."))
    print(f"  Tổng lượt đánh giá      : {(sum_rv or 0):,}".replace(",", "."))
    print(f"  Điểm sao trung bình     : {round(avg_r, 2) if avg_r is not None else '-'} (chỉ tính SP có đánh giá)")
    print(f"  SP chưa có số lượng bán : {null_q}")

    print("\n  Phân bố theo mức giá:")
    bands = [("Dưới 50.000đ", 0, 50_000), ("50.000 - 100.000đ", 50_000, 100_000),
             ("100.000 - 200.000đ", 100_000, 200_000), ("Trên 200.000đ", 200_000, None)]
    for label, lo, hi in bands:
        if hi is None:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{TABLE}" WHERE "{C["price"]}" >= ?', (lo,)).fetchone()[0]
        else:
            cnt = conn.execute(
                f'SELECT COUNT(*) FROM "{TABLE}" WHERE "{C["price"]}" >= ? AND "{C["price"]}" < ?', (lo, hi)
            ).fetchone()[0]
        print(f"    {label:<20}: {cnt}")


# ======================= MENU CHÍNH =======================
MENU = [
    ("Xem danh sách sản phẩm (phân trang)", chuc_nang_1),
    ("Tìm kiếm sản phẩm theo tên", chuc_nang_2),
    ("Lọc sản phẩm theo khoảng giá", chuc_nang_3),
    ("Top sản phẩm bán chạy nhất", chuc_nang_4),
    ("Top sản phẩm đánh giá cao nhất", chuc_nang_5),
    ("Top sản phẩm giảm giá nhiều nhất", chuc_nang_6),
    ("Thống kê tổng quan", chuc_nang_7),
]


def show_menu():
    print("\n" + "=" * 46)
    print("      QUẢN LÝ & TRUY VẤN SẢN PHẨM (SQLite)")
    print("=" * 46)
    for i, (title, _) in enumerate(MENU, 1):
        print(f"  {i}. {title}")
    print("  0. Thoát")
    print("=" * 46)


def main():
    conn = get_conn()
    C = resolve_columns(conn)
    while True:
        show_menu()
        choice = input("Chọn chức năng (0-7): ").strip()
        if choice == "0":
            print("Tạm biệt!")
            break
        if choice.isdigit() and 1 <= int(choice) <= len(MENU):
            try:
                MENU[int(choice) - 1][1](conn, C)
            except sqlite3.Error as e:
                print(f"\n  Lỗi CSDL: {e}")
            input("\nNhấn Enter để quay lại menu...")
        else:
            print("  Lựa chọn không hợp lệ, vui lòng nhập từ 0 đến 7.")
    conn.close()


if __name__ == "__main__":
    main()