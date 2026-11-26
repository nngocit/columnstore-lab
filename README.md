# ColumnStore Lab — Mô Phỏng Hệ Quản Trị Cơ Sở Dữ Liệu Dạng Cột (SIGMOD 2008)

Ứng dụng mô phỏng tương tác giáo dục về kiến trúc Column-Oriented DBMS và thuật toán Invisible Join dựa trên bài báo khoa học kinh điển:
> **"Query Execution in Column-Oriented Database Systems"**  
> *Daniel J. Abadi, Samuel R. Madden, Nabil Hachem (SIGMOD 2008)*  
> Thử nghiệm trên bộ dữ liệu chuẩn Star Schema Benchmark (SSBM Q3.1).

- **Tác giả:** Nguyễn Thanh Xuân Ngọc (MSHV: 2618480104014)
- **Công nghệ:** Python (NumPy), JavaScript (Vanilla ES6), HTML5 Native `<dialog>`, CSS3 Glassmorphism
- **Live Demo Cloudflare Pages:** [https://cs-lab-a3k.pages.dev](https://cs-lab-a3k.pages.dev)
- **Live Demo GitHub Pages:** [https://nngocit.github.io/columnstore-lab/](https://nngocit.github.io/columnstore-lab/)
- **Mã nguồn GitHub:** [https://github.com/nngocit/columnstore-lab](https://github.com/nngocit/columnstore-lab)

---

## 1. Cac Tinh Nang Chinh

- **Tab 0 - Star Schema Overview:** Mo hinh luu tru Fact (lineorder) va 4 bang Dimension (customer, supplier, dwdate, part).
- **Tab 1 - Row-Store vs Column-Store:** So sanh co che nap bo nho dem Cache Line va bang thong bus RAM giua NSM va DSM.
- **Tab 2 - Compression Techniques:** Mo phong 4 phuong phap nen cot: RLE, Dictionary Encoding, Bit-Packing va Frame-of-Reference.
- **Tab 3 - Invisible Join:** Quy trinh 3 pha (Dimension Filtering, Fact Probing & Bitmap AND, Late Materialization).
- **Tab 4 - Performance Benchmark:** So sanh hieu nang 3 chien luoc (Plan A Row-Store, Plan B Column-Store co ban, Plan C Column-Store toi uu khoang).
- **Tab 5 - Python Engine:** Toan bo ma nguon mo phong backend.

---

## 2. Huong Dan Khoi Chay

### Cach 1: Chay Local voi Python Web Server

```bash
cd Demo_NguyenThanhXuanNgoc
python web_server.py
```
Truy cap: `http://localhost:8000/` tren trinh duyet.

### Cach 2: Chay Truc Tiep Client-side

Mo truc tiep tep `index.html` bang bat ky trinh duyet hien dai nao (Chrome, Edge, Firefox, Safari).

---

## 3. Trien Khai Cloudflare Pages

- **Framework preset:** None
- **Build command:** (de trong)
- **Build output directory:** `/` (thu muc goc chua `index.html`)
