#!/usr/bin/env python3
"""
Demo minh họa bài báo:
"Column-Stores vs. Row-Stores: How Different Are They Really?"
(Abadi, Madden, Hachem - SIGMOD 2008)

File CHÍNH chỉ giữ đúng logic cốt lõi của 4 phần thuyết trình.
Toàn bộ hằng số, hàm sinh dữ liệu, đo giờ và kiểm chứng đã tách sang `demo_helpers.py`.

Chạy:  python column_store_demo_de_hieu.py
       python column_store_demo_de_hieu.py --part 3
       python column_store_demo_de_hieu.py --part all --rows 3000000

4 phần demo cốt lõi:
  1. Layout hàng vs cột  -> column-store chỉ đọc đúng 3/17 cột cần dùng
  2. Nén RLE             -> tính COUNT(*) trực tiếp trên dữ liệu đã nén
  3. Invisible join      -> minh họa 3 pha trên dữ liệu mẫu Figure 2-4 của bài báo
  4. Mini-benchmark      -> truy vấn kiểu SSBM Q3.1: Row-store vs Invisible join
"""
import argparse
import numpy as np

from demo_helpers import (
    MA_KHU_VUC_ASIA, NAM_BAT_DAU, NAM_KET_THUC_LOC,
    NGAY_BAT_DAU_LOC_RLE, NGAY_KET_THUC_LOC_RLE,
    SO_BYTE_MOI_INT32, SO_COT_LINEORDER, SO_COT_TRUY_VAN_PHAN_1, SO_NGAY_PHAN_BIET_RLE,
    chuyen_bang_fact_sang_dang_hang, do_thoi_gian_nhanh_nhat, in_chung_minh_nap_ram,
    in_du_lieu_mau_phan_3, in_mau_bang_phan_1, in_mau_du_lieu_phan_2,
    in_mau_luoc_do_sao_phan_4, in_tieu_de_phan, la_tap_khoa_lien_tuc,
    lay_ram_tien_trinh_mb, tao_du_lieu_bang_lineorder, tao_du_lieu_mau_bai_bao,
    tao_luoc_do_sao, tim_khoang_khoa_lien_tuc, tinh_join_ngay_tho_kiem_chung, tinh_tong_theo_nhom,
)


# ============================================================================
# PHẦN 1. LAYOUT HÀNG VS CỘT
# ============================================================================
def tinh_doanh_thu_giam_gia(bang_du_lieu):
    """SELECT SUM(extendedprice * discount) WHERE discount BETWEEN 1 AND 3 AND quantity < 25"""
    cot_giam_gia = bang_du_lieu["discount"]
    cot_so_luong = bang_du_lieu["quantity"]
    cot_gia_ban = bang_du_lieu["extendedprice"]

    dong_thoa = (cot_giam_gia >= 1) & (cot_giam_gia <= 3) & (cot_so_luong < 25)
    return int((cot_gia_ban[dong_thoa].astype(np.int64) * cot_giam_gia[dong_thoa]).sum())


