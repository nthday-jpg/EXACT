# Kế Hoạch Triển Khai Thực Tế: Data Augmentation & Normalization Cho Dịch NL -> FOL

Tài liệu này trình bày quy trình xử lý dữ liệu tinh giản, tập trung vào tính khả thi, tối ưu hóa công sức phát triển (ROI cao) và hạn chế tối đa rủi ro lệch phân phối (domain shift) cho bộ dữ liệu dịch Ngôn ngữ tự nhiên sang Logic mệnh đề bậc một (NL -> FOL) quy mô nhỏ đến trung bình.

---

## 📌 Phân Biệt Các Khái Niệm Cốt Lõi (Conceptual Separation)

Để tối ưu hóa pipeline huấn luyện và tránh nhầm lẫn trong thiết kế hệ thống, các bước xử lý dữ liệu được chia làm 3 phạm trù độc lập:

1. **Data Normalization (Chuẩn hóa dữ liệu)**: Định dạng lại dữ liệu hiện có về dạng chuẩn hóa (canonical representation) để thu hẹp không gian nhãn mục tiêu (target label space), làm giảm entropy phân phối đầu ra của mô hình dịch. Quá trình này **không** sinh thêm dữ liệu mới và áp dụng cho 100% mẫu dữ liệu (bao gồm cả tập train, validation và test).
2. **Data Augmentation (Tăng cường dữ liệu)**: Quá trình tạo ra các mẫu dữ liệu huấn luyện mới từ dữ liệu gốc nhằm gia tăng quy mô và độ đa dạng cho tập huấn luyện. Chỉ áp dụng trên tập huấn luyện (Train Set) sau khi đã phân tách.
3. **Curriculum Learning (Học theo chương trình)**: Chiến lược lên lịch trình (scheduling) thứ tự xuất hiện của các mẫu huấn luyện trong quá trình tối ưu hóa mô hình (ví dụ: huấn luyện từ mẫu ngắn đến mẫu dài). Đây là chiến lược huấn luyện, không phải là bước sinh dữ liệu.

---

## ⚠️ Dataset-Specific Risks and Imbalances (Rủi ro và Mất cân bằng Đặc thù của Dataset)

Phân tích số liệu thực tế từ dataset cho thấy các điểm mất cân bằng cấu trúc quan trọng sau:
*   **Số lượng lượng từ**: Số lượng lượng từ toàn thể (`ForAll` = 5023) vượt trội hoàn toàn so với lượng từ tồn tại (`Exists` = 952), với tỷ lệ `ForAll/Exists` ≈ 5.3.
*   **Độ sâu lồng nhau**: Các cấu trúc lồng lượng từ phức tạp (`Quantifier nesting >= 2`) chỉ chiếm khoảng 9.88% toàn bộ dataset.
*   **Phân bố logic pattern**:
    *   Pattern `ForAll` chiếm đa số với 63.95%.
    *   Pattern `Exists` chỉ chiếm 9.57%.
    *   Pattern lồng nhau `ForAll Exists` chỉ chiếm 1.48%.
    *   Pattern lồng nhau `Exists ForAll` chỉ chiếm 0.97%.

Đây là một mất cân bằng cấu trúc quan trọng của dataset. Sự mất cân bằng này đặt ra rủi ro lớn là mô hình dễ bị thiên lệch (bias) thiên về lượng từ toàn thể `ForAll` và các cấu trúc đơn giản, dẫn đến khả năng suy luận và dịch các cấu trúc lồng nhau phức tạp hoặc lượng từ tồn tại bị suy giảm nghiêm trọng.

---

## 📊 Bảng Đánh Giá & Phân Loại Các Phương Pháp (ROI-Focused Evaluation)

