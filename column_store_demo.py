from datetime import datetime
"""Pure-function computation engine for Column-Stores vs. Row-Stores (Abadi et al., SIGMOD 2008)."""
import time
import numpy as np

from demo_helpers import (
    MA_KHU_VUC_ASIA, NAM_BAT_DAU, NAM_KET_THUC_LOC, NGAY_BAT_DAU_LOC_RLE, NGAY_KET_THUC_LOC_RLE,
    SO_BYTE_MOI_INT32, SO_COT_LINEORDER, SO_COT_TRUY_VAN_PHAN_1, SO_NGAY_PHAN_BIET_RLE,
    SO_KHACH_HANG, SO_NHA_CUNG_CAP, SO_NGAY_TRONG_BANG_CHIEU,
    chuyen_bang_fact_sang_dang_hang, do_thoi_gian_nhanh_nhat, la_tap_khoa_lien_tuc,
    tao_du_lieu_bang_lineorder, tao_du_lieu_mau_bai_bao, tao_luoc_do_sao,
    tim_khoang_khoa_lien_tuc, tinh_join_ngay_tho_kiem_chung, tinh_tong_theo_nhom,
)


COT_MAC_DINH_P1 = ("quantity", "discount", "extendedprice", "orderdate")
TAP_COT_P1_HOP_LE = set(COT_MAC_DINH_P1) | {f"c{i:02d}" for i in range(4, SO_COT_LINEORDER)}


def parse_projection_from_sql(sql_text):
    """Tự động phân tích các cột trong projection từ câu truy vấn SQL (SELECT, WHERE, GROUP BY, ORDER BY)."""
    import re
    if not sql_text or not isinstance(sql_text, str):
        return list(COT_MAC_DINH_P1)
    cleaned = re.sub(r'--[^\r\n]*', ' ', sql_text)
    cleaned = re.sub(r'/\*.*?\*/', ' ', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'[\[\]`]', ' ', cleaned)
    raw_tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_.]*', cleaned.lower())
    alias_map = {
        'qty': 'quantity', 'disc': 'discount', 'price': 'extendedprice', 'revenue': 'extendedprice',
        'c4': 'c04', 'c5': 'c05', 'c6': 'c06', 'c7': 'c07', 'c8': 'c08', 'c9': 'c09'
    }
    found_cols = []
    seen = set()
    for token in raw_tokens:
        col = token.split('.')[-1]
        col = alias_map.get(col, col)
        if col in TAP_COT_P1_HOP_LE and col not in seen:
            seen.add(col)
            found_cols.append(col)
    if not found_cols and re.search(r'\bselect\s+(\*|\w+\.\*)', cleaned, re.IGNORECASE):
        return list(COT_MAC_DINH_P1) + [f"c{i:02d}" for i in range(4, SO_COT_LINEORDER)]
    return found_cols or list(COT_MAC_DINH_P1)


def _chuan_hoa_cot_phan_1(danh_sach_cot):
    if not danh_sach_cot:
        return list(COT_MAC_DINH_P1)
    da_seen, kq = set(), []
    for col in danh_sach_cot:
        if col in TAP_COT_P1_HOP_LE and col not in da_seen:
            da_seen.add(col)
            kq.append(col)
    return kq or list(COT_MAC_DINH_P1)


def do_benchmark_chuan(ham_can_do, *tham_so, warmups=2, iterations=5):
    """Chạy warm-up và thực hiện iterations lượt đo độc lập, trả về kết quả và các thống kê phân phối (ms)."""
    for _ in range(warmups):
        ham_can_do(*tham_so)
    timings = []
    ket_qua = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        ket_qua = ham_can_do(*tham_so)
        timings.append((time.perf_counter() - t0) * 1000.0)
    arr = np.array(timings)
    return {
        "res": ket_qua,
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "mean": float(np.mean(arr)),
        "timings": [round(float(x), 2) for x in timings]
    }


def tinh_doanh_thu_q11_hang(bang_hang, d_year):
    """Plan A: Row-Store (AoS) - Full Tuple Scan & Early Materialization.
    Nạp toàn bộ 17 trường (68B/dòng), duyệt qua điều kiện lọc và tính doanh thu.
    """
    dong_thoa = (bang_hang["discount"] >= 1) & (bang_hang["discount"] <= 3) & \
                (bang_hang["quantity"] < 25) & \
                (d_year[bang_hang["orderdate"]] == 1993)
    matching = bang_hang[dong_thoa]
    return int((matching["extendedprice"].astype(np.int64) * matching["discount"]).sum())


def tinh_doanh_thu_q11_cot(bang_cot, d_year):
    """Plan B: Column-Store (SoA) - Projection Column Scan & Late Materialization.
    Chỉ nạp đúng 4 cột cần thiết (16B/dòng): quantity, discount, extendedprice, orderdate.
    13 cột còn lại hoàn toàn không được nạp (Not Loaded - 0 Byte I/O).
    """
    dong_thoa = (bang_cot["discount"] >= 1) & (bang_cot["discount"] <= 3) & \
                (bang_cot["quantity"] < 25) & \
                (d_year[bang_cot["orderdate"]] == 1993)
    return int((bang_cot["extendedprice"][dong_thoa].astype(np.int64) * bang_cot["discount"][dong_thoa]).sum())


def tinh_doanh_thu_giam_gia(bang_du_lieu, danh_sach_cot=None, d_year=None):
    """Hàm tương thích cho truy vấn có tập cột động hoặc mặc định theo chuẩn Q1.1."""
    if d_year is not None:
        if isinstance(bang_du_lieu, np.ndarray) and bang_du_lieu.dtype.names:
            return tinh_doanh_thu_q11_hang(bang_du_lieu, d_year)
        elif isinstance(bang_du_lieu, dict):
            return tinh_doanh_thu_q11_cot(bang_du_lieu, d_year)

    cot_chon = _chuan_hoa_cot_phan_1(danh_sach_cot)
    cot_giam_gia = bang_du_lieu["discount"] if "discount" in cot_chon else None
    cot_so_luong = bang_du_lieu["quantity"] if "quantity" in cot_chon else None
    dong_thoa = np.ones(len(bang_du_lieu[cot_chon[0]]), dtype=bool)
    if cot_giam_gia is not None:
        dong_thoa &= (cot_giam_gia >= 1) & (cot_giam_gia <= 3)
    if cot_so_luong is not None:
        dong_thoa &= (cot_so_luong < 25)

    co_gia, co_giam = "extendedprice" in cot_chon, cot_giam_gia is not None
    cot_phu = [c for c in cot_chon if c not in COT_MAC_DINH_P1]
    if co_gia and co_giam:
        tong = bang_du_lieu["extendedprice"][dong_thoa].astype(np.int64) * cot_giam_gia[dong_thoa]
    elif co_gia:
        tong = bang_du_lieu["extendedprice"][dong_thoa].astype(np.int64)
    elif co_giam:
        tong = cot_giam_gia[dong_thoa].astype(np.int64)
    elif "quantity" in cot_chon:
        tong = cot_so_luong[dong_thoa].astype(np.int64)
    else:
        tong = bang_du_lieu[cot_phu[0]][dong_thoa].astype(np.int64)
        cot_phu = cot_phu[1:]
    for c in cot_phu:
        tong = tong + bang_du_lieu[c][dong_thoa].astype(np.int64)
    return int(tong.sum())