def demo_phan_1_layout_hang_va_cot(so_dong, bo_sinh_ngau_nhien):
    """So sánh tốc độ truy vấn chỉ dùng 3/17 cột giữa lưu theo hàng và lưu theo cột."""
    in_tieu_de_phan("PHẦN 1. Layout hàng vs cột: query chỉ đụng 3 trong 17 cột")
    ram_truoc_mb = lay_ram_tien_trinh_mb()
    bang_theo_hang, bang_theo_cot = tao_du_lieu_bang_lineorder(so_dong, bo_sinh_ngau_nhien)
    ram_sau_mb = lay_ram_tien_trinh_mb()
    in_chung_minh_nap_ram(ram_truoc_mb, ram_sau_mb, bang_theo_hang, bang_theo_cot)
    print()
    in_mau_bang_phan_1(bang_theo_cot)
    print()

    ket_qua_hang, thoi_gian_hang = do_thoi_gian_nhanh_nhat(tinh_doanh_thu_giam_gia, bang_theo_hang)
    ket_qua_cot, thoi_gian_cot = do_thoi_gian_nhanh_nhat(tinh_doanh_thu_giam_gia, bang_theo_cot)
    assert ket_qua_hang == ket_qua_cot

    # Giải thích kích thước 68 byte/dòng và cách RAM/CPU đọc dữ liệu thực tế:
    # - Mỗi cột int32 tốn 4 byte, bảng có 17 cột -> 17 x 4 = 68 byte/dòng (dòng 101).
    # - Row layout (bang_theo_hang): 17 cột của 1 dòng nằm liền nhau [qty, discount, price, c03..c16].
    #   CPU nạp dữ liệu theo từng khối cache line (64 byte), nên muốn lấy 4 byte của discount
    #   phải kéo theo hàng loạt cột thừa kề bên và nhảy bước 68 byte sang dòng kế -> tốn băng thông RAM/cache.
    # - Column layout (bang_theo_cot): 3 cột cần dùng nằm trong 3 mảng 1 chiều riêng, xếp sát nhau.
    #   Mỗi cache line 64 byte nạp liền 16 giá trị discount liên tiếp, không đụng tới 14 cột thừa.
    dung_luong_can_mb = SO_COT_TRUY_VAN_PHAN_1 * SO_BYTE_MOI_INT32 * so_dong / 1e6
    dung_luong_toan_bang_mb = SO_COT_LINEORDER * SO_BYTE_MOI_INT32 * so_dong / 1e6

    print(f"Số dòng: {so_dong:,}   |   dữ liệu query cần: {dung_luong_can_mb:.0f} MB / toàn bảng: {dung_luong_toan_bang_mb:.0f} MB")
    print(f"Row layout   : {thoi_gian_hang * 1000:8.1f} ms  (mỗi dòng 68 byte nằm liền nhau, phải lướt qua cả 17 cột)")
    print(f"Column layout: {thoi_gian_cot * 1000:8.1f} ms  (3 mảng liên tục)")
    print(f"=> column nhanh hơn ~{thoi_gian_hang / thoi_gian_cot:.1f}x, kết quả giống nhau: {ket_qua_hang:,}")


# ============================================================================
# PHẦN 2. NÉN RLE VÀ THAO TÁC TRỰC TIẾP TRÊN DỮ LIỆU NÉN
# ============================================================================
def ma_hoa_rle(mang_da_sap_xep):
    """Nén RLE: gom các giá trị giống nhau liên tiếp thành (gia_tri, so_lan_lap)."""
    vi_tri_doi = np.flatnonzero(mang_da_sap_xep[1:] != mang_da_sap_xep[:-1]) + 1
    vi_tri_bat_dau = np.concatenate(([0], vi_tri_doi))
    gia_tri_moi_cum = mang_da_sap_xep[vi_tri_bat_dau]
    so_lan_lap_moi_cum = np.diff(np.concatenate((vi_tri_bat_dau, [len(mang_da_sap_xep)])))
    return gia_tri_moi_cum, so_lan_lap_moi_cum


