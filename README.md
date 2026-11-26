# ColumnStore Lab — Mo Phong He Quan Tri Co So Du Lieu Dang Cot

Ung dung mo phong tuong tac giao duc ve kien truc Column-Oriented DBMS va thuat toan Invisible Join tren bo du lieu Star Schema Benchmark (SSBM Q3.1).

- **Tac gia:** Nguyen Thanh Xuan Ngoc
- **Cong nghe:** Python (NumPy), JavaScript (Vanilla ES6), HTML5 Canvas/Dialog, CSS3 Glassmorphism

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
