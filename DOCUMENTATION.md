# TÀI LIỆU DỰ ÁN: MINESWEEPER (DÒ MÌN)

## Mục lục

1. [Giới thiệu tổng quan](#1-giới-thiệu-tổng-quan)
2. [Luật chơi](#2-luật-chơi)
3. [Kiến trúc chương trình](#3-kiến-trúc-chương-trình)
4. [Cấu trúc dữ liệu](#4-cấu-trúc-dữ-liệu)
5. [Các thuật toán được áp dụng](#5-các-thuật-toán-được-áp-dụng)
   - 5.1 Đặt mìn ngẫu nhiên (Deferred Random Sampling)
   - 5.2 Tính trước số mìn lân cận (Neighbour Pre-computation)
   - 5.3 Mở ô trống – Tìm kiếm theo chiều sâu DFS (Flood Fill)
   - 5.4 Chord – Mở tự động các ô lân cận
   - 5.5 Kiểm tra chiến thắng
6. [Phân tích Time Complexity và Space Complexity](#6-phân-tích-time-complexity-và-space-complexity)
7. [So sánh DFS và BFS trong bài toán Flood Fill](#7-so-sánh-dfs-và-bfs-trong-bài-toán-flood-fill)
8. [Hướng dẫn sử dụng](#8-hướng-dẫn-sử-dụng)
9. [Cấu trúc file dự án](#9-cấu-trúc-file-dự-án)

---

## 1. Giới thiệu tổng quan

**Minesweeper (Dò mìn)** là trò chơi logic đơn người chơi kinh điển. Người chơi cần mở tất cả các ô an toàn trên bảng mà không chạm vào quả mìn nào. Trò chơi sử dụng các con số hiển thị trên ô đã mở để suy luận vị trí mìn.

Chương trình được viết bằng **Python** sử dụng thư viện đồ hoạ **Pygame**, hỗ trợ 3 mức độ khó:

| Mức độ | Kích thước | Số mìn |
|--------|-----------|--------|
| Dễ (Easy) | 5 × 5 = 25 ô | 4 |
| Trung bình (Medium) | 9 × 9 = 81 ô | 10 |
| Khó (Hard) | 16 × 16 = 256 ô | 40 |

---

## 2. Luật chơi

- **Mở ô (Left-click):** Click chuột trái để lật mở một ô. Nếu ô đó có số, số đó cho biết có bao nhiêu quả mìn trong 8 ô xung quanh (ngang, dọc, chéo). Nếu ô trống (số = 0), tất cả các ô trống liền kề sẽ tự động được mở ra (dùng thuật toán DFS).
- **Đặt cờ (Right-click):** Click chuột phải để đánh dấu/bỏ đánh dấu cờ trên ô nghi ngờ có mìn.
- **Chord (Middle-click):** Click chuột giữa lên ô đã mở có số — nếu số cờ xung quanh bằng đúng con số đó, các ô chưa cắm cờ xung quanh sẽ tự động được mở.
- **Thắng:** Mở hết tất cả các ô an toàn (không phải mìn).
- **Thua:** Click vào ô chứa mìn → game kết thúc ngay lập tức, toàn bộ mìn được hiển thị.

---

## 3. Kiến trúc chương trình

Chương trình được thiết kế theo mô hình **tách biệt Logic – Giao diện (Separation of Concerns)**:

```
┌──────────────────────────────────────────┐
│              main() – Điểm vào           │
│  ┌──────────────┐  ┌──────────────────┐  │
│  │  Menu Screen  │→│    Game Loop     │  │
│  │ (chọn độ khó) │  │  (vòng lặp game) │  │
│  └──────────────┘  │  ┌────────────┐  │  │
│                     │  │   Board    │  │  │
│                     │  │ (logic     │  │  │
│                     │  │  thuần tuý)│  │  │
│                     │  └────────────┘  │  │
│                     │  ┌────────────┐  │  │
│                     │  │  Renderer  │  │  │
│                     │  │ (vẽ giao   │  │  │
│                     │  │  diện)     │  │  │
│                     │  └────────────┘  │  │
│                     └──────────────────┘  │
└──────────────────────────────────────────┘
```

### Các thành phần chính:

| Thành phần | Mô tả | Dòng code |
|-----------|-------|-----------|
| **`Board`** (class) | Chứa toàn bộ logic game: đặt mìn, mở ô (DFS), cắm cờ, kiểm tra thắng/thua. Không phụ thuộc Pygame. | 63–188 |
| **`Renderer`** (class) | Đọc trạng thái từ `Board` và vẽ lên màn hình Pygame: ô, số, cờ, mìn, header. | 193–348 |
| **`difficulty_menu()`** | Màn hình chọn độ khó trước khi bắt đầu game. | 352–397 |
| **`game_loop()`** | Vòng lặp chính: xử lý sự kiện Pygame, gọi Board và Renderer mỗi frame (60 FPS). | 432–525 |
| **`main()`** | Điểm vào chương trình, quản lý luồng menu → game → restart/quit. | 530–549 |

---

## 4. Cấu trúc dữ liệu

Bảng game được biểu diễn bằng **4 ma trận 2 chiều** (mảng 2D), mỗi ma trận có kích thước `rows × cols`:

### 4.1. Ma trận `mines[r][c]` — Vị trí mìn
- **Kiểu:** `bool`
- **Ý nghĩa:** `True` nếu ô `(r, c)` chứa mìn, `False` nếu an toàn.
- **Khởi tạo:** Tất cả `False`. Chỉ được gán `True` khi đặt mìn sau lần click đầu tiên.

### 4.2. Ma trận `revealed[r][c]` — Trạng thái đã mở
- **Kiểu:** `bool`
- **Ý nghĩa:** `True` nếu ô `(r, c)` đã được người chơi mở (lật).

### 4.3. Ma trận `flagged[r][c]` — Trạng thái cắm cờ
- **Kiểu:** `bool`
- **Ý nghĩa:** `True` nếu ô `(r, c)` đang được đánh dấu cờ.

### 4.4. Ma trận `neighbour[r][c]` — Số mìn lân cận
- **Kiểu:** `int`
- **Ý nghĩa:**
  - Nếu ô là mìn: giá trị = `−1` (sentinel).
  - Nếu ô an toàn: giá trị = số lượng mìn trong 8 ô xung quanh (0–8).

### Tổng bộ nhớ

Với bảng kích thước R × C:

**Tổng bộ nhớ = 4 × R × C = O(R × C)**

**Ví dụ cụ thể:**
- Easy (5×5): 4 × 25 = 100 giá trị
- Medium (9×9): 4 × 81 = 324 giá trị
- Hard (16×16): 4 × 256 = 1024 giá trị

---

## 5. Các thuật toán được áp dụng

### 5.1. Đặt mìn ngẫu nhiên (Deferred Random Sampling)

#### Mô tả
Mìn **không được đặt khi khởi tạo bảng**, mà được **trì hoãn đến lần click chuột đầu tiên** của người chơi. Điều này đảm bảo lần click đầu luôn an toàn (không bao giờ trúng mìn) — đây là hành vi chuẩn của Minesweeper kinh điển.

#### Mã giả (Pseudocode)

```
PLACE_MINES(safe_r, safe_c, num_mines):
    1. Tạo "vùng an toàn" = tập hợp 9 ô trong ô 3×3 quanh (safe_r, safe_c)
    2. Tạo danh sách ứng viên = tất cả ô KHÔNG nằm trong vùng an toàn
    3. Chọn ngẫu nhiên num_mines ô từ danh sách (dùng random.sample)
    4. Đánh dấu mines[r][c] = True cho các ô được chọn
    5. Gọi COMPUTE_NEIGHBOURS() để tính số mìn lân cận
```

#### Tham chiếu mã nguồn

```python
# minesweeper.py, dòng 84–115 — phương thức Board._place_mines()
def _place_mines(self, safe_r, safe_c):
    safe = set()
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            nr, nc = safe_r + dr, safe_c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                safe.add((nr, nc))
    candidates = [(r, c) for r in range(self.rows)
                         for c in range(self.cols) if (r, c) not in safe]
    chosen = random.sample(candidates, self.num_mines)
    for r, c in chosen:
        self.mines[r][c] = True
```

#### Phân tích độ phức tạp

| | Chi tiết | Độ phức tạp |
|---|---|---|
| **Time** | Duyệt R × C ô để tạo danh sách ứng viên + `random.sample` chọn k mìn | **O(R × C)** |
| **Space** | Danh sách ứng viên chứa tối đa R × C − 9 phần tử | **O(R × C)** |

---

### 5.2. Tính trước số mìn lân cận (Neighbour Pre-computation)

#### Mô tả
Ngay sau khi đặt mìn, chương trình duyệt **toàn bộ** bảng một lần duy nhất để tính giá trị `neighbour[r][c]` cho mọi ô. Giá trị này được dùng suốt game mà không cần tính lại.

#### Mã giả

```
COMPUTE_NEIGHBOURS():
    Với mỗi ô (r, c) trên bảng:
        Nếu mines[r][c] == True:
            neighbour[r][c] = -1         // ô mìn, đánh dấu sentinel
        Ngược lại:
            count = 0
            Duyệt 8 ô lân cận (dr, dc) ∈ {-1, 0, 1}² \ {(0,0)}:
                Nếu ô (r+dr, c+dc) hợp lệ VÀ là mìn:
                    count += 1
            neighbour[r][c] = count
```

#### Tham chiếu mã nguồn

```python
# minesweeper.py, dòng 105–115 — trong Board._place_mines()
for r in range(self.rows):
    for c in range(self.cols):
        if self.mines[r][c]:
            self.neighbour[r][c] = -1
            continue
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.mines[nr][nc]:
                    count += 1
        self.neighbour[r][c] = count
```

#### Phân tích độ phức tạp

| | Chi tiết | Độ phức tạp |
|---|---|---|
| **Time** | Duyệt R × C ô, mỗi ô kiểm tra tối đa 8 láng giềng → R × C × 8 | **O(R × C)** |
| **Space** | Ma trận `neighbour` kích thước R × C | **O(R × C)** |

> **Lưu ý:** Hằng số 8 (kiểm tra 8 hướng) không phụ thuộc kích thước bảng, nên bị loại khỏi ký hiệu Big-O.

---

### 5.3. ⭐ Mở ô trống – Tìm kiếm theo chiều sâu DFS (Flood Fill)

Đây là **thuật toán cốt lõi** của trò chơi.

#### Bài toán

Khi người chơi click vào một ô an toàn có `neighbour = 0` (ô trống, không có mìn nào xung quanh), trò chơi cần **tự động mở tất cả các ô trống liền kề** và **các ô có số nằm ở biên** của vùng trống đó. Đây chính là bài toán **flood fill** (lấp đầy vùng) — tương tự thuật toán tô màu trong phần mềm đồ hoạ.

#### Thuật toán: DFS dùng Stack tường minh (Iterative DFS)

Thay vì dùng đệ quy (có nguy cơ tràn stack với bảng lớn), chương trình sử dụng **DFS lặp** với stack tường minh (Python list):

```
DFS_REVEAL(start_r, start_c):
    stack ← [(start_r, start_c)]       // Khởi tạo stack với ô bắt đầu

    WHILE stack không rỗng:
        (r, c) ← stack.pop()           // Lấy phần tử trên cùng (LIFO)

        IF revealed[r][c] OR flagged[r][c]:
            CONTINUE                    // Bỏ qua ô đã xử lý hoặc cắm cờ

        revealed[r][c] ← True          // Mở ô này

        IF neighbour[r][c] == 0:       // Ô trống → mở rộng sang láng giềng
            FOR mỗi hướng (dr, dc) trong 8 hướng:
                (nr, nc) ← (r + dr, c + dc)
                IF (nr, nc) hợp lệ AND chưa mở AND không phải mìn:
                    stack.push((nr, nc))
        // Nếu neighbour > 0 → ô số, chỉ mở nó, KHÔNG mở rộng thêm
```

#### Tham chiếu mã nguồn

```python
# minesweeper.py, dòng 119–133 — phương thức Board._dfs_reveal()
def _dfs_reveal(self, r, c):
    stack = [(r, c)]
    while stack:
        cr, cc = stack.pop()
        if self.revealed[cr][cc]:
            continue
        if self.flagged[cr][cc]:
            continue
        self.revealed[cr][cc] = True
        if self.neighbour[cr][cc] == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if not self.revealed[nr][nc] and not self.mines[nr][nc]:
                            stack.append((nr, nc))
```

#### Minh hoạ chi tiết

Giả sử bảng 5×5 (M = mìn, số = neighbour count):

```
  Bảng:                     Click vào ô (0,0):
  ┌───┬───┬───┬───┬───┐
  │ 0 │ 0 │ 1 │ M │ 1 │    Bước 1: stack = [(0,0)]
  ├───┼───┼───┼───┼───┤    Bước 2: pop (0,0) → mở → neighbour=0 → đẩy láng giềng
  │ 0 │ 0 │ 1 │ 1 │ 1 │    Bước 3: pop (1,1) → mở → neighbour=0 → đẩy láng giềng
  ├───┼───┼───┼───┼───┤    Bước 4: pop (2,2) → mở → neighbour=1 → DỪNG mở rộng
  │ 1 │ 1 │ 1 │ 0 │ 0 │    Bước 5: pop (2,1) → mở → neighbour=1 → DỪNG mở rộng
  ├───┼───┼───┼───┼───┤    Bước 6: pop (2,0) → mở → neighbour=1 → DỪNG mở rộng
  │ M │ 1 │ 0 │ 0 │ 0 │    Bước 7: pop (1,0) → mở → neighbour=0 → đẩy láng giềng
  ├───┼───┼───┼───┼───┤    Bước 8: pop (0,1) → mở → neighbour=0 → đẩy láng giềng
  │ 1 │ 1 │ 0 │ 0 │ 0 │    Bước 9: pop (0,2) → mở → neighbour=1 → DỪNG mở rộng
  └───┴───┴───┴───┴───┘    ... tiếp tục cho đến khi stack rỗng.

  Kết quả: Toàn bộ vùng trống liên thông và viền số được mở.
```

**Nguyên tắc hoạt động:**
1. Ô trống (neighbour = 0): **mở và mở rộng** → đẩy 8 láng giềng vào stack.
2. Ô có số (neighbour > 0): **chỉ mở**, không mở rộng → làm "biên" của vùng.
3. Ô cờ hoặc đã mở: **bỏ qua** → tránh xử lý lặp.

#### Phân tích độ phức tạp

| | Trường hợp tốt nhất | Trường hợp xấu nhất | Chi tiết |
|---|---|---|---|
| **Time** | O(1) — click vào ô có số | **O(R × C)** — toàn bộ bảng trống | Mỗi ô được push/pop tối đa 1 lần nhờ kiểm tra `revealed` |
| **Space** | O(1) — stack chỉ có 1 phần tử | **O(R × C)** — stack chứa mọi ô | Khi bảng gần như trống hoàn toàn |

**Giải thích chi tiết:**

- **Mỗi ô chỉ được xử lý đúng 1 lần:** Khi `pop` một ô ra, kiểm tra `revealed[cr][cc]` — nếu đã mở thì `continue`. Sau khi mở xong, đặt `revealed = True`. Do đó ô không bao giờ bị xử lý lại → **không có trùng lặp**.
- Một ô có thể bị **push nhiều lần** vào stack (từ nhiều láng giềng khác nhau), nhưng chỉ được **xử lý 1 lần** (lần pop đầu tiên). Các lần pop sau sẽ gặp `continue` ngay.
- Tổng số thao tác push ≤ 8 × R × C (mỗi ô có tối đa 8 láng giềng push nó) → vẫn là **O(R × C)**.

---

### 5.4. Chord – Mở tự động các ô lân cận

#### Mô tả

Khi người chơi click chuột giữa vào ô đã mở có số `n`, chương trình đếm số cờ xung quanh. Nếu **số cờ = n**, tất cả ô chưa cắm cờ và chưa mở xung quanh sẽ được `reveal()` — có thể kích hoạt thêm DFS flood fill.

#### Mã giả

```
CHORD(r, c):
    IF ô (r,c) chưa mở HOẶC neighbour[r][c] ≤ 0:
        RETURN

    flag_count ← đếm số ô cắm cờ trong 8 láng giềng

    IF flag_count == neighbour[r][c]:
        Với mỗi láng giềng (nr, nc) chưa cắm cờ và chưa mở:
            REVEAL(nr, nc)     // có thể gọi DFS bên trong
```

#### Tham chiếu mã nguồn

```python
# minesweeper.py, dòng 160–181 — phương thức Board.chord()
def chord(self, r, c):
    if not self.revealed[r][c]:
        return
    n = self.neighbour[r][c]
    if n <= 0:
        return
    flag_count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            ...
            if self.flagged[nr][nc]:
                flag_count += 1
    if flag_count == n:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                ...
                if not self.flagged[nr][nc] and not self.revealed[nr][nc]:
                    self.reveal(nr, nc)
```

#### Phân tích độ phức tạp

| | Chi tiết | Độ phức tạp |
|---|---|---|
| **Time** | Đếm cờ: O(8) = O(1) + gọi `reveal()` tối đa 8 lần → mỗi lần có thể kích hoạt DFS | **O(1) + chi phí DFS** |
| **Space** | Không dùng bộ nhớ phụ (ngoài DFS nếu kích hoạt) | **O(1)** |

---

### 5.5. Kiểm tra chiến thắng (Win Detection)

#### Mô tả

Sau mỗi lần mở ô thành công, chương trình kiểm tra: nếu **tất cả ô không phải mìn đều đã mở** → người chơi thắng.

#### Mã giả

```
CHECK_WIN():
    Với mỗi ô (r, c):
        IF NOT mines[r][c] AND NOT revealed[r][c]:
            RETURN False    // còn ô an toàn chưa mở
    RETURN True             // tất cả ô an toàn đã mở → THẮNG
```

#### Tham chiếu mã nguồn

```python
# minesweeper.py, dòng 183–187 — phương thức Board._check_win()
def _check_win(self):
    for r in range(self.rows):
        for c in range(self.cols):
            if not self.mines[r][c] and not self.revealed[r][c]:
                return
    self.won = True
```

#### Phân tích độ phức tạp

| | Chi tiết | Độ phức tạp |
|---|---|---|
| **Time** | Duyệt toàn bộ bảng R × C mỗi lần kiểm tra | **O(R × C)** |
| **Space** | Không dùng bộ nhớ phụ | **O(1)** |

> **Ghi chú:** Hàm này được gọi sau mỗi lần `reveal()`. Trong thực tế, với bảng lớn nhất (16×16 = 256 ô), chi phí là không đáng kể.

---

## 6. Phân tích Time Complexity và Space Complexity

Gọi **N = R × C** là tổng số ô, **k** là số mìn.

### 6.1. Bảng tổng hợp tất cả thao tác

| Thao tác | Time Complexity | Space Complexity | Ghi chú |
|----------|----------------|-----------------|---------|
| Khởi tạo bảng | O(N) | O(N) | Tạo 4 ma trận |
| Đặt mìn (`_place_mines`) | O(N) | O(N) | Tạo danh sách ứng viên |
| Tính neighbour | O(N) | O(N) | N × 8 phép so sánh |
| **DFS Flood Fill** (`_dfs_reveal`) | **O(N)** worst-case | **O(N)** worst-case | Thuật toán chính |
| Đặt/bỏ cờ (`toggle_flag`) | O(1) | O(1) | Chỉ đổi 1 giá trị bool |
| Chord | O(1) + DFS | O(1) + DFS | Tối đa 8 láng giềng |
| Kiểm tra thắng (`_check_win`) | O(N) | O(1) | Duyệt toàn bộ bảng |
| Vẽ bảng (`draw_board`) | O(N) | O(1) | Vẽ từng ô mỗi frame |
| **Toàn bộ 1 ván game** | **O(N)** amortised | **O(N)** | Chi phí trung bình |

### 6.2. Phân tích chi tiết theo mức độ khó

| Mức độ | N | DFS worst-case | Bộ nhớ ma trận | Stack DFS max |
|--------|---|---------------|----------------|---------------|
| Easy 5×5 | 25 | 25 thao tác | 100 giá trị | 25 phần tử |
| Medium 9×9 | 81 | 81 thao tác | 324 giá trị | 81 phần tử |
| Hard 16×16 | 256 | 256 thao tác | 1024 giá trị | 256 phần tử |

> Với các kích thước bảng trong game, mọi thao tác đều hoàn thành **gần như tức thì** (dưới 1ms).

### 6.3. Phân tích amortised (chi phí khấu hao) cho toàn bộ ván chơi

Trong suốt **một ván chơi** (từ click đầu tiên đến thắng/thua):
- **Tổng số ô được reveal:** tối đa N − k (tất cả ô an toàn).
- **Tổng thao tác DFS:** Mỗi ô chỉ được reveal đúng 1 lần. Dù gọi `_dfs_reveal()` nhiều lần, tổng số ô xử lý qua tất cả các lần gọi ≤ N.
- **Chi phí khấu hao mỗi click:** O(N / m) trong đó m là số lần click → trung bình rất nhỏ.

**Tổng Time cho cả ván = O(N) (khởi tạo) + O(N) (tổng DFS) + O(m × N) (win check)**

Trong đó m là số lần click. Với m ≤ N và N ≤ 256, tổng chi phí ≈ O(N²) worst-case, nhưng trên thực tế rất nhanh.

---

## 7. So sánh DFS và BFS trong bài toán Flood Fill

| Tiêu chí | DFS (Stack – LIFO) | BFS (Queue – FIFO) |
|----------|-------------------|-------------------|
| **Cấu trúc dữ liệu** | Stack (Python `list`) | Queue (`collections.deque`) |
| **Thứ tự duyệt** | Đi sâu trước, quay lại sau | Duyệt theo lớp (wavefront) |
| **Time Complexity** | O(N) | O(N) |
| **Space Complexity** | O(N) worst-case | O(N) worst-case |
| **Kết quả** | ✅ Cùng tập ô được mở | ✅ Cùng tập ô được mở |
| **Bộ nhớ thực tế** | Thường **thấp hơn** — chỉ lưu 1 nhánh | Thường **cao hơn** — lưu toàn bộ wavefront |
| **Triển khai Python** | `list.append()` + `list.pop()` — đơn giản | `deque.append()` + `deque.popleft()` |
| **Hiệu ứng hình ảnh** | Mở theo nhánh sâu | Mở lan toả đều đặn |

### Lý do chọn DFS:

1. **Yêu cầu đề bài** — đề bài yêu cầu sử dụng thuật toán DFS.
2. **Đơn giản** — `list` của Python tự nhiên hoạt động như stack (`append`/`pop`), không cần import thêm.
3. **Hiệu quả bộ nhớ** — DFS thường dùng ít bộ nhớ hơn BFS trong thực tế vì chỉ lưu một nhánh đang khám phá, trong khi BFS lưu toàn bộ "mặt sóng" (wavefront).
4. **Kết quả tương đương** — Cả DFS và BFS đều mở ra **cùng một tập ô** (connected component), chỉ khác thứ tự mở.

### Minh hoạ thứ tự duyệt

```
Bảng ví dụ (0 = trống, # = số):
    0  0  #
    0  0  #
    #  #  #

DFS (bắt đầu từ (0,0)):          BFS (bắt đầu từ (0,0)):
    1  4  6                           1  2  5
    2  3  7                           3  4  6
    5  8  9                           7  8  9

→ DFS đi sâu theo 1 hướng trước   → BFS mở đều theo vòng tròn
→ Kết quả cuối cùng: GIỐNG NHAU   → Kết quả cuối cùng: GIỐNG NHAU
```

---

## 8. Hướng dẫn sử dụng

### Cài đặt

```bash
# Tạo môi trường ảo và cài pygame
python3 -m venv .venv
source .venv/bin/activate
pip install pygame-ce
```

### Chạy game

```bash
source .venv/bin/activate
python3 minesweeper.py
```

### Điều khiển

| Thao tác | Chức năng |
|----------|----------|
| Click trái | Mở ô |
| Click phải | Đặt/bỏ cờ |
| Click giữa | Chord (mở tự động lân cận) |
| Click vào 🙂 | Chơi lại |
| Phím `R` | Chơi lại (cùng độ khó) |
| Phím `M` | Quay về menu chọn độ khó |
| Phím `Q` | Thoát game |

### Giao diện

- **Góc trái trên:** Bộ đếm mìn còn lại (tổng mìn − số cờ đã đặt)
- **Góc phải trên:** Đồng hồ đếm giây (tối đa 999)
- **Giữa trên:** Nút mặt cười — 🙂 đang chơi, 😎 thắng, 😵 thua

---

## 9. Cấu trúc file dự án

```
BTL_AI/
├── minesweeper.py      # Mã nguồn chính (game logic + GUI)
├── DOCUMENTATION.md    # Tài liệu dự án (file này)
└── .venv/              # Môi trường ảo Python (không commit)
```

---

*Tài liệu được viết cho Bài tập lớn môn Trí tuệ Nhân tạo.*