| Phương pháp | Phân loại | Mức độ ưu tiên | Rủi ro Domain Shift | Hiệu quả thực tế | Ghi chú triển khai |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Quantifier Variable Canonicalization** | Normalization | **Bắt buộc (100%)** | Không đáng kể | **Rất Cao** | Tiền xử lý mặc định cho cả Train/Val/Test để giảm không gian nhãn |
| **2. Entity Anonymization** | Augmentation | **Trọng tâm (High ROI)** | Rất thấp | **Rất Cao** | Sinh biến thể ngẫu nhiên để xóa nhớ vẹt, domain shift thấp nhưng không bằng 0 |
| **3. Multi-Premise Permutation** | Augmentation | **Bổ trợ (High ROI)** | Thấp | **Cao** | Chỉ áp dụng cho các story dài (từ 4 tiền đề trở lên) để tránh dư thừa |
| **4. Hard Negative Augmentation** | Augmentation | **Chuyên biệt (High ROI)**| Trung bình | **Cao** | Giới hạn ở tỷ lệ 10–20% tập train, tập trung giải quyết mất cân bằng lượng từ/phủ định |
| **5. Quantified Variable Renaming** | Augmentation | Ít ưu tiên hiện tại | Thấp | **Hạn chế** | Có thể làm tăng entropy nhãn mục tiêu không cần thiết |
| **6. Predicate Renaming** | Augmentation | Ít ưu tiên hiện tại | Trung bình | **Hạn chế** | Có nguy cơ làm giảm tính tự nhiên của ngôn ngữ đối với LLM |
| **7. Logic Template Expansion** | Augmentation | Ít ưu tiên hiện tại | Trung bình | **Có điều kiện** | Có thể hữu ích để tăng coverage cho cấu trúc logic hiếm |
| **8. Logical Normal Form Conversion** | Augmentation | Ít ưu tiên hiện tại | Trung bình | **Hạn chế** | Có thể làm hỏng tính causality lập luận tự nhiên của câu dịch |
| **9. Commutative Reordering** | Augmentation | Ít ưu tiên hiện tại | Thấp | **Trung bình** | Khó sinh văn bản NL trôi chảy tương ứng bằng rule-based |
| **10. Premise Subset Augmentation** | Augmentation | Ít ưu tiên hiện tại | Trung bình | **Trung bình** | Yêu cầu sửa đổi nhãn logic phức tạp, dễ gây mâu thuẫn nhãn |

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
*   **Tại sao ưu tiên**: Phương pháp này cực kỳ dễ triển khai bằng rule-based/regex, giúp giải quyết hiệu quả hiện tượng ghi nhớ thực thể (entity memorization bias) của LLM.
*   **Đánh giá Domain Shift**: Domain shift thấp nhưng không bằng 0, do các thực thể tự nhiên bị thay thế bởi các placeholder tổng quát.
*   **Cách triển khai**: Sinh biến thể cho tập huấn luyện theo ngân sách dữ liệu được khuyến nghị.

#### 3. Multi-Premise Permutation (Hoán vị tiền đề)
*   **Nguyên lý**: Xáo trộn thứ tự xuất hiện của các tiền đề (Premises) trong cả danh sách NL và FOL song song.
*   **Tại sao ưu tiên**: Giảm thiểu định kiến vị trí (positional bias) – nơi mô hình tự động giả định tiền đề thứ $i$ trong văn bản luôn tương ứng với dòng logic thứ $i$ ở đầu ra.
*   **Cách triển khai**: Để tránh tạo ra dữ liệu dư thừa cho các câu chuyện ngắn, phương pháp này **chỉ áp dụng** cho các story có số lượng tiền đề đủ lớn (ví dụ: **từ 4 tiền đề trở lên**).