def demo_phan_2_nen_rle(so_dong, bo_sinh_ngau_nhien):
    """Minh họa tỷ lệ nén RLE và tốc độ đếm COUNT(*) trực tiếp trên dữ liệu nén."""
    in_tieu_de_phan("PHẦN 2. Nén RLE trên cột đã sort + thao tác trực tiếp trên dữ liệu nén")

    cot_ngay = np.sort(bo_sinh_ngau_nhien.integers(0, SO_NGAY_PHAN_BIET_RLE, so_dong, dtype=np.int32))
    gia_tri_cum, so_lan_lap = ma_hoa_rle(cot_ngay)
    in_mau_du_lieu_phan_2(cot_ngay, gia_tri_cum, so_lan_lap)
    print()

    print("Ví dụ minh họa của bài báo:  1,1,1,2,2  ->  (1 x 3), (2 x 2)")
    gt_mau, sl_mau = ma_hoa_rle(np.array([1, 1, 1, 2, 2]))
    print("  encode thử:", list(zip(gt_mau.tolist(), sl_mau.tolist())))
    print(f"\nCột orderdate: {cot_ngay.nbytes / 1e6:.1f} MB thô  ->  RLE: {(gia_tri_cum.nbytes + so_lan_lap.nbytes) / 1e3:.1f} KB  ({len(gia_tri_cum):,} run, độ dài run trung bình ~{so_dong / len(gia_tri_cum):,.0f})")

    # So sánh đếm trên cột thô (hàng triệu phần tử) vs đếm thẳng trên ~2.400 cụm RLE.
    dem_thuong = lambda: int(((cot_ngay >= NGAY_BAT_DAU_LOC_RLE) & (cot_ngay <= NGAY_KET_THUC_LOC_RLE)).sum())
    dem_rle = lambda: int(so_lan_lap[(gia_tri_cum >= NGAY_BAT_DAU_LOC_RLE) & (gia_tri_cum <= NGAY_KET_THUC_LOC_RLE)].sum())

    ket_qua_thuong, thoi_gian_thuong = do_thoi_gian_nhanh_nhat(dem_thuong)
    ket_qua_rle, thoi_gian_rle = do_thoi_gian_nhanh_nhat(dem_rle)
    assert ket_qua_thuong == ket_qua_rle

    print(f"\nCOUNT(*) WHERE orderdate BETWEEN {NGAY_BAT_DAU_LOC_RLE} AND {NGAY_KET_THUC_LOC_RLE}")
    print(f"  Giải nén / duyệt từng giá trị : {thoi_gian_thuong * 1e3:8.3f} ms")
    print(f"  Thao tác trực tiếp trên RLE   : {thoi_gian_rle * 1e3:8.3f} ms   (~{thoi_gian_thuong / thoi_gian_rle:,.0f}x)   kết quả giống nhau: {ket_qua_thuong:,}")


# ============================================================================
# PHẦN 3. INVISIBLE JOIN TỪNG BƯỚC (DỮ LIỆU MẪU FIGURE 2-4 CỦA BÀI BÁO)
# ============================================================================
def demo_phan_3_invisible_join():
    """Trình diễn liền mạch 3 pha Invisible Join + Between-Predicate Rewriting."""
    in_tieu_de_phan("PHẦN 3. Invisible join từng bước (dữ liệu mẫu = Figure 2-4 của bài báo)")
    khach, ncc, ngay, fact = tao_du_lieu_mau_bai_bao()
    in_du_lieu_mau_phan_3(khach, ncc, ngay, fact)

    # PHA 1: Lọc từng bảng chiều -> thu được tập khóa thỏa điều kiện.
    khoa_khach = {k for k, kv in zip(khach["custkey"], khach["region"]) if kv == "Asia"}
    khoa_ncc = {k for k, kv in zip(ncc["suppkey"], ncc["region"]) if kv == "Asia"}
    khoa_ngay = {k for k, nam in zip(ngay["datekey"], ngay["year"]) if NAM_BAT_DAU <= nam <= NAM_KET_THUC_LOC}
    print(f"PHA 1 (lọc bảng chiều): customer={sorted(khoa_khach)}, supplier={sorted(khoa_ncc)}, dwdate={sorted(khoa_ngay)}")

    # PHA 2: Probe từng cột khóa ngoại của bảng fact -> tạo bitmap 0/1 rồi AND -> position list P.
    bm_khach = np.array([k in khoa_khach for k in fact["custkey"]], dtype=int)
    bm_ncc = np.array([k in khoa_ncc for k in fact["suppkey"]], dtype=int)
    bm_ngay = np.array([k in khoa_ngay for k in fact["orderdate"]], dtype=int)
    bm_tong_hop = bm_khach & bm_ncc & bm_ngay
    vi_tri = np.flatnonzero(bm_tong_hop)
    print(f"\nPHA 2 (AND bitmap): cust={bm_khach.tolist()} & supp={bm_ncc.tolist()} & date={bm_ngay.tolist()}")
    print(f"  => AND = {bm_tong_hop.tolist()}   -> position list P = {vi_tri.tolist()}")

    # PHA 3 (Late Materialization): chỉ lấy giá trị cột cho các vị trí trong P rồi GROUP BY.
    anh_xa_nam = dict(zip(ngay["datekey"], ngay["year"]))
    ds_qg_khach = [khach["nation"][k - 1] for k in fact["custkey"][vi_tri]]
    ds_qg_ncc = [ncc["nation"][k - 1] for k in fact["suppkey"][vi_tri]]
    ds_nam = [anh_xa_nam[k] for k in fact["orderdate"][vi_tri]]
    ds_doanh_thu = fact["revenue"][vi_tri]

    ket_qua = {}
    for qg_khach, qg_ncc, nam, doanh_thu in zip(ds_qg_khach, ds_qg_ncc, ds_nam, ds_doanh_thu):
        khoa_nhom = (qg_khach, qg_ncc, nam)
        ket_qua[khoa_nhom] = ket_qua.get(khoa_nhom, 0) + int(doanh_thu)

    assert ket_qua == tinh_join_ngay_tho_kiem_chung(khach, ncc, ngay, fact)
    print(f"\nPHA 3 (lấy giá trị cho {len(vi_tri)}/{len(fact['revenue'])} dòng qua hết predicate):")
    for khoa_nhom, tong in sorted(ket_qua.items()):
        print("  ", khoa_nhom, tong)

    # Tối ưu Between-Predicate Rewriting: đánh lại khóa theo region để kiểm tra khoảng [min, max].
    khoa_cu = sorted(khoa_khach)
    thu_tu_moi = sorted(range(len(khach["custkey"])), key=lambda i: (khach["region"][i], khach["nation"][i]))
    bang_doi_khoa = {cu + 1: moi + 1 for moi, cu in enumerate(thu_tu_moi)}
    khoa_moi = sorted(bang_doi_khoa[k] for k in khoa_khach)
    print(f"\nBETWEEN-PREDICATE REWRITING: khóa cũ {khoa_cu} (liên tục? {la_tap_khoa_lien_tuc(khoa_cu)})")
    print(f"  -> đánh lại khóa theo region: {khoa_moi} (liên tục? {la_tap_khoa_lien_tuc(khoa_moi)})")
    print(f"  => viết lại thành: {khoa_moi[0]} <= lo.custkey <= {khoa_moi[-1]} (không cần hash table)")


