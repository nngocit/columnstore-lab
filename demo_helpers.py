"""Hàm phụ trợ, hằng số và bộ sinh dữ liệu thuần tính toán cho Demo Column-Store."""
import time
import numpy as np

SO_LAN_DO_THOI_GIAN, SO_BYTE_MOI_INT32 = 3, 4
SO_COT_LINEORDER, SO_COT_TRUY_VAN_PHAN_1 = 17, 3
SO_NGAY_PHAN_BIET_RLE, NGAY_BAT_DAU_LOC_RLE, NGAY_KET_THUC_LOC_RLE = 2_405, 1_000, 1_364
SO_KHACH_HANG, SO_NHA_CUNG_CAP, SO_NGAY_TRONG_BANG_CHIEU = 30_000, 2_000, 2_555
SO_KHU_VUC, SO_QUOC_GIA, SO_NAM = 5, 25, 8
NAM_BAT_DAU, NAM_KET_THUC_LOC, MA_KHU_VUC_ASIA, SO_COT_DEM_TRONG_FACT = 1992, 1997, 2, 13


def do_thoi_gian_nhanh_nhat(ham_can_do, *tham_so, so_lan_lap=SO_LAN_DO_THOI_GIAN):
    """Chạy lặp lại hàm và trả về (kết quả, thời gian nhanh nhất tính bằng giây)."""
    thoi_gian_tot_nhat, ket_qua = float("inf"), None
    for _ in range(so_lan_lap):
        moc = time.perf_counter()
        ket_qua = ham_can_do(*tham_so)
        thoi_gian_tot_nhat = min(thoi_gian_tot_nhat, time.perf_counter() - moc)
    return ket_qua, thoi_gian_tot_nhat


def tao_du_lieu_bang_lineorder(so_dong, bo_sinh_ngau_nhien):
    """Tạo bảng LINEORDER (17 cột int32) dưới 2 cách lưu: theo hàng (AoS) và theo cột (SoA).
    Chuẩn SSBM Q1.1: Cần 4 cột FACT: quantity, discount, extendedprice, orderdate.
    13 cột còn lại (c04..c16) là các thuộc tính đệm không được truy vấn nạp (Not Loaded trong Column-Store).
    """
    ten_cot = ["quantity", "discount", "extendedprice", "orderdate"] + [f"c{i:02d}" for i in range(4, SO_COT_LINEORDER)]
    bang_cot = {c: bo_sinh_ngau_nhien.integers(0, 50, so_dong, dtype=np.int32) for c in ten_cot}
    bang_cot["quantity"] = bo_sinh_ngau_nhien.integers(1, 51, so_dong, dtype=np.int32)
    bang_cot["discount"] = bo_sinh_ngau_nhien.integers(0, 11, so_dong, dtype=np.int32)
    bang_cot["extendedprice"] = bo_sinh_ngau_nhien.integers(1000, 100000, so_dong, dtype=np.int32)
    bang_cot["orderdate"] = bo_sinh_ngau_nhien.integers(0, SO_NGAY_TRONG_BANG_CHIEU, so_dong, dtype=np.int32)
    # Đảm bảo 5 dòng mẫu visual preview chuẩn:
    # Row #0: qty=46, disc=10, price=69380, orderdate=100 (Year 1992 -> Loại)
    # Row #1: qty=18, disc=2, price=87666, orderdate=400 (Year 1993, disc in 1..3, qty < 25 -> Khớp 87,666 * 2 = 175,332)
    # Row #2: qty=33, disc=1, price=57501, orderdate=450 (Year 1993, qty >= 25 -> Loại)
    # Row #3: qty=48, disc=4, price=23188, orderdate=800 (Year 1994 -> Loại)
    # Row #4: qty=5, disc=1, price=91400, orderdate=150 (Year 1992 -> Loại)
    if so_dong > 4:
        bang_cot["quantity"][:5] = [46, 18, 33, 48, 5]
        bang_cot["discount"][:5] = [10, 2, 1, 4, 1]
        bang_cot["extendedprice"][:5] = [69380, 87666, 57501, 23188, 91400]
        bang_cot["orderdate"][:5] = [100, 400, 450, 800, 150]
    elif so_dong > 1:
        bang_cot["quantity"][1] = 18
        bang_cot["discount"][1] = 2
        bang_cot["extendedprice"][1] = 87666
        bang_cot["orderdate"][1] = 400
    bang_hang = np.empty(so_dong, dtype=np.dtype([(c, np.int32) for c in ten_cot]))
    for c in ten_cot:
        bang_hang[c] = bang_cot[c]
    return bang_hang, bang_cot