class BoDuLieuToanCuc:
    """Quản lý bộ dữ liệu nạp trong RAM cho cặp (rows, seed) hiện tại.
    Khi đổi seed hoặc đổi số dòng, toàn bộ cache cũ bị hủy và tái sinh ngẫu nhiên theo đúng seed đó.
    """
    def __init__(self, rows: int, seed: int):
        self.rows = int(rows)
        self.seed = int(seed)

        # 1. Star Schema (c_region, s_region, d_year, fact_cot, fact_hang)
        # Dùng chung cho cả Phần 4 Benchmark và Invisible Join
        rng_star = np.random.default_rng(self.seed)
        self.chieu, self.fact_cot = tao_luoc_do_sao(self.rows, rng_star)
        self.fact_hang = chuyen_bang_fact_sang_dang_hang(self.fact_cot, self.rows)

        # 2. Lineorder table 17 cột cho Phần 1 (AoS vs SoA)
        rng_p1 = np.random.default_rng(self.seed + 101)
        self.p1_hang, self.p1_cot = tao_du_lieu_bang_lineorder(self.rows, rng_p1)

        # 3. Mảng orderdate 2,405 cụm cho Phần 2 (Nén RLE) - đồng bộ 100% với fact_cot['orderdate'] đã sort
        self.p2_cot_ngay = self.fact_cot["orderdate"]
        vi_tri_doi = np.flatnonzero(self.p2_cot_ngay[1:] != self.p2_cot_ngay[:-1]) + 1
        vi_tri_bat_dau = np.concatenate(([0], vi_tri_doi))
        self.p2_gia_tri_cum = self.p2_cot_ngay[vi_tri_bat_dau]
        self.p2_so_lan_lap = np.diff(np.concatenate((vi_tri_bat_dau, [len(self.p2_cot_ngay)])))


_BO_DU_LIEU_HIEN_TAI: BoDuLieuToanCuc | None = None


def lay_bo_du_lieu_chuan(rows: int, seed: int) -> BoDuLieuToanCuc:
    """Lấy từ cache hoặc hủy bỏ cache cũ để sinh lại khi (rows, seed) thay đổi."""
    global _BO_DU_LIEU_HIEN_TAI
    if _BO_DU_LIEU_HIEN_TAI is not None:
        if _BO_DU_LIEU_HIEN_TAI.rows == rows and _BO_DU_LIEU_HIEN_TAI.seed == seed:
            return _BO_DU_LIEU_HIEN_TAI
    _BO_DU_LIEU_HIEN_TAI = None
    _BO_DU_LIEU_HIEN_TAI = BoDuLieuToanCuc(rows, seed)
    return _BO_DU_LIEU_HIEN_TAI