# ============================================================================
# PHẦN 4. MINI-BENCHMARK KIỂU SSBM QUERY 3.1
# ============================================================================
def demo_phan_4_mini_benchmark(so_dong, bo_sinh_ngau_nhien):
    """So sánh 3 kế hoạch thực thi (A: Row-store, B: Invisible Join, C: + Between) cạnh nhau."""
    in_tieu_de_phan("PHẦN 4. Mini-benchmark kiểu SSBM Q3.1: customer.region = supplier.region = 'ASIA', 1992-1997")
    chieu, fact_cot = tao_luoc_do_sao(so_dong, bo_sinh_ngau_nhien)
    in_mau_luoc_do_sao_phan_4(so_dong, fact_cot)
    fact_hang = chuyen_bang_fact_sang_dang_hang(fact_cot, so_dong)

    def ke_hoach_a_row_store():
        """A. Row-store: lọc nối tiếp từng bảng chiều, copy nguyên bản ghi 68B qua từng bước."""
        dong = fact_hang[(chieu["c_region"] == MA_KHU_VUC_ASIA)[fact_hang["custkey"]]]
        dong = dong[(chieu["s_region"] == MA_KHU_VUC_ASIA)[dong["suppkey"]]]
        ngay_thoa = (chieu["d_year"] >= NAM_BAT_DAU) & (chieu["d_year"] <= NAM_KET_THUC_LOC)
        dong = dong[ngay_thoa[dong["orderdate"]]]
        return tinh_tong_theo_nhom(chieu["c_nation"][dong["custkey"]], chieu["s_nation"][dong["suppkey"]], chieu["d_year"][dong["orderdate"]], dong["revenue"])

    def ke_hoach_b_invisible_join():
        """B. Invisible Join + tra bảng: AND 3 bitmap -> Late Materialization ở pha 3."""
        ngay_thoa = (chieu["d_year"] >= NAM_BAT_DAU) & (chieu["d_year"] <= NAM_KET_THUC_LOC)
        vi_tri = np.flatnonzero((chieu["c_region"] == MA_KHU_VUC_ASIA)[fact_cot["custkey"]] & (chieu["s_region"] == MA_KHU_VUC_ASIA)[fact_cot["suppkey"]] & ngay_thoa[fact_cot["orderdate"]])
        return tinh_tong_theo_nhom(chieu["c_nation"][fact_cot["custkey"][vi_tri]], chieu["s_nation"][fact_cot["suppkey"][vi_tri]], chieu["d_year"][fact_cot["orderdate"][vi_tri]], fact_cot["revenue"][vi_tri])

    def ke_hoach_c_invisible_join_between():
        """C. Invisible Join + Between-Predicate Rewriting: thay tra bảng bằng so sánh khoảng [min, max]."""
        c_min, c_max = tim_khoang_khoa_lien_tuc(chieu["c_region"] == MA_KHU_VUC_ASIA)
        s_min, s_max = tim_khoang_khoa_lien_tuc(chieu["s_region"] == MA_KHU_VUC_ASIA)
        d_min, d_max = tim_khoang_khoa_lien_tuc((chieu["d_year"] >= NAM_BAT_DAU) & (chieu["d_year"] <= NAM_KET_THUC_LOC))
        ck, sk, dk = fact_cot["custkey"], fact_cot["suppkey"], fact_cot["orderdate"]
        vi_tri = np.flatnonzero((ck >= c_min) & (ck <= c_max) & (sk >= s_min) & (sk <= s_max) & (dk >= d_min) & (dk <= d_max))
        return tinh_tong_theo_nhom(chieu["c_nation"][ck[vi_tri]], chieu["s_nation"][sk[vi_tri]], chieu["d_year"][dk[vi_tri]], fact_cot["revenue"][vi_tri])

    kq_a, tg_a = do_thoi_gian_nhanh_nhat(ke_hoach_a_row_store)
    kq_b, tg_b = do_thoi_gian_nhanh_nhat(ke_hoach_b_invisible_join)
    kq_c, tg_c = do_thoi_gian_nhanh_nhat(ke_hoach_c_invisible_join_between)
    assert kq_a == kq_b == kq_c

    print(f"Số dòng fact: {so_dong:,}  |  số nhóm kết quả: {len(kq_a)}  |  3 plan cho kết quả GIỐNG NHAU (tổng doanh thu: {sum(kq_a.values()):,})")
    print(f"  A. Kiểu row-store (copy cả tuple 68B qua từng join) : {tg_a * 1000:8.1f} ms")
    print(f"  B. Invisible join, predicate = tra bảng (late mat.)  : {tg_b * 1000:8.1f} ms   ({tg_a / tg_b:4.1f}x so với A)")
    print(f"  C. Invisible join + between-predicate rewriting      : {tg_c * 1000:8.1f} ms   ({tg_a / tg_c:4.1f}x so với A)")


