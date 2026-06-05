# Kế Hoạch Triển Khai Thực Tế: Data Augmentation & Normalization Cho Dịch NL -> FOL

Tài liệu này trình bày quy trình xử lý dữ liệu tinh giản, tập trung vào tính khả thi, tối ưu hóa công sức phát triển (ROI cao) và hạn chế tối đa rủi ro lệch phân phối (domain shift) cho bộ dữ liệu dịch Ngôn ngữ tự nhiên sang Logic mệnh đề bậc một (NL -> FOL) quy mô nhỏ đến trung bình.

---

## 📌 Phân Biệt Các Khái Niệm Cốt Lõi (Conceptual Separation)

Để tối ưu hóa pipeline huấn luyện và tránh nhầm lẫn trong thiết kế hệ thống, các bước xử lý dữ liệu được chia làm 3 phạm trù độc lập:

1. **Data Normalization (Chuẩn hóa dữ liệu)**: Định dạng lại dữ liệu hiện có về dạng chuẩn hóa (canonical representation) để thu hẹp không gian nhãn mục tiêu (target label space), làm giảm entropy phân phối đầu ra của mô hình dịch. Quá trình này **không** sinh thêm dữ liệu mới và áp dụng cho 100% mẫu dữ liệu (bao gồm cả tập train, validation và test).
2. **Data Augmentation (Tăng cường dữ liệu)**: Quá trình tạo ra các mẫu dữ liệu huấn luyện mới từ dữ liệu gốc nhằm gia tăng quy mô và độ đa dạng cho tập huấn luyện. Chỉ áp dụng trên tập huấn luyện (Train Set) sau khi đã phân tách.
3. **Curriculum Learning (Học theo chương trình)**: Chiến lược lên lịch trình (scheduling) thứ tự xuất hiện của các mẫu huấn luyện trong quá trình tối ưu hóa mô hình (ví dụ: huấn luyện từ mẫu ngắn đến mẫu dài). Đây là chiến lược huấn luyện, không phải là bước sinh dữ liệu.

---

## 📊 Bảng Đánh Giá & Phân Loại Các Phương Pháp (ROI-Focused Evaluation)

| Phương pháp | Phân loại | Mức độ ưu tiên | Rủi ro Domain Shift | Hiệu quả thực tế | Ghi chú triển khai |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Quantifier Variable Canonicalization** | Normalization | **Bắt buộc (100%)** | Không có | **Rất Cao** | Tiền xử lý mặc định cho cả Train/Val/Test để giảm không gian nhãn |
| **2. Entity Anonymization** | Augmentation | **Trọng tâm (High ROI)** | Rất thấp | **Rất Cao** | Sinh 2–5 biến thể cho mỗi story tùy quy mô dữ liệu để xóa nhớ vẹt |
| **3. Multi-Premise Permutation** | Augmentation | **Bổ trợ (High ROI)** | Thấp | **Cao** | Chỉ áp dụng cho các story dài (từ 4 tiền đề trở lên) để tránh dư thừa |
| **4. Hard Negative Augmentation** | Augmentation | **Chuyên biệt (High ROI)**| Trung bình | **Cao** | Giới hạn ở tỷ lệ nhỏ (5–15% tập train), tập trung vào lượng từ, phủ định |
| **5. Quantified Variable Renaming** | Augmentation | Không triển khai | Thấp | **Thấp** | Làm tăng entropy nhãn mục tiêu không cần thiết |
| **6. Predicate Renaming** | Augmentation | Không triển khai | Cao | **Trung bình** | Phá vỡ tính tự nhiên của ngôn ngữ, làm giảm hiệu năng của LLM |
| **7. Logic Template Expansion** | Augmentation | Không triển khai | Cao | **Trung bình** | Dễ gây overfit vào khuôn mẫu ngôn ngữ nhân tạo |
| **8. Logical Normal Form Conversion** | Augmentation | Không triển khai | Cao | **Thấp** | Làm hỏng tính causality lập luận tự nhiên của câu dịch |
| **9. Commutative Reordering** | Augmentation | Không triển khai | Thấp | **Trung bình** | Khó sinh văn bản NL trôi chảy tương ứng bằng rule-based |
| **10. Premise Subset Augmentation** | Augmentation | Không triển khai | Trung bình | **Trung bình** | Yêu cầu sửa đổi nhãn logic phức tạp, dễ gây mâu thuẫn nhãn |

---

## 🔍 Chi Tiết Các Phương Pháp Triển Khai (High-ROI Implementation)

### A. Tiền Xử Lý Bắt Buộc (Data Normalization)