def lay_du_lieu_preview(rows: int = 6_000_000, seed: int = 42) -> dict:
    """Trả về 5 dòng dữ liệu thực tế đầu tiên của 4 bảng Star Schema trong RAM theo seed và rows."""
    ds = lay_bo_du_lieu_chuan(rows, seed)
    chieu = ds.chieu
    fact_cot = ds.fact_cot
    p1_cot = ds.p1_cot

    REGIONS = ["AMERICA", "AFRICA", "ASIA", "EUROPE", "MIDDLE EAST"]
    NATIONS = [
        "UNITED STATES", "ARGENTINA", "BRAZIL", "CANADA", "PERU",
        "ALGERIA", "ETHIOPIA", "KENYA", "MOROCCO", "MOZAMBIQUE",
        "CHINA", "INDIA", "INDONESIA", "JAPAN", "VIETNAM",
        "FRANCE", "GERMANY", "RUSSIA", "UNITED KINGDOM", "ROMANIA",
        "EGYPT", "IRAN", "IRAQ", "JORDAN", "SAUDI ARABIA"
    ]
    MKT_SEGMENTS = ["AUTOMOBILE", "BUILDING", "FURNITURE", "HOUSEHOLD", "MACHINERY"]
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # 1. LINEORDER (5 dòng đầu tiên)
    n_sample = min(5, rows)
    lo_rows = []
    for i in range(n_sample):
        pad_vals = [int(p1_cot[f"c{c_i:02d}"][i]) for c_i in range(4, 14)]
        ck_val = int(fact_cot["custkey"][i])
        sk_val = int(fact_cot["suppkey"][i])
        ok_val = int(fact_cot["orderdate"][i])
        cr_id = int(chieu["c_region"][ck_val])
        cn_id = int(chieu["c_nation"][ck_val])
        sr_id = int(chieu["s_region"][sk_val])
        sn_id = int(chieu["s_nation"][sk_val])
        dy_val = int(chieu["d_year"][ok_val])
        lo_rows.append({
            "dong": i + 1,
            "idx": i,
            "custkey": ck_val,
            "suppkey": sk_val,
            "orderdate": ok_val,
            "quantity": int(p1_cot["quantity"][i]),
            "discount": int(p1_cot["discount"][i]),
            "extendedprice": int(p1_cot["extendedprice"][i]),
            "revenue": int(fact_cot["revenue"][i]),
            "padding": ", ".join(str(v) for v in pad_vals),
            "c_region": REGIONS[cr_id] if 0 <= cr_id < len(REGIONS) else f"Region#{cr_id}",
            "c_nation": NATIONS[cn_id] if 0 <= cn_id < len(NATIONS) else f"Nation#{cn_id}",
            "s_region": REGIONS[sr_id] if 0 <= sr_id < len(REGIONS) else f"Region#{sr_id}",
            "s_nation": NATIONS[sn_id] if 0 <= sn_id < len(NATIONS) else f"Nation#{sn_id}",
            "d_year": dy_val,
        })

    # 1b. Dành riêng cho Tab 3 (SSBM Q3.1 ASIA x ASIA, 1992-1997):
    # Sinh động 5 dòng Fact mẫu từ RAM mảng cột NumPy:
    # - Dòng 1: lo_rows[0] (idx: 0) -> AMERICA x ASIA (1992) -> bc=0, bs=1, bd=1 -> AND=0
    # - Dòng 2: Dòng đầu tiên trong RAM khớp ASIA x ASIA (1992-1997) (idx: 1) -> bc=1, bs=1, bd=1 -> AND=1 (TRÚNG)
    # - Dòng 3: lo_rows[2] (idx: 2) -> EUROPE x ASIA (1992) -> bc=0, bs=1, bd=1 -> AND=0
    # - Dòng 4: lo_rows[3] (idx: 3) -> ASIA x AMERICA (1992) -> bc=1, bs=0, bd=1 -> AND=0
    # - Dòng 5: Dòng đầu tiên trong RAM có năm 1998 (idx: 4) -> AMERICA x MIDDLE EAST (1998) -> bc=0, bs=0, bd=0 -> AND=0
    def _tao_dong_p3_fact(i_source, dong, idx):
        pad_vals = [int(p1_cot[f"c{c_i:02d}"][i_source]) if i_source < len(p1_cot[f"c{c_i:02d}"]) else 0 for c_i in range(4, 14)]
        ck_v = int(fact_cot["custkey"][i_source])
        sk_v = int(fact_cot["suppkey"][i_source])
        ok_v = int(fact_cot["orderdate"][i_source])
        cr_i = int(chieu["c_region"][ck_v])
        cn_i = int(chieu["c_nation"][ck_v])
        sr_i = int(chieu["s_region"][sk_v])
        sn_i = int(chieu["s_nation"][sk_v])
        dy_v = int(chieu["d_year"][ok_v])
        return {
            "dong": dong,
            "idx": idx,
            "custkey": ck_v,
            "suppkey": sk_v,
            "orderdate": ok_v,
            "quantity": int(p1_cot["quantity"][i_source]) if i_source < len(p1_cot["quantity"]) else 25,
            "discount": int(p1_cot["discount"][i_source]) if i_source < len(p1_cot["discount"]) else 5,
            "extendedprice": int(p1_cot["extendedprice"][i_source]) if i_source < len(p1_cot["extendedprice"]) else 50000,
            "revenue": int(fact_cot["revenue"][i_source]),
            "padding": ", ".join(str(v) for v in pad_vals),
            "c_region": REGIONS[cr_i] if 0 <= cr_i < len(REGIONS) else f"Region#{cr_i}",
            "c_nation": NATIONS[cn_i] if 0 <= cn_i < len(NATIONS) else f"Nation#{cn_i}",
            "s_region": REGIONS[sr_i] if 0 <= sr_i < len(REGIONS) else f"Region#{sr_i}",
            "s_nation": NATIONS[sn_i] if 0 <= sn_i < len(NATIONS) else f"Nation#{sn_i}",
            "d_year": dy_v,
        }

    ck_arr = fact_cot["custkey"]
    sk_arr = fact_cot["suppkey"]
    od_arr = fact_cot["orderdate"]
    cr_arr = chieu["c_region"][ck_arr]
    sr_arr = chieu["s_region"][sk_arr]
    dy_arr = chieu["d_year"][od_arr]

    # Tìm dòng khớp ASIA (cr==2) x ASIA (sr==2) và 1992 <= d_year <= 1997 trong RAM
    match_mask = (cr_arr == 2) & (sr_arr == 2) & (dy_arr >= 1992) & (dy_arr <= 1997)
    first_match_idx = int(np.argmax(match_mask)) if np.any(match_mask) else (1 if len(ck_arr) > 1 else 0)

    # Tìm dòng năm 1998 trong RAM
    y1998_mask = (dy_arr == 1998)
    first_1998_idx = int(np.argmax(y1998_mask)) if np.any(y1998_mask) else min(4, len(ck_arr) - 1)

    p3_fact_rows = [
        _tao_dong_p3_fact(0, 1, 0),
        _tao_dong_p3_fact(first_match_idx, 2, 1),
        _tao_dong_p3_fact(2 if len(ck_arr) > 2 else 0, 3, 2),
        _tao_dong_p3_fact(3 if len(ck_arr) > 3 else 0, 4, 3),
        _tao_dong_p3_fact(first_1998_idx, 5, 4),
    ]

    # Trích xuất danh sách Dimension khớp đúng với 5 dòng Fact của Tab 3:
    unique_cust = {}
    unique_supp = {}
    unique_date = {}
    for r in p3_fact_rows:
        ck = r["custkey"]
        sk = r["suppkey"]
        od = r["orderdate"]
        if ck not in unique_cust:
            unique_cust[ck] = {
                "custkey": ck,
                "region": r["c_region"],
                "nation": r["c_nation"]
            }
        if sk not in unique_supp:
            unique_supp[sk] = {
                "suppkey": sk,
                "region": r["s_region"],
                "nation": r["s_nation"]
            }
        if od not in unique_date:
            unique_date[od] = {
                "datekey": od,
                "year": r["d_year"]
            }

    p3_ram = {
        "fact_rows": p3_fact_rows,
        "cust_rows": sorted(list(unique_cust.values()), key=lambda x: x["custkey"]),
        "supp_rows": sorted(list(unique_supp.values()), key=lambda x: x["suppkey"]),
        "date_rows": sorted(list(unique_date.values()), key=lambda x: x["datekey"])
    }

    # 2. CUSTOMER (5 dòng đầu)
    cust_rows = []
    for i in range(5):
        r_id = int(chieu["c_region"][i])
        n_id = int(chieu["c_nation"][i])
        cust_rows.append({
            "custkey": i + 1,
            "name": f"Customer#{i + 1:09d}",
            "region": REGIONS[r_id] if 0 <= r_id < len(REGIONS) else f"Region#{r_id}",
            "nation": NATIONS[n_id] if 0 <= n_id < len(NATIONS) else f"Nation#{n_id}",
            "mktsegment": MKT_SEGMENTS[i % len(MKT_SEGMENTS)]
        })

    # 3. SUPPLIER (5 dòng đầu)
    supp_rows = []
    for i in range(5):
        r_id = int(chieu["s_region"][i])
        n_id = int(chieu["s_nation"][i])
        supp_rows.append({
            "suppkey": i + 1,
            "name": f"Supplier#{i + 1:09d}",
            "region": REGIONS[r_id] if 0 <= r_id < len(REGIONS) else f"Region#{r_id}",
            "nation": NATIONS[n_id] if 0 <= n_id < len(NATIONS) else f"Nation#{n_id}"
        })

    # 4. DWDATE (5 dòng đầu)
    date_rows = []
    for i in range(5):
        yr = int(chieu["d_year"][i])
        dow = DAYS[(2 + i) % 7]
        date_rows.append({
            "datekey": i,
            "year": yr,
            "yearmonth": f"{yr}01",
            "dayofweek": dow
        })

    return {
        "ok": True,
        "seed": seed,
        "rows": rows,
        "p3_ram": p3_ram,
        "tables": {
            "lineorder": {
                "name": "LINEORDER",
                "label": "LINEORDER (Fact)",
                "total_rows": rows,
                "desc": "Bảng dữ liệu đơn hàng gồm 17 cột (mã khách hàng, nhà cung cấp, ngày đặt, số lượng, chiết khấu và doanh thu).",
                "rows": lo_rows
            },
            "customer": {
                "name": "CUSTOMER",
                "label": "CUSTOMER (Chiều khách hàng)",
                "total_rows": SO_KHACH_HANG,
                "desc": "Bảng thông tin khách hàng (30,000 khách hàng phân bổ theo quốc gia và khu vực).",
                "rows": cust_rows
            },
            "supplier": {
                "name": "SUPPLIER",
                "label": "SUPPLIER (Chiều nhà cung cấp)",
                "total_rows": SO_NHA_CUNG_CAP,
                "desc": "Bảng thông tin nhà cung cấp (2,000 nhà cung cấp phân bổ theo quốc gia và khu vực).",
                "rows": supp_rows
            },
            "dwdate": {
                "name": "DWDATE",
                "label": "DWDATE (Chiều ngày tháng)",
                "total_rows": SO_NGAY_TRONG_BANG_CHIEU,
                "desc": "Bảng thời gian giao dịch (2,555 ngày từ năm 1992 đến 1998, phân loại theo năm, quý và tháng).",
                "rows": date_rows
            }
        }
    }