# ============================================================================
# ĐIỂM BẮT ĐẦU CHƯƠNG TRÌNH
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Demo Column-Stores vs Row-Stores (Abadi et al., SIGMOD 2008)")
    parser.add_argument("--part", choices=["all", "1", "2", "3", "4"], default="all", help="chọn phần chạy (mặc định all)")
    parser.add_argument("--rows", type=int, default=6_000_000, help="số dòng bảng fact (mặc định 6 triệu)")
    parser.add_argument("--seed", type=int, default=42, help="seed ngẫu nhiên (mặc định 42)")
    args = parser.parse_args()

    bo_sinh_ngau_nhien = np.random.default_rng(args.seed)
    print(f"numpy {np.__version__}, rows = {args.rows:,}, seed = {args.seed}, part = {args.part}")

    cac_phan = {
        "1": lambda: demo_phan_1_layout_hang_va_cot(args.rows, bo_sinh_ngau_nhien),
        "2": lambda: demo_phan_2_nen_rle(args.rows, bo_sinh_ngau_nhien),
        "3": demo_phan_3_invisible_join,
        "4": lambda: demo_phan_4_mini_benchmark(args.rows, bo_sinh_ngau_nhien),
    }
    danh_sach_chay = ["1", "2", "3", "4"] if args.part == "all" else [args.part]
    for ma_phan in danh_sach_chay:
        cac_phan[ma_phan]()

    print("\nLưu ý: mô hình trong bộ nhớ bằng numpy, không phải C-Store/System X; xem docstring đầu file.")


if __name__ == "__main__":
    main()
