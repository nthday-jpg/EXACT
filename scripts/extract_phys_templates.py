import re
import json
from pathlib import Path
from typing import Dict, Any, List

# Import từ các module hệ thống của bạn
from src.physics.types import PhysicsTask
from src.utils.physics_tasks import load_physics_tasks
from src.physics.preprocessing import preprocess
from src.physics.postprocessing import postprocess_answer

def pipeline_extract_templates(input_path: str, output_dir: str = "runs") -> None:
    """
    Tải bài toán, chuẩn hóa câu hỏi thành template và trích xuất thông tin model.
    """
    # 1. Tải dữ liệu
    # load_physics_tasks sẽ đưa 'correct_answer' vào task.correct 
    # và các trường còn lại vào task.metadata
    tasks: List[PhysicsTask] = load_physics_tasks(input_path)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    unique_templates: Dict[str, Dict[str, Any]] = {}

    # --- REGEX CHUẨN HÓA CÂU HỎI ---
    sci_num = r'\d+(?:\.\d+)?[eE][+-]?\d+'
    normal_num = r'\d+(?:\.\d+)?'
    base_num_pattern = f"(?:{sci_num}|{normal_num})"
    full_pattern = fr"{base_num_pattern}\s*(?:[VNFJWC]|\u03a9|\u00b0|Hz|F|A|[kMGTdcmμnp]?[a-zA-Z]+)?"

    print(f"🔄 Đang xử lý {len(tasks)} câu hỏi...")

    for task in tasks:
        meta = task.metadata or {}

        # 2. Xử lý Ground Truth (correct_answer)
        # Vì preprocess cần string, ta xử lý từng phần của dict
        if task.correct and isinstance(task.correct, dict):
            for key in ["ans", "unit"]:
                val = task.correct.get(key)
                if isinstance(val, str):
                    task.correct[key] = preprocess(val)

        # 3. Xử lý model_answer (Dữ liệu từ file của bạn là list)
        model_answer = meta.get("model_answer")

        # 4. Xử lý model_output (Chuỗi JSON thô chứa thought/physics_analysis)
        model_output = meta.get("model_output")

        # 5. Tạo Skeleton cho câu hỏi
        normalized_q = re.sub(full_pattern, ' [VAR] ', task.question)
        normalized_q = " ".join(normalized_q.split())
        
        # 6. Lọc trùng cấu trúc
        if normalized_q not in unique_templates:
            unique_templates[normalized_q] = {
                "template_skeleton": normalized_q,
                "original_task": {
                    "question": task.question,
                    "correct_answer": task.correct,
                    "model_answer": model_answer,
                    "model_output": model_output,
                    "domains": meta.get("domains", []),
                    "is_correct": meta.get("is_correct")
                }
            }
            
    template_list = list(unique_templates.values())
    
    # 7. Lưu file
    output_file = output_path / "processed_templates.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(template_list, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Hoàn tất!")
    print(f"📊 Tổng số bản ghi: {len(tasks)}")
    print(f"🎯 Số dạng bài độc nhất: {len(template_list)}")
    print(f"💾 Kết quả tại: {output_file}")

if __name__ == "__main__":
    # File đầu vào theo cấu trúc bạn đã gửi
    INPUT_FILE = "runs/physics_distillation_correct.json" 
    pipeline_extract_templates(INPUT_FILE)