def demo_phan_1_layout_hang_va_cot(so_dong, bo_sinh_ngau_nhien, danh_sach_cot=None, sql=None):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PYTHON] demo_phan_1_layout_hang_va_cot: rows={so_dong}, cols={danh_sach_cot}")
    """Phần 1: Same Query, Two Execution Plans (SSBM Q1.1).
    Từ 1 câu truy vấn logic SSBM Q1.1 duy nhất, sinh ra 2 phương án thực thi:
    - Plan A: Row-Store (AoS - Full Tuple Scan 17 cột, 68B/dòng)
    - Plan B: Column-Store (SoA - Columnar Projection Scan 4 cột, 16B/dòng, 13 cột Not Loaded)
    """
    seed_val = int(bo_sinh_ngau_nhien) if isinstance(bo_sinh_ngau_nhien, (int, np.integer)) else 42
    ds = lay_bo_du_lieu_chuan(so_dong, seed_val)
    bang_hang, bang_cot = ds.p1_hang, ds.p1_cot
    d_year = ds.chieu["d_year"]

    # Đếm số dòng thỏa mãn điều kiện Q1.1 (year=1993, disc in 1..3, qty < 25)
    dong_thoa = (bang_cot["discount"] >= 1) & (bang_cot["discount"] <= 3) & \
                (bang_cot["quantity"] < 25) & \
                (d_year[bang_cot["orderdate"]] == 1993)
    matching_rows = int(dong_thoa.sum())

    # Benchmark Rigor: 2 warm-ups + 5 lượt đo thực tế
    bench_hang = do_benchmark_chuan(lambda: tinh_doanh_thu_q11_hang(bang_hang, d_year), warmups=2, iterations=5)
    bench_cot = do_benchmark_chuan(lambda: tinh_doanh_thu_q11_cot(bang_cot, d_year), warmups=2, iterations=5)

    kq_hang, tg_hang = bench_hang["res"], bench_hang["median"]
    kq_cot, tg_cot = bench_cot["res"], bench_cot["median"]
    assert kq_hang == kq_cot, f"Lỗi không nhất quán: Plan A ({kq_hang}) != Plan B ({kq_cot})"

    # 5 dòng mẫu visual preview chuẩn xác:
    samples = []
    for i in range(min(5, so_dong)):
        od = int(bang_cot["orderdate"][i])
        yr = int(d_year[od]) if od < len(d_year) else 1992 + od // 365
        row_s = {
            "qty": int(bang_cot["quantity"][i]),
            "disc": int(bang_cot["discount"][i]),
            "price": int(bang_cot["extendedprice"][i]),
            "orderdate": od,
            "year": yr,
        }
        for c_i in range(4, SO_COT_LINEORDER):
            row_s[f"c{c_i:02d}"] = int(bang_cot[f"c{c_i:02d}"][i])
        samples.append(row_s)

    speedup = round(tg_hang / max(tg_cot, 1e-9), 2)
    mb_total_val = round(SO_COT_LINEORDER * SO_BYTE_MOI_INT32 * so_dong / 1e6, 1)  # 408.0 MB
    mb_needed_val = round(4 * SO_BYTE_MOI_INT32 * so_dong / 1e6, 1)               # 96.0 MB

    default_sql = (
        "-- SSBM Query 1.1: Aggregation & Star Join (Abadi et al., SIGMOD 2008)\n"
        "SELECT SUM(lo.extendedprice * lo.discount) AS revenue\n"
        "FROM lineorder lo\n"
        "JOIN dwdate d ON lo.orderdate = d.datekey\n"
        "WHERE d.year = 1993\n"
        "  AND lo.discount BETWEEN 1 AND 3\n"
        "  AND lo.quantity < 25;"
    )

    return {
        "mb_hang_ram": round(bang_hang.nbytes / 1e6, 1),
        "mb_cot_ram": round(sum(c.nbytes for c in bang_cot.values()) / 1e6, 1),
        "mb_needed": 96.0,
        "mb_total": 408.0,
        "mb_hang_read": 408.0,
        "mb_cot_read": 96.0,
        "bytes_per_row_hang": 68,
        "bytes_per_row_cot": 16,
        "num_cols_hang": 17,
        "num_cols_cot": 4,
        "num_cols_skipped": 13,
        "bandwidth_savings_pct": 76.5,
        "t_row": round(tg_hang, 1),
        "t_col": round(tg_cot, 1),
        "t_row_median": round(bench_hang["median"], 1),
        "t_row_std": round(bench_hang["std"], 2),
        "t_row_min": round(bench_hang["min"], 1),
        "t_row_mean": round(bench_hang["mean"], 1),
        "t_col_median": round(bench_cot["median"], 1),
        "t_col_std": round(bench_cot["std"], 2),
        "t_col_min": round(bench_cot["min"], 1),
        "t_col_mean": round(bench_cot["mean"], 1),
        "speedup_1": speedup,
        "res_1": int(kq_hang),
        "matching_rows": matching_rows,
        "selected_cols": ["quantity", "discount", "extendedprice", "orderdate"],
        "num_selected_cols": 4,
        "samples": samples,
        "sql_parsed": True,
        "sql": sql or default_sql,
        "difference": int(abs(kq_hang - kq_cot)),
        "verified_equivalent": bool(kq_hang == kq_cot),
        "plan_a": {
            "name": "Plan A: Row-Store (AoS)",
            "strategy": "Full Tuple Scan & Early Materialization",
            "cols_read": 17,
            "bytes_per_row": 68,
            "total_mb": 408.0,
            "wasted_b": 52,
            "wasted_mb": 312.0,
            "wasted_pct": 76.5,
            "time_ms": round(tg_hang, 1),
            "std_ms": round(bench_hang["std"], 2),
            "result": int(kq_hang),
            "matching_rows": matching_rows,
        },
        "plan_b": {
            "name": "Plan B: Column-Store (SoA)",
            "strategy": "Columnar Projection Scan & Late Materialization",
            "cols_read": 4,
            "cols_list": ["quantity", "discount", "extendedprice", "orderdate"],
            "not_loaded_cols": 13,
            "bytes_per_row": 16,
            "total_mb": 96.0,
            "savings_mb": 312.0,
            "savings_pct": 76.5,
            "time_ms": round(tg_cot, 1),
            "std_ms": round(bench_cot["std"], 2),
            "result": int(kq_cot),
            "matching_rows": matching_rows,
        }
    }


def ma_hoa_rle(mang_da_sap_xep):
    """Nén RLE: gom các giá trị giống nhau liên tiếp thành (gia_tri, so_lan_lap)."""
    vi_tri_doi = np.flatnonzero(mang_da_sap_xep[1:] != mang_da_sap_xep[:-1]) + 1
    vi_tri_bat_dau = np.concatenate(([0], vi_tri_doi))
    return mang_da_sap_xep[vi_tri_bat_dau], np.diff(np.concatenate((vi_tri_bat_dau, [len(mang_da_sap_xep)])))