def tao_du_lieu_mau_bai_bao():
    """Khởi tạo đúng 3 bảng chiều và bảng fact 7 dòng từ Figure 2-4 của bài báo."""
    khach = {"custkey": [1, 2, 3], "region": ["Asia", "Europe", "Asia"], "nation": ["China", "France", "India"]}
    ncc = {"suppkey": [1, 2], "region": ["Asia", "Europe"], "nation": ["Russia", "Spain"]}
    ngay = {"datekey": [0, 1, 2], "year": [1992, 1992, 1992]}
    fact = {
        "custkey": np.array([3, 3, 2, 1, 2, 1, 3]), "suppkey": np.array([1, 2, 1, 1, 2, 2, 2]),
        "orderdate": np.array([0, 0, 1, 1, 1, 2, 2]), "revenue": np.array([43256, 33333, 12121, 23233, 45456, 43251, 34235]),
    }
    return khach, ncc, ngay, fact


def tao_luoc_do_sao(so_dong, bo_sinh_ngau_nhien):
    """Tạo 3 bảng chiều (đã sort theo region/year) và bảng fact dạng cột cho Phần 4."""
    cac_bang_chieu = {
        "c_region": np.arange(SO_KHACH_HANG) // (SO_KHACH_HANG // SO_KHU_VUC), "c_nation": np.arange(SO_KHACH_HANG) // (SO_KHACH_HANG // SO_QUOC_GIA),
        "s_region": np.arange(SO_NHA_CUNG_CAP) // (SO_NHA_CUNG_CAP // SO_KHU_VUC), "s_nation": np.arange(SO_NHA_CUNG_CAP) // (SO_NHA_CUNG_CAP // SO_QUOC_GIA),
        "d_year": NAM_BAT_DAU + np.arange(SO_NGAY_TRONG_BANG_CHIEU) // 365,
    }
    bang_fact_cot = {
        "custkey": bo_sinh_ngau_nhien.integers(0, SO_KHACH_HANG, so_dong, dtype=np.int32),
        "suppkey": bo_sinh_ngau_nhien.integers(0, SO_NHA_CUNG_CAP, so_dong, dtype=np.int32),
        "orderdate": np.sort(bo_sinh_ngau_nhien.integers(0, SO_NGAY_PHAN_BIET_RLE, so_dong, dtype=np.int32)),
        "revenue": bo_sinh_ngau_nhien.integers(1, 100_000, so_dong, dtype=np.int32),
    }
    return cac_bang_chieu, bang_fact_cot


def chuyen_bang_fact_sang_dang_hang(bang_fact_theo_cot, so_dong):
    """Tạo bản sao dạng hàng của bảng fact: 4 cột dùng + 13 cột đệm = 17 cột (68 byte/dòng)."""
    truong = [("custkey", "i4"), ("suppkey", "i4"), ("orderdate", "i4"), ("revenue", "i4")] + [(f"pad{i}", "i4") for i in range(SO_COT_DEM_TRONG_FACT)]
    bang_hang = np.zeros(so_dong, dtype=np.dtype(truong))
    for ten_cot, mang_cot in bang_fact_theo_cot.items():
        bang_hang[ten_cot] = mang_cot
    return bang_hang