#### 1. Quantifier Variable Canonicalization (Chuẩn hóa biến lượng từ)
*   **Nguyên lý**: Định dạng lại tên của các biến lượng từ ràng buộc (bound variables) trong công thức FOL mục tiêu theo thứ tự xuất hiện chuẩn hóa (ví dụ: luôn dùng `x`, `y`, `z`... theo thứ tự từ trái qua phải).
*   **Tại sao bắt buộc**: Đây là bước chuẩn hóa cú pháp nhằm làm giảm đáng kể entropy của target vocabulary. Nó giúp hàm loss tối ưu hóa hiệu quả hơn vì loại bỏ việc phạt mô hình khi dự đoán các biến đồng dạng toán học nhưng khác ký tự.
*   **Cách triển khai**: Tích hợp trực tiếp vào pipeline tiền xử lý dữ liệu thô, tự động áp dụng trên **100% dữ liệu** (Train, Val, Test) trước khi đưa vào huấn luyện hoặc đánh giá.

### B. Các Phương Pháp Data Augmentation Trọng Tâm

#### 2. Entity Anonymization (Ẩn danh hóa thực thể)
*   **Nguyên lý**: Xác định các thực thể (tên riêng, số liệu, hằng số) trong câu NL và công thức FOL, sau đó thay thế bằng các chữ cái đại diện (`A`, `B`, `C`...) hoặc các tên ngẫu nhiên khác.
*   **Tại sao ưu tiên**: Phương pháp này cực kỳ dễ triển khai bằng rule-based/regex, không có rủi ro domain shift và giúp giải quyết triệt để hiện tượng ghi nhớ thực thể (entity memorization bias) của LLM.
*   **Cách triển khai**: Sinh từ **2 đến 5 biến thể** cho mỗi story gốc trong tập huấn luyện (tùy thuộc vào quy mô dữ liệu ban đầu).

#### 3. Multi-Premise Permutation (Hoán vị tiền đề)
*   **Nguyên lý**: Xáo trộn thứ tự xuất hiện của các tiền đề (Premises) trong cả danh sách NL và FOL song song.
*   **Tại sao ưu tiên**: Loại bỏ định kiến vị trí (positional bias) – nơi mô hình tự động giả định tiền đề thứ $i$ trong văn bản luôn tương ứng với dòng logic thứ $i$ ở đầu ra.
*   **Cách triển khai**: Để tránh tạo ra dữ liệu dư thừa cho các câu chuyện ngắn, phương pháp này **chỉ áp dụng** cho các story có số lượng tiền đề đủ lớn (ví dụ: **từ 4 tiền đề trở lên**).

#### 4. Hard Negative Augmentation (Tăng cường mẫu đối nghịch khó)
*   **Nguyên lý**: Thực hiện các thay đổi nhỏ mang tính quyết định logic trong câu NL (ví dụ: đổi "tất cả" thành "một số", thêm từ phủ định "không") và cập nhật công thức FOL tương ứng để đảo ngược kết quả suy luận logic.
*   **Tại sao ưu tiên**: Giúp mô hình dịch nhạy bén và chính xác hơn ở các từ chức năng logic (quantifiers, negation) – các lỗi dịch phổ biến nhất của LLM.
*   **Cách triển khai**: Giới hạn ở một tỷ lệ nhỏ, chỉ chiếm khoảng **5–15% tập huấn luyện** nhằm tránh làm trôi lệch phân phối dữ liệu tự nhiên. Tập trung hoàn toàn vào các lỗi logic phổ biến (lượng từ, phủ định, từ liên kết logic).

---

## 🚫 Các Phương Pháp Không Ưu Tiên Triển Khai (Low-ROI / Future Work)

Các phương pháp sau được lược bỏ hoặc chuyển xuống nhóm nghiên cứu tương lai do chi phí phát triển lớn, mang lại lợi ích thực tế thấp hoặc rủi ro domain shift cao:

*   **Quantified Variable Renaming & Predicate Renaming**: Việc đổi tên biến lượng từ ngẫu nhiên làm tăng entropy đầu ra không cần thiết. Đổi tên vị từ (ví dụ: `Likes(x, y)` -> `P(x, y)`) làm mất tính tự nhiên của ngôn ngữ, ảnh hưởng tiêu cực đến khả năng in-context understanding của LLM.
*   **Logic Template Expansion & Logical Normal Form Conversion**: Sử dụng template sinh đồ thị logic nhân tạo dễ khiến mô hình bị overfit vào cấu trúc nhân tạo của template. Chuyển đổi công thức logic về dạng CNF/NNF phá vỡ cấu trúc lập luận tự nhiên, cản trở cơ chế attention của mô hình.
*   **Commutative Reordering & Premise Subset Augmentation**: Rất khó hoán đổi các mệnh đề giao hoán trong câu NL một cách tự nhiên bằng luật. Tách tập con tiền đề yêu cầu tính toán và cập nhật lại nhãn logic phức tạp (dễ sinh nhãn sai lệch).