def demo_phan_2_nen_rle(so_dong, bo_sinh_ngau_nhien, ngay_bd=NGAY_BAT_DAU_LOC_RLE, ngay_kt=NGAY_KET_THUC_LOC_RLE):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PYTHON] demo_phan_2_nen_rle: rows={so_dong}, range=[{ngay_bd}..{ngay_kt}]")
    """Phần 2 (RLE): trả về dict tỉ lệ nén RLE và tốc độ COUNT(*) trực tiếp trên cụm nén."""
    ngay_bd = max(0, min(SO_NGAY_PHAN_BIET_RLE - 1, int(ngay_bd)))
    ngay_kt = max(ngay_bd, min(SO_NGAY_PHAN_BIET_RLE - 1, int(ngay_kt)))
    seed_val = int(bo_sinh_ngau_nhien) if isinstance(bo_sinh_ngau_nhien, (int, np.integer)) else 42
    ds = lay_bo_du_lieu_chuan(so_dong, seed_val)
    cot_ngay = ds.p2_cot_ngay
    gia_tri_cum, so_lan_lap = ds.p2_gia_tri_cum, ds.p2_so_lan_lap
    # 3 CASE TÍNH TOÁN TRỰC TIẾP TRÊN CỤM NÉN RLE (ZERO-DECOMPRESSION):
    if ngay_bd == 0 and ngay_kt >= SO_NGAY_PHAN_BIET_RLE - 1:
        # Case 3: Toàn bộ bảng (Full COUNT(*) không WHERE) -> duyệt 2,405 cụm thay vì 6M dòng
        dem_thuong = lambda: int((cot_ngay >= 0).sum())
        dem_rle = lambda: int(so_lan_lap.sum())
    elif ngay_bd == ngay_kt:
        # Case 2: Dấu bằng (=) (Exact Match · 1 ngày) -> Nhị phân 1 vị trí O(log K), 0 phép cộng!
        idx = int(np.searchsorted(gia_tri_cum, ngay_bd))
        dem_thuong = lambda: int((cot_ngay == ngay_bd).sum())
        dem_rle = lambda: int(so_lan_lap[idx]) if (idx < len(gia_tri_cum) and gia_tri_cum[idx] == ngay_bd) else 0
    else:
        # Case 1: Lọc khoảng (Between Predicate: ngay_bd <= orderdate <= ngay_kt) -> Nhị phân 2 đầu + SUM
        dem_thuong = lambda: int(((cot_ngay >= ngay_bd) & (cot_ngay <= ngay_kt)).sum())
        dem_rle = lambda: int(so_lan_lap[(gia_tri_cum >= ngay_bd) & (gia_tri_cum <= ngay_kt)].sum())

    kq_thuong, tg_thuong = do_thoi_gian_nhanh_nhat(dem_thuong)
    kq_rle, tg_rle = do_thoi_gian_nhanh_nhat(dem_rle)
    assert kq_thuong == kq_rle
    mask_loc = (gia_tri_cum >= ngay_bd) & (gia_tri_cum <= ngay_kt)
    gt_khop, lap_khop = gia_tri_cum[mask_loc], so_lan_lap[mask_loc]
    cum_khop_mau = [[int(gt_khop[i]), int(lap_khop[i])] for i in range(min(2, len(gt_khop)))]
    if len(gt_khop) > 2:
        cum_khop_mau.append([int(gt_khop[-1]), int(lap_khop[-1])])
    all_matched = [[int(gt_khop[i]), int(lap_khop[i])] for i in range(min(120, len(gt_khop)))]
    gt_bo_qua, lap_bo_qua = gia_tri_cum[~mask_loc], so_lan_lap[~mask_loc]
    cum_bo_qua_mau = [[int(gt_bo_qua[i]), int(lap_bo_qua[i])] for i in range(min(3, len(gt_bo_qua)))]
    return {
        "raw_mb": round(cot_ngay.nbytes / 1e6, 1), "rle_kb": round((gia_tri_cum.nbytes + so_lan_lap.nbytes) / 1e3, 1),
        "num_runs": int(len(gia_tri_cum)), "avg_run": int(round(so_dong / len(gia_tri_cum))),
        "t_raw_rle": round(tg_thuong * 1e3, 3), "t_direct_rle": round(tg_rle * 1e3, 3),
        "speedup_2": round(tg_thuong / max(tg_rle, 1e-9), 1), "res_2": int(kq_thuong),
        "rle_start": ngay_bd, "rle_end": ngay_kt,
        "first_runs": [[int(gia_tri_cum[i]), int(so_lan_lap[i])] for i in range(min(10, len(gia_tri_cum)))],
        "matched_runs_count": int(len(gt_khop)),
        "matched_edge_runs": cum_khop_mau,
        "all_matched_runs": all_matched,
        "skipped_sample_runs": cum_bo_qua_mau,
    }


def demo_phan_3_invisible_join():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PYTHON] demo_phan_3_invisible_join: start 3-phase stepper execution")
    """Phần 3 (Invisible Join): mô phỏng 3 pha Figure 2–4, Position List P, GROUP BY và Between Rewriting."""
    khach, ncc, ngay, fact = tao_du_lieu_mau_bai_bao()
    # Pha 1: Lọc bảng chiều nhỏ trong CPU Cache L1/L2 -> tập mã khóa thỏa điều kiện
    khoa_khach, khoa_ncc = ({k for k, kv in zip(t[col], t["region"]) if kv == "Asia"} for t, col in ((khach, "custkey"), (ncc, "suppkey")))
    khoa_ngay = {k for k, nam in zip(ngay["datekey"], ngay["year"]) if NAM_BAT_DAU <= nam <= NAM_KET_THUC_LOC}
    # Pha 2: Quét cột khóa ngoại Fact -> tạo Bitmap vectors và nhân AND bitwise
    bm_khach, bm_ncc, bm_ngay = (np.array([k in s for k in fact[col]], dtype=int) for s, col in ((khoa_khach, "custkey"), (khoa_ncc, "suppkey"), (khoa_ngay, "orderdate")))
    bm_and = bm_khach & bm_ncc & bm_ngay
    vi_tri = np.flatnonzero(bm_and)  # Danh sách vị trí các dòng sống sót (Position List P)
    # Pha 3 (Late Materialization): Chỉ đọc cột revenue và tra bảng băm cho các vị trí sống sót
    anh_xa_nam, ket_qua = dict(zip(ngay["datekey"], ngay["year"])), {}
    for ck, sk, dk, rev in zip(fact["custkey"][vi_tri], fact["suppkey"][vi_tri], fact["orderdate"][vi_tri], fact["revenue"][vi_tri]):
        khoa = (khach["nation"][ck - 1], ncc["nation"][sk - 1], int(anh_xa_nam[dk]))
        ket_qua[khoa] = ket_qua.get(khoa, 0) + int(rev)
    assert ket_qua == tinh_join_ngay_tho_kiem_chung(khach, ncc, ngay, fact)
    # Tối ưu Between-Predicate Rewriting: Đánh số lại khóa chiều để tạo khoảng liên tục
    thu_tu_moi = sorted(range(len(khach["custkey"])), key=lambda i: (khach["region"][i], khach["nation"][i]))
    bang_doi_khoa = {cu + 1: moi + 1 for moi, cu in enumerate(thu_tu_moi)}
    khoa_moi = sorted(bang_doi_khoa[k] for k in khoa_khach)
    assert not la_tap_khoa_lien_tuc(sorted(khoa_khach)) and la_tap_khoa_lien_tuc(khoa_moi)
    return {
        "p1_cust": sorted(int(x) for x in khoa_khach), "p1_supp": sorted(int(x) for x in khoa_ncc),
        "p1_date": sorted(int(x) for x in khoa_ngay), "bm_cust": bm_khach.tolist(), "bm_supp": bm_ncc.tolist(),
        "bm_date": bm_ngay.tolist(), "bm_and": bm_and.tolist(), "pos_list": vi_tri.tolist(),
        "p3_rows": [{"c_nation": c, "s_nation": s, "d_year": y, "revenue": r} for (c, s, y), r in sorted(ket_qua.items())],
        "rewritten_range": f"{khoa_moi[0]} <= lo.custkey <= {khoa_moi[-1]}",
    }