def tinh_join_ngay_tho_kiem_chung(khach, ncc, ngay, fact):
    """Join từng dòng theo cách thông thường để đối chiếu kết quả với Invisible Join."""
    ket_qua = {}
    for i in range(len(fact["revenue"])):
        vc, vs, vd = fact["custkey"][i] - 1, fact["suppkey"][i] - 1, ngay["datekey"].index(fact["orderdate"][i])
        nam = ngay["year"][vd]
        if khach["region"][vc] == "Asia" and ncc["region"][vs] == "Asia" and NAM_BAT_DAU <= nam <= NAM_KET_THUC_LOC:
            khoa = (khach["nation"][vc], ncc["nation"][vs], nam)
            ket_qua[khoa] = ket_qua.get(khoa, 0) + int(fact["revenue"][i])
    return ket_qua


def la_tap_khoa_lien_tuc(danh_sach_khoa_da_sap_xep):
    """Kiểm tra danh sách khóa tăng dần có tạo thành đoạn số nguyên liên tiếp hay không."""
    return bool(danh_sach_khoa_da_sap_xep) and danh_sach_khoa_da_sap_xep == list(range(danh_sach_khoa_da_sap_xep[0], danh_sach_khoa_da_sap_xep[-1] + 1))


def tinh_tong_theo_nhom(quoc_gia_khach, quoc_gia_ncc, nam_dat_hang, doanh_thu):
    """GROUP BY (c_nation, s_nation, d_year) và SUM(revenue) bằng mã hóa 1 chiều + np.bincount."""
    so_nhom_con = SO_QUOC_GIA * SO_NAM
    ma_nhom = quoc_gia_khach.astype(np.int64) * so_nhom_con + quoc_gia_ncc * SO_NAM + (nam_dat_hang - NAM_BAT_DAU)
    tong_o = np.bincount(ma_nhom, weights=doanh_thu.astype(np.float64), minlength=SO_QUOC_GIA * so_nhom_con)
    return {(int(m // so_nhom_con), int((m // SO_NAM) % SO_QUOC_GIA), int(NAM_BAT_DAU + (m % SO_NAM))): int(tong_o[m]) for m in np.flatnonzero(tong_o)}


def tim_khoang_khoa_lien_tuc(mat_na_thoa_dieu_kien):
    """Trả về (khoa_nho_nhat, khoa_lon_nhat) của một đoạn khóa liên tục thỏa điều kiện."""
    vi_tri = np.flatnonzero(mat_na_thoa_dieu_kien)
    assert (vi_tri[-1] - vi_tri[0] + 1) == len(vi_tri), "Tập khóa không liên tục"
    return int(vi_tri[0]), int(vi_tri[-1])


class DemoDataset(dict):
    """Container dữ liệu chuẩn cho Demo Column-Store, hỗ trợ cả dict key, object attr và tuple unpacking."""
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"Không tìm thấy thuộc tính {name}")

    def __iter__(self):
        yield self["chieu"]
        yield self["fact_cot"]
        yield self["fact_hang"]
        yield self["p1_hang"]
        yield self["p1_cot"]


def sinh_du_lieu_demo(N=6_000_000, seed=42):
    """Tạo bộ dữ liệu mô phỏng Star Schema đầy đủ cho N dòng và seed xác định."""
    rng_star = np.random.default_rng(seed)
    cac_bang_chieu, bang_fact_cot = tao_luoc_do_sao(N, rng_star)
    bang_fact_hang = chuyen_bang_fact_sang_dang_hang(bang_fact_cot, N)
    rng_p1 = np.random.default_rng(seed + 101)
    bang_hang_p1, bang_cot_p1 = tao_du_lieu_bang_lineorder(N, rng_p1)
    return DemoDataset({
        "chieu": cac_bang_chieu,
        "fact_cot": bang_fact_cot,
        "fact_hang": bang_fact_hang,
        "p1_hang": bang_hang_p1,
        "p1_cot": bang_cot_p1,
    })