#### 4. Hard Negative Augmentation (Tăng cường mẫu đối nghịch khó)
*   **Nguyên lý**: Thực hiện các thay đổi nhỏ mang tính quyết định logic trong câu NL (ví dụ: đổi "tất cả" thành "một số", thêm từ phủ định "không") và cập nhật công thức FOL tương ứng để đảo ngược kết quả suy luận logic.
*   **Tại sao ưu tiên (ROI)**: Hiệu quả thực tế của Hard Negative đến từ việc trực tiếp giải quyết sự mất cân bằng giữa Universal và Existential quantifiers (`ForAll` = 5023 so với `Exists` = 952), kết hợp với tần suất phủ định rất cao (`NOT` = 2662) trong dataset. Điều này giúp mô hình dịch nhạy bén và chính xác hơn ở các từ chức năng logic quan trọng.
*   **Khuyến nghị triển khai**:
    *   **Ưu tiên cao**:
        *   Biến đổi lượng từ: `Every` ↔ `Some`, `All` ↔ `Exists`.
        *   Biến đổi vị từ phủ định: `Positive` ↔ `Negated predicates`.
    *   **Không ưu tiên (Ít ưu tiên hiện tại)**:
        *   Biến đổi tương đương điều kiện hai chiều (`Biconditional transformations`).
        *   Phủ định cấp lượng từ (`Quantifier-level negation`).
        *   Các toán tử logic hiếm gặp (`Rare logical operators`), vì các hiện tượng này xuất hiện rất ít trong dataset hiện tại.
*   **Cách triển khai**: Giới hạn ở khoảng **10–20% tập huấn luyện** nhằm kiểm soát phân phối dữ liệu tự nhiên.

---

## 🚫 Các Phương Pháp Ít Ưu Tiên Hơn Trong Giai Đoạn Hiện Tại

Các phương pháp sau ít được ưu tiên triển khai trong giai đoạn hiện tại do chi phí phát triển lớn so với hiệu quả mang lại cho quy mô dữ liệu hiện có, hoặc có rủi ro nhất định đối với phân phối dữ liệu gốc:

*   **Quantified Variable Renaming & Predicate Renaming**: Việc đổi tên biến lượng từ ngẫu nhiên có thể làm tăng entropy đầu ra không cần thiết. Đổi tên vị từ (ví dụ: `Likes(x, y)` -> `P(x, y)`) có nguy cơ làm giảm tính tự nhiên của ngôn ngữ và ảnh hưởng tiêu cực đến hiệu năng in-context understanding của LLM.
*   **Logic Template Expansion**: Dataset hiện có 742 stories và gần như toàn bộ cấu trúc logic trong tập `logic_based` là độc nhất sau khi chuẩn hóa predicate. Do đó Template Expansion không phải ưu tiên ở giai đoạn hiện tại. Tuy nhiên phương pháp này vẫn có thể hữu ích nếu mục tiêu là tăng coverage cho các hiện tượng hiếm như nested quantifiers hoặc reasoning chains sâu.
*   **Logical Normal Form Conversion**: Chuyển đổi công thức logic về dạng CNF/NNF có rủi ro làm hỏng tính causality lập luận tự nhiên của câu dịch, cản trở cơ chế attention của mô hình.
*   **Commutative Reordering & Premise Subset Augmentation**: Khó hoán đổi các mệnh đề giao hoán trong câu NL một cách tự nhiên bằng luật. Tách tập con tiền đề yêu cầu tính toán và cập nhật lại nhãn logic phức tạp, dễ dẫn đến mâu thuẫn nhãn logic nếu không được kiểm soát chặt chẽ.

---

## 💰 Recommended Augmentation Budget (Ngân Sách Tăng Cường Khuyến Nghị)

Dataset hiện tại có độ đa dạng story tương đối cao (**742 stories trên tổng số 1812 samples**), vì vậy không nên thực hiện mở rộng dữ liệu quá mức nhằm tránh làm loãng phân phối gốc hoặc làm mất tính cân bằng tự nhiên. Mục tiêu hợp lý là đưa dataset cuối cùng lên khoảng **1.5x–2.0x** kích thước ban đầu, thay vì mở rộng quá lớn từ 3x–10x.

Ngân sách tăng cường cụ thể được phân bổ như sau:
*   **Quantifier Canonicalization**: Áp dụng cho **toàn bộ dataset (100% samples)** bao gồm cả tập Train, Validation và Test.
*   **Entity Anonymization**: Áp dụng cho khoảng **50% số lượng train samples**.
*   **Hard Negative**: Áp dụng cho khoảng **10–20% số lượng train samples**.
*   **Multi-Premise Permutation**: Tạo **1 permutation/story** và chỉ áp dụng cho các story có **từ 4 premises trở lên**.