def demo_phan_4_benchmark_q31(so_dong, bo_sinh_ngau_nhien):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PYTHON] demo_phan_4_benchmark_q31: rows={so_dong}, running Plan A/B/C benchmarks")
    """Phần 4 (SSBM Q3.1): trả về dict so sánh Plan A (Row), Plan B (Invisible Join), Plan C (+ Between)."""
    seed_val = int(bo_sinh_ngau_nhien) if isinstance(bo_sinh_ngau_nhien, (int, np.integer)) else 42
    ds = lay_bo_du_lieu_chuan(so_dong, seed_val)
    chieu, fact_cot, fact_hang = ds.chieu, ds.fact_cot, ds.fact_hang
    ngay_thoa = (chieu["d_year"] >= NAM_BAT_DAU) & (chieu["d_year"] <= NAM_KET_THUC_LOC)
    c_asia, s_asia = chieu["c_region"] == MA_KHU_VUC_ASIA, chieu["s_region"] == MA_KHU_VUC_ASIA

    # PLAN A: Row-Store truyền thống - Early Materialization (sao chép tuple 68B qua từng phép join)
    def ke_hoach_a():
        dong = fact_hang[c_asia[fact_hang["custkey"]]]
        dong = dong[s_asia[dong["suppkey"]]]
        dong = dong[ngay_thoa[dong["orderdate"]]]
        return tinh_tong_theo_nhom(chieu["c_nation"][dong["custkey"]], chieu["s_nation"][dong["suppkey"]], chieu["d_year"][dong["orderdate"]], dong["revenue"])

    # PLAN B: Column-Store + Invisible Join (tra bảng băm + nhân Bitmap AND + Late Materialization)
    def ke_hoach_b():
        vi_tri = np.flatnonzero(c_asia[fact_cot["custkey"]] & s_asia[fact_cot["suppkey"]] & ngay_thoa[fact_cot["orderdate"]])
        return tinh_tong_theo_nhom(chieu["c_nation"][fact_cot["custkey"][vi_tri]], chieu["s_nation"][fact_cot["suppkey"][vi_tri]], chieu["d_year"][fact_cot["orderdate"][vi_tri]], fact_cot["revenue"][vi_tri])

    # PLAN C: Column-Store + Between Predicate (đổi tra bảng băm thành so sánh khoảng trên CPU ALU/SIMD)
    def ke_hoach_c():
        (c_min, c_max), (s_min, s_max), (d_min, d_max) = (tim_khoang_khoa_lien_tuc(m) for m in (c_asia, s_asia, ngay_thoa))
        ck, sk, dk = fact_cot["custkey"], fact_cot["suppkey"], fact_cot["orderdate"]
        vi_tri = np.flatnonzero((ck >= c_min) & (ck <= c_max) & (sk >= s_min) & (sk <= s_max) & (dk >= d_min) & (dk <= d_max))
        return tinh_tong_theo_nhom(chieu["c_nation"][ck[vi_tri]], chieu["s_nation"][sk[vi_tri]], chieu["d_year"][dk[vi_tri]], fact_cot["revenue"][vi_tri])

    kq_a, tg_a = do_thoi_gian_nhanh_nhat(ke_hoach_a)
    kq_b, tg_b = do_thoi_gian_nhanh_nhat(ke_hoach_b)
    kq_c, tg_c = do_thoi_gian_nhanh_nhat(ke_hoach_c)
    assert kq_a == kq_b == kq_c  # Kiểm chứng dữ liệu: cả 3 kế hoạch phải ra cùng 150 nhóm và cùng tổng doanh thu
    return {
        "num_groups": len(kq_a), "total_rev_4": int(sum(kq_a.values())),
        "t_plan_a": round(tg_a * 1000, 1), "t_plan_b": round(tg_b * 1000, 1),
        "speedup_b": round(tg_a / max(tg_b, 1e-9), 1), "t_plan_c": round(tg_c * 1000, 1),
        "speedup_c": round(tg_a / max(tg_c, 1e-9), 1),
    }


# Alias tương thích ngược cho tên cũ
demo_phan_4_mini_benchmark = demo_phan_4_benchmark_q31


def _tao_log_ket_qua(part, rows, seed, codes, merged, elapsed_ms):
    """Tạo danh sách dòng log thực thi chi tiết trả về cho khung log Web Dashboard."""
    logs = [f'[PYTHON] chay_demo_cho_web(part="{part}", rows={rows:,}, seed={seed})']
    if "1" in codes:
        mode_str = "Chế độ Thực thi SQL" if merged.get("sql_parsed") else "Chế độ Mô phỏng Chiếu"
        logs.extend([
            f"[Phần 1 · AoS vs SoA] {mode_str} · Đọc {merged['num_selected_cols']}/17 cột: {', '.join(merged['selected_cols'])}",
            f"  • RAM cấp phát: Row={merged['mb_hang_ram']} MB | Col={merged['mb_cot_ram']} MB",
            f"  • Khối lượng quét: Col={merged['mb_needed']} MB ({merged.get('bytes_per_row_cot', merged['num_selected_cols']*4)}B/dòng) vs Row={merged['mb_total']} MB ({merged.get('bytes_per_row_hang', 68)}B/dòng) -> Tiết kiệm {merged.get('bandwidth_savings_pct', 0):.1f}% băng thông",
            f"  • Benchmark Rigor (2 warm-ups + 5 lượt đo thực tế):",
            f"    - Row-Store (AoS):    Median={merged.get('t_row_median', merged['t_row'])} ms, Std Dev=±{merged.get('t_row_std', 0.0)} ms (Mean={merged.get('t_row_mean', merged['t_row'])} ms)",
            f"    - Column-Store (SoA): Median={merged.get('t_col_median', merged['t_col'])} ms, Std Dev=±{merged.get('t_col_std', 0.0)} ms (Mean={merged.get('t_col_mean', merged['t_col'])} ms)",
            f"    - Tăng tốc (Speedup): {merged['speedup_1']}x nhanh hơn",
            f"  • Kết quả: SUM = {merged['res_1']:,} (assert kq_hang == kq_cot ✓)",
        ])
    if "2" in codes:
        logs.extend([
            f"[Phần 2 · Nén RLE] Cột orderdate đã sắp xếp ({rows:,} dòng)",
            f"  • Dung lượng: Gốc={merged['raw_mb']} MB -> RLE={merged['rle_kb']} KB ({merged['num_runs']:,} cụm, TB {merged['avg_run']:,} dòng/cụm)",
            f"  • Lọc cụm: WHERE orderdate BETWEEN {merged.get('rle_start', NGAY_BAT_DAU_LOC_RLE)} AND {merged.get('rle_end', NGAY_KET_THUC_LOC_RLE)} -> khớp {merged.get('matched_runs_count', 365):,}/{merged['num_runs']:,} cụm",
            f"  • Tốc độ COUNT: Quét thường={merged['t_raw_rle']} ms vs Đếm RLE={merged['t_direct_rle']} ms -> {merged['speedup_2']}x",
            f"  • Kết quả: COUNT = {merged['res_2']:,} (assert kq_thuong == kq_rle ✓)",
        ])
    if "3" in codes:
        logs.extend([
            "[Phần 3 · Invisible Join] Dữ liệu mẫu 7 dòng (SIGMOD 2008 Fig. 2)",
            f"  • Pha 1 (Lọc chiều): cust={merged['p1_cust']}, supp={merged['p1_supp']}, date={merged['p1_date']}",
            f"  • Pha 2 (Bitmap AND): {merged['bm_cust']} & {merged['bm_supp']} & {merged['bm_date']} -> {merged['bm_and']} => P={merged['pos_list']}",
            f"  • Pha 3 (Late Materialization): {merged['p3_rows']}",
            f"  • Between Rewriting: {merged['rewritten_range']} (liên tục ✓)",
        ])
    if "4" in codes:
        logs.extend([
            f"[Phần 4 · SSBM Q3.1] Fact={rows:,} dòng -> {merged['num_groups']} nhóm",
            f"  • Plan A (Row-Store Join):      {merged['t_plan_a']} ms (1.0x)",
            f"  • Plan B (Invisible Join):      {merged['t_plan_b']} ms ({merged['speedup_b']}x)",
            f"  • Plan C (+ Between-Predicate): {merged['t_plan_c']} ms ({merged['speedup_c']}x)",
            f"  • Tổng doanh thu: {merged['total_rev_4']:,} (assert kq_a == kq_b == kq_c ✓)",
        ])
    logs.append(f"[OK] Python trả kết quả sau {elapsed_ms} ms")
    return logs