---

## ⚙️ Cấu Hình Tăng Cường Cố Định (Fixed Augmentation Configuration)

Để đảm bảo tính khả thi, dễ bảo trì và dễ tái lập kết quả, các thành phần điều phối ngân sách động phức tạp (như Logic Complexity Profiling, Feedback Loop tối ưu hóa ngân sách) được loại bỏ. Hệ thống sẽ sử dụng một cấu hình tăng cường cố định như sau:

| Thông số cấu hình | Giá trị thiết lập | Phạm vi áp dụng |
| :--- | :--- | :--- |
| **Quantifier Variable Canonicalization** | Áp dụng 100% | Toàn bộ Dataset (Train/Val/Test) |
| **Entity Anonymization Rate ($k_{entity}$)** | 3 biến thể / story | Tập Train |
| **Multi-Premise Permutation Rate ($k_{perm}$)** | 2 biến thể / story | Tập Train (Chỉ story có $\ge 4$ tiền đề) |
| **Hard Negative Augmentation Ratio** | 10% tổng quy mô tập Train | Tập Train (Tập trung vào lượng từ và phủ định) |

> [!NOTE]
> **Hướng nghiên cứu tương lai**: Việc tự động phân bổ ngân sách tăng cường theo độ phức tạp logic (Logic Complexity Profiling) và feedback loop động sẽ chỉ được xem xét khi tập dữ liệu gốc mở rộng quy mô lên trên 100,000 mẫu.

---

## 🛡️ Quy Trình Thực Tế Không Rò Rỉ Dữ Liệu (Practical No-Leakage Pipeline)

Để đảm bảo tập Validation và Test không bị rò rỉ dữ liệu tăng cường (data leakage), quy trình chuẩn hóa và tăng cường dữ liệu được thiết kế theo tuyến tính một chiều:

```mermaid
graph TD
    A["Dữ liệu thô (Raw Dataset)"] --> B("1. Phân chia tập dữ liệu ở mức Story (Story-level Split)")
    
    B --> C["Tập Validation / Test sạch"]
    B --> D["Tập Huấn Luyện Gốc (Original Train Set)"]
    
    subgraph Tiền Xử Lý (Normalization)
        C --> E["Chuẩn hóa biến lượng từ (Quantifier Canonicalization)"]
        D --> F["Chuẩn hóa biến lượng từ (Quantifier Canonicalization)"]
    end
    
    subgraph Tăng Cường Dữ Liệu Tập Huấn Luyện (Data Augmentation)
        F --> G["Ẩn danh hóa thực thể (Entity Anonymization) <br> [2-5 biến thể/story]"]
        G --> H["Hoán vị tiền đề (Multi-Premise Permutation) <br> [Chỉ áp dụng với story có >= 4 tiền đề]"]
        H --> I["Tăng cường mẫu đối nghịch khó (Hard Negatives) <br> [Tỷ lệ nhỏ 5-15%]"]
    end
    
    E --> J["Tập Validation/Test cuối cùng (Sạch & Chuẩn hóa)"]
    I --> K["Tập Huấn Luyện Tăng Cường Cuối Cùng (Final Augmented Train Set)"]
    
    style J fill:#d4edda,stroke:#28a745,stroke-width:2px
    style K fill:#d1ecf1,stroke:#17a2b8,stroke-width:2px
```

*   **Đặc điểm nổi bật**:
    1. **Tách biệt trước, tăng cường sau**: Việc phân chia Train/Val/Test ở mức Story-level được thực hiện đầu tiên. Tuyệt đối không áp dụng bất kỳ phương pháp Augmentation nào trên tập Validation và Test.
    2. **Chuẩn hóa đồng bộ**: Cả tập Train và tập Val/Test đều được đi qua bước *Quantifier Variable Canonicalization* để đảm bảo mô hình học và đánh giá trên cùng một dạng chuẩn logic.
    3. **Pipeline tuyến tính, đơn giản**: Các phương pháp tăng cường được áp dụng tuần tự theo cấu hình cố định, giúp dễ kiểm soát chất lượng dữ liệu và giảm tối đa chi phí lập trình hệ thống.