---

## ⚙️ Cấu Hình Tăng Cường Thực Tế (Fixed Augmentation Configuration)

Để đảm bảo tính khả thi, dễ bảo trì và dễ tái lập kết quả, các thành phần điều phối ngân sách động phức tạp được loại bỏ. Hệ thống sử dụng một cấu hình tăng cường cố định nhằm bám sát ngân sách khuyến nghị như sau:

| Thông số cấu hình | Giá trị thiết lập | Phạm vi áp dụng |
| :--- | :--- | :--- |
| **Quantifier Variable Canonicalization** | Áp dụng 100% | Toàn bộ Dataset (Train/Val/Test) |
| **Entity Anonymization Ratio** | Áp dụng cho ~50% Train samples | Tập Train |
| **Multi-Premise Permutation Rate** | 1 permutation / story | Tập Train (Chỉ áp dụng với story có $\ge 4$ tiền đề) |
| **Hard Negative Augmentation Ratio** | 10% – 20% tổng quy mô tập Train | Tập Train (Tập trung vào Every ↔ Some, All ↔ Exists và phủ định vị từ) |

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
        F --> G["Ẩn danh hóa thực thể (Entity Anonymization) <br> [~50% train samples]"]
        G --> H["Hoán vị tiền đề (Multi-Premise Permutation) <br> [1 permutation/story cho story có >= 4 tiền đề]"]
        H --> I["Tăng cường mẫu đối nghịch khó (Hard Negatives) <br> [Tỷ lệ 10-20%]"]
    end
    
    E --> J["Tập Validation/Test cuối cùng (Sạch & Chuẩn hóa)"]
    I --> K["Tập Huấn Luyện Tăng Cường Cuối Cùng (Final Augmented Train Set)"]
    
    style J fill:#d4edda,stroke:#28a745,stroke-width:2px
    style K fill:#d1ecf1,stroke:#17a2b8,stroke-width:2px
```

*   **Đặc điểm nổi bật**:
    1. **Tách biệt trước, tăng cường sau**: Việc phân chia Train/Val/Test ở mức Story-level được thực hiện đầu tiên. Không áp dụng các phương pháp Augmentation trên tập Validation và Test để đảm bảo đánh giá khách quan.
    2. **Chuẩn hóa đồng bộ**: Cả tập Train và tập Val/Test đều được đi qua bước *Quantifier Variable Canonicalization* để đảm bảo mô hình học và đánh giá trên cùng một dạng chuẩn logic.
    3. **Pipeline tuyến tính, đơn giản**: Các phương pháp tăng cường được áp dụng tuần tự theo cấu hình cố định, giúp dễ kiểm soát chất lượng dữ liệu và giảm tối đa chi phí lập trình hệ thống.

---

## 📝 Kết Luận (Conclusion)

Dựa trên các phân tích đặc thù cấu trúc và thống kê của dataset hiện tại:
1.  **Các phương pháp có ROI cao nhất**: **Quantifier Canonicalization**, **Entity Anonymization**, **Hard Negative Augmentation**, và **Multi-Premise Permutation** là các phương pháp mang lại tỷ suất hiệu quả trên chi phí đầu tư (ROI) cao nhất cho dataset hiện tại.
2.  **Khoảng trống cấu trúc lớn nhất**: Độ phủ lượng từ lồng nhau (**Nested quantifier coverage**) với tỷ lệ cấu trúc lồng phức tạp $\ge 2$ rất hạn chế (chỉ khoảng 9.88%) mới chính là khoảng trống cấu trúc đáng chú ý nhất của dataset.
3.  **Định hướng chiến lược**: Các quyết định data augmentation trong tương lai nên ưu tiên tập trung vào việc gia tăng độ phủ (coverage) của các hiện tượng logic hiếm gặp (như nested quantifiers, deep reasoning chains) thay vì chỉ đơn thuần tăng quy mô số lượng mẫu huấn luyện một cách đại trà.