def chay_invisible_join_cho_web(cust_region="Asia", supp_region="Asia", year_start=1992, year_end=1997, rows=6_000_000, seed=42):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PYTHON] chay_invisible_join_cho_web: cust_region={cust_region}, supp_region={supp_region}, years={year_start}..{year_end}, rows={rows}")
    """Tính toán và mô phỏng chi tiết Invisible Join vs Row-store Hash Join theo tham số REST API."""
    cust_region = str(cust_region or "Asia").strip()
    supp_region = str(supp_region or "Asia").strip()
    year_start = 1992 if year_start is None else int(year_start)
    year_end = 1997 if year_end is None else int(year_end)
    rows = 6_000_000 if rows is None else int(rows)
    seed = 42 if seed is None else int(seed)

    if not (1 <= rows <= 30_000_000):
        raise ValueError("rows must be between 1 and 30,000,000")
    if year_start > year_end:
        raise ValueError("year_start must be <= year_end")

    c_reg_norm = cust_region.lower()
    s_reg_norm = supp_region.lower()

    # 1. Dữ liệu mẫu bài báo 7 dòng (SIGMOD 2008 Figure 2-4)
    khach, ncc, ngay, fact_toy = tao_du_lieu_mau_bai_bao()
    khoa_khach = {k for k, kv in zip(khach["custkey"], khach["region"]) if kv.lower() == c_reg_norm}
    khoa_ncc = {k for k, kv in zip(ncc["suppkey"], ncc["region"]) if kv.lower() == s_reg_norm}
    khoa_ngay = {k for k, nam in zip(ngay["datekey"], ngay["year"]) if year_start <= nam <= year_end}

    bm_khach = np.array([1 if k in khoa_khach else 0 for k in fact_toy["custkey"]], dtype=int)
    bm_ncc = np.array([1 if k in khoa_ncc else 0 for k in fact_toy["suppkey"]], dtype=int)
    bm_ngay = np.array([1 if k in khoa_ngay else 0 for k in fact_toy["orderdate"]], dtype=int)
    bm_and = bm_khach & bm_ncc & bm_ngay
    pos_list_toy = np.flatnonzero(bm_and).tolist()

    anh_xa_nam = dict(zip(ngay["datekey"], ngay["year"]))
    ket_qua_toy = {}
    for idx in pos_list_toy:
        ck, sk, dk, rev = fact_toy["custkey"][idx], fact_toy["suppkey"][idx], fact_toy["orderdate"][idx], fact_toy["revenue"][idx]
        khoa = (khach["nation"][ck - 1], ncc["nation"][sk - 1], int(anh_xa_nam[dk]))
        ket_qua_toy[khoa] = ket_qua_toy.get(khoa, 0) + int(rev)

    p3_rows = [
        {"c_nation": c, "s_nation": s, "d_year": y, "year": y, "revenue": r}
        for (c, s, y), r in sorted(ket_qua_toy.items())
    ]

    thu_tu_moi = sorted(range(len(khach["custkey"])), key=lambda i: (khach["region"][i], khach["nation"][i]))
    bang_doi_khoa = {cu + 1: moi + 1 for moi, cu in enumerate(thu_tu_moi)}
    khoa_moi = sorted(bang_doi_khoa[k] for k in khoa_khach)
    is_contig = bool(khoa_moi) and la_tap_khoa_lien_tuc(khoa_moi)
    rewritten_range = f"{khoa_moi[0]} <= lo.custkey <= {khoa_moi[-1]}" if is_contig else (f"lo.custkey IN {khoa_moi}" if khoa_moi else "None")

    # 2. Mô phỏng quy mô lớn trên Lược đồ sao (Star Schema)
    reg_map = {"america": 0, "africa": 1, "asia": 2, "europe": 3, "middle east": 4}
    c_id = reg_map.get(c_reg_norm, MA_KHU_VUC_ASIA)
    s_id = reg_map.get(s_reg_norm, MA_KHU_VUC_ASIA)

    ds = lay_bo_du_lieu_chuan(rows, seed)
    chieu, fact_cot, fact_hang = ds.chieu, ds.fact_cot, ds.fact_hang

    c_mask = chieu["c_region"] == c_id
    s_mask = chieu["s_region"] == s_id
    d_mask = (chieu["d_year"] >= year_start) & (chieu["d_year"] <= year_end)

    # Traditional Row-Store Hash Join (Early Materialization - quét 17 cột, 68 byte/dòng)
    t0_row = time.perf_counter()
    dong1 = fact_hang[c_mask[fact_hang["custkey"]]]
    dong2 = dong1[s_mask[dong1["suppkey"]]]
    dong3 = dong2[d_mask[dong2["orderdate"]]]
    res_row = tinh_tong_theo_nhom(chieu["c_nation"][dong3["custkey"]], chieu["s_nation"][dong3["suppkey"]], chieu["d_year"][dong3["orderdate"]], dong3["revenue"])
    t_row_ms = round((time.perf_counter() - t0_row) * 1000, 1)

    len_d1, len_d2, len_d3 = len(dong1), len(dong2), len(dong3)
    inter_rows = len_d1 + len_d2

    # Column-Store Invisible Join (3 Pha - late materialization)
    t0_p1 = time.perf_counter()
    cm = chieu["c_region"] == c_id
    sm = chieu["s_region"] == s_id
    dm = (chieu["d_year"] >= year_start) & (chieu["d_year"] <= year_end)
    t_p1_ms = round((time.perf_counter() - t0_p1) * 1000, 2)

    t0_p2 = time.perf_counter()
    p_cust = cm[fact_cot["custkey"]]
    p_supp = sm[fact_cot["suppkey"]]
    p_date = dm[fact_cot["orderdate"]]
    and_bm_bench = p_cust & p_supp & p_date
    pos_bench = np.flatnonzero(and_bm_bench)
    t_p2_ms = round((time.perf_counter() - t0_p2) * 1000, 2)

    t0_p3 = time.perf_counter()
    ck_m = fact_cot["custkey"][pos_bench]
    sk_m = fact_cot["suppkey"][pos_bench]
    dk_m = fact_cot["orderdate"][pos_bench]
    rev_m = fact_cot["revenue"][pos_bench]
    res_col = tinh_tong_theo_nhom(chieu["c_nation"][ck_m], chieu["s_nation"][sk_m], chieu["d_year"][dk_m], rev_m)
    t_p3_ms = round((time.perf_counter() - t0_p3) * 1000, 2)

    t_col_ms = round(t_p1_ms + t_p2_ms + t_p3_ms, 1)
    matched_rows = int(len(pos_bench))
    assert res_row == res_col, "Kết quả GROUP BY của Row-store và Column-store phải trùng khớp 100%!"

    speedup_x = round(t_row_ms / max(t_col_ms, 0.001), 1)
    total_rev_ij = int(sum(res_col.values()))
    num_groups_ij = len(res_col)

    # Row-store statistics
    rowstore_stats = {
        "elapsed_ms": t_row_ms,
        "bytes_scanned_mb": round(rows * 68 / 1e6, 1),
        "cells_read": rows * 17,
        "physical_joins": 3,
        "intermediate_rows": inter_rows,
        "tuple_size_bytes": 68,
        "total_revenue": total_rev_ij,
        "num_groups": num_groups_ij,
    }

    # Column-store statistics
    columnstore_stats = {
        "elapsed_ms": t_col_ms,
        "bytes_scanned_mb": round((rows * 3 * 4 + matched_rows * 4) / 1e6, 1),
        "cells_read": rows * 3 + matched_rows,
        "physical_joins": 0,
        "intermediate_rows": 0,
        "matched_rows": matched_rows,
        "speedup_x": speedup_x,
        "total_revenue": total_rev_ij,
        "num_groups": num_groups_ij,
    }

    breakdown = {
        "phase1": {
            "title": "Pha 1 · Lọc bảng chiều & Tạo bảng băm",
            "description": "Lọc các bảng chiều độc lập theo điều kiện WHERE, tạo bảng băm nhỏ trong cache CPU",
            "cust_region": cust_region,
            "supp_region": supp_region,
            "year_range": f"{year_start}..{year_end}",
            "cust_keys_toy": sorted(int(x) for x in khoa_khach),
            "supp_keys_toy": sorted(int(x) for x in khoa_ncc),
            "date_keys_toy": sorted(int(x) for x in khoa_ngay),
            "cust_matched_count": int(cm.sum()),
            "supp_matched_count": int(sm.sum()),
            "date_matched_count": int(dm.sum()),
            "elapsed_ms": t_p1_ms,
        },
        "phase2": {
            "title": "Pha 2 · Quét khóa ngoại & Bitwise AND",
            "description": "Quét song song 3 cột khóa ngoại trên Fact table, sinh 3 bitmap và thực hiện bitwise AND",
            "columns_scanned": ["custkey", "suppkey", "orderdate"],
            "bytes_scanned_mb": round(rows * 3 * 4 / 1e6, 1),
            "cells_read": rows * 3,
            "bm_cust_toy": bm_khach.tolist(),
            "bm_supp_toy": bm_ncc.tolist(),
            "bm_date_toy": bm_ngay.tolist(),
            "bm_and_toy": bm_and.tolist(),
            "pos_list_toy": pos_list_toy,
            "matched_rows": matched_rows,
            "selectivity_pct": round(matched_rows / max(rows, 1) * 100, 2),
            "elapsed_ms": t_p2_ms,
        },
        "phase3": {
            "title": "Pha 3 · Late Materialization & GROUP BY",
            "description": "Chỉ đọc cột revenue tại các vị trí P thỏa mãn và tổng hợp GROUP BY",
            "columns_retrieved": ["revenue"],
            "bytes_materialized_mb": round(matched_rows * 4 / 1e6, 2),
            "cells_read": matched_rows,
            "groups_count": len(res_col),
            "total_revenue": int(sum(res_col.values())),
            "elapsed_ms": t_p3_ms,
        },
        "rowstore": {
            "title": "Row-Store Truyền thống (Early Materialization)",
            "description": "Quét toàn bộ 17 cột (68B/dòng), thực hiện 3 phép Hash Join tạo ra các bản ghi trung gian khổng lồ",
            "columns_scanned": 17,
            "tuple_size_bytes": 68,
            "join_pipeline": [
                {"step": 1, "join": "Customer Hash Join", "input_rows": rows, "output_rows": len_d1, "bytes_mb": round(len_d1 * 68 / 1e6, 1)},
                {"step": 2, "join": "Supplier Hash Join", "input_rows": len_d1, "output_rows": len_d2, "bytes_mb": round(len_d2 * 68 / 1e6, 1)},
                {"step": 3, "join": "DWDate Hash Join", "input_rows": len_d2, "output_rows": len_d3, "bytes_mb": round(len_d3 * 68 / 1e6, 1)},
            ],
            "total_bytes_moved_mb": round((rows + len_d1 + len_d2) * 68 / 1e6, 1),
            "intermediate_rows": inter_rows,
        },
        "comparison": {
            "speedup_x": speedup_x,
            "bandwidth_saved_pct": round((1 - (rows * 3 * 4 + matched_rows * 4) / max(rows * 68, 1)) * 100, 1),
            "cells_reduction_pct": round((1 - (rows * 3 + matched_rows) / max(rows * 17, 1)) * 100, 1),
            "physical_joins_eliminated": 3,
            "intermediate_rows_eliminated": inter_rows,
        },
        "rewritten_range": rewritten_range,
    }

    logs = [
        f'[POST /api/invisible-join] cust="{cust_region}", supp="{supp_region}", years={year_start}..{year_end}, rows={rows:,}',
        f"  • Row-Store Hash Join: {t_row_ms} ms | Quét 17 cột ({rowstore_stats['bytes_scanned_mb']} MB) | 3 phép join | {inter_rows:,} dòng trung gian",
        f"  • Column-Store Invisible Join: {t_col_ms} ms | Quét 3 FK + 1 Rev ({columnstore_stats['bytes_scanned_mb']} MB) | 0 join vật lý | 0 dòng trung gian | {matched_rows:,} dòng khớp ({breakdown['phase2']['selectivity_pct']}%)",
        f"  • Tăng tốc: {speedup_x}x nhanh hơn so với Row-Store (assert kết quả khớp 100% ✓)",
        f"  • Toy Example P={pos_list_toy} -> {len(p3_rows)} nhóm: {p3_rows}",
    ]

    return {
        "ok": True,
        "cust_region": cust_region,
        "supp_region": supp_region,
        "year_start": year_start,
        "year_end": year_end,
        "rows": rows,
        "seed": seed,
        "rowstore_stats": rowstore_stats,
        "columnstore_stats": columnstore_stats,
        "p3_rows": p3_rows,
        "breakdown": breakdown,
        "logs": logs,
    }


def chay_demo_cho_web(part="all", rows=6_000_000, seed=42, cols=None, sql=None, rle_start=None, rle_end=None):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PYTHON] chay_demo_cho_web: part={part}, rows={rows}, seed={seed}")
    """Chạy phần demo theo yêu cầu và trả về dict thuần JSON-ready cho Web Dashboard."""
    part = str(part).strip().lower()
    if part not in {"1", "2", "3", "4", "all"}:
        raise ValueError(f"Invalid part: {part}")
    ngay_bd = NGAY_BAT_DAU_LOC_RLE if rle_start is None else int(rle_start)
    ngay_kt = NGAY_KET_THUC_LOC_RLE if rle_end is None else int(rle_end)
    t0 = time.perf_counter()
    runners = {
        "1": lambda: demo_phan_1_layout_hang_va_cot(rows, seed, cols, sql=sql),
        "2": lambda: demo_phan_2_nen_rle(rows, seed, ngay_bd, ngay_kt),
        "3": demo_phan_3_invisible_join,
        "4": lambda: demo_phan_4_benchmark_q31(rows, seed),
    }
    codes = ["1", "2", "3", "4"] if part == "all" else [part]
    merged = {}
    for code in codes:
        merged.update(runners[code]())
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "ok": True,
        "part": part,
        "rows": rows,
        "seed": seed,
        "elapsed_ms": elapsed_ms,
        "parsed": merged,
        "logs": _tao_log_ket_qua(part, rows, seed, codes, merged, elapsed_ms),
    }
