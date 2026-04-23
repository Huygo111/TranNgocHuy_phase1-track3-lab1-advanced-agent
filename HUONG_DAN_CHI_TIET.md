# Hướng Dẫn Chi Tiết: Hoàn Thành Reflexion Agent Lab

## 📋 Mục Lục
1. [Chuẩn bị Môi Trường](#1-chuẩn-bị-môi-trường)
2. [Hiểu Cấu Trúc Dự Án](#2-hiểu-cấu-trúc-dự-án)
3. [Thay Thế Mock Runtime](#3-thay-thế-mock-runtime-với-llm-thật)
4. [Chạy Benchmark Thực Tế](#4-chạy-benchmark-thực-tế)
5. [Tính Token Tiêu Thụ](#5-tính-toán-token-tiêu-thụ-thực-tế)
6. [Định Dạng báo Cáo](#6-định-dạng-báo-cáo)
7. [Bonus Features](#7-bonus-features)
8. [Kiểm Tra & Chấm Điểm](#8-kiểm-tra--chấm-điểm)

---

## 1. Chuẩn Bị Môi Trường

### Bước 1.1: Tạo Virtual Environment

```bash
# Tạo venv
python -m venv .venv

# Kích hoạt venv (Windows)
.venv\Scripts\activate

# Kích hoạt venv (macOS/Linux)
source .venv/bin/activate
```

### Bước 1.2: Cài Đặt Dependencies

```bash
# Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# Nếu chưa có requirements.txt, cài các gói chính:
pip install anthropic openai requests python-dotenv
```

### Bước 1.3: Kiểm Tra Cấu Trúc Thư Mục

```
project/
├── src/
│   └── reflexion_lab/
│       ├── __init__.py
│       ├── schemas.py          # Định nghĩa kiểu dữ liệu
│       ├── prompts.py          # Template prompts
│       ├── mock_runtime.py     # ❌ Cần thay thế
│       ├── agents.py           # Cấu trúc agent chính
│       └── reporting.py        # Xuất báo cáo
├── data/
│   └── hotpot_mini.json        # Dataset mẫu
├── outputs/                    # Thư mục kết quả
├── run_benchmark.py            # Script chính
├── autograde.py                # Công cụ chấm điểm
└── requirements.txt            # Dependencies
```

---

## 2. Hiểu Cấu Trúc Dự Án

### Bước 2.1: Đọc File Schemas

Mở `src/reflexion_lab/schemas.py` để hiểu các kiểu dữ liệu:

```python
# Trace: lưu từng bước tư duy của agent
class Trace:
    thought: str
    action: str
    observation: str

# Record: lưu kết quả cho 1 câu hỏi
class Record:
    question: str
    traces: List[Trace]
    final_answer: str
    is_correct: bool
    token_count: int
```

**Việc cần làm**: Hiểu rõ cấu trúc này vì report phải xuất dữ liệu theo định dạng này.

### Bước 2.2: Đọc File Prompts

Mở `src/reflexion_lab/prompts.py` để xem các template:

```python
ACTOR_PROMPT = """Bạn là một agent chuyên trả lời câu hỏi..."""
EVALUATOR_PROMPT = """Đánh giá câu trả lời có đúng không..."""
REFLECTOR_PROMPT = """Phân tích lỗi và đề xuất cách sửa..."""
```

**Việc cần làm**: Không cần sửa, chỉ cần hiểu flow của 3 component: Actor → Evaluator → Reflector.

### Bước 2.3: Đọc Mock Runtime

Mở `src/reflexion_lab/mock_runtime.py` để thấy cái mà cần thay thế:

```python
def mock_actor_call(prompt: str):
    # Giả lập: trả về chuỗi cố định
    return "Thought: ...\nAction: ..."

def mock_evaluator_call(prompt: str):
    # Giả lập: luôn trả về True
    return True
```

**Việc cần làm**: Thay thế bằng gọi thực LLM API.

---

## 3. Thay Thế Mock Runtime Với LLM Thật

### Bước 3.1: Lựa Chọn LLM Provider

Chọn 1 trong các tùy chọn:

#### ✅ **Option A: Claude API (Anthropic)** - Khuyên dùng
- Chất lượng tốt nhất
- Token counting hỗ trợ tốt
- Yêu cầu API key

```bash
pip install anthropic
```

#### ✅ **Option B: OpenAI API**
- Có free tier
- Dễ sử dụng
- Yêu cầu API key

```bash
pip install openai
```

#### ✅ **Option C: Ollama (Local)**
- Miễn phí, không cần API
- Chạy trên máy tính
- Cần cài Ollama trước

```bash
# Cài Ollama từ https://ollama.ai
# Chạy: ollama run mistral (hoặc model khác)
pip install requests
```

### Bước 3.2: Tạo File Config cho API Key

Tạo file `.env` trong thư mục gốc:

```env
# Nếu dùng Claude
ANTHROPIC_API_KEY=your_key_here

# Nếu dùng OpenAI
OPENAI_API_KEY=your_key_here

# Nếu dùng Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

### Bước 3.3: Thay Thế Mock Runtime

**Xóa hoặc comment nội dung trong `src/reflexion_lab/mock_runtime.py`**, rồi thêm code thực:

#### Nếu dùng Claude:

```python
import anthropic
import os
import json

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def call_actor(prompt: str) -> tuple[str, int]:
    """
    Gọi Actor để tạo thought/action.
    
    Return: (response_text, token_used)
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",  # Hoặc model khác
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = response.content[0].text
    token_used = response.usage.output_tokens
    
    return response_text, token_used


def call_evaluator(prompt: str) -> tuple[bool, int]:
    """
    Gọi Evaluator để kiểm tra câu trả lời.
    
    Return: (is_correct, token_used)
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = response.content[0].text.lower()
    token_used = response.usage.output_tokens
    
    # Kiểm tra xem có chứa "yes" hay "correct"
    is_correct = "yes" in response_text or "correct" in response_text
    
    return is_correct, token_used


def call_reflector(prompt: str) -> tuple[str, int]:
    """
    Gọi Reflector để phản chiếu lỗi.
    
    Return: (reflection_text, token_used)
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    reflection_text = response.content[0].text
    token_used = response.usage.output_tokens
    
    return reflection_text, token_used
```

#### Nếu dùng OpenAI:

```python
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_actor(prompt: str) -> tuple[str, int]:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Hoặc model khác
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = response.choices[0].message.content
    token_used = response.usage.completion_tokens
    
    return response_text, token_used

# Tương tự cho evaluator và reflector...
```

#### Nếu dùng Ollama (Local):

```python
import requests
import os
import json

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

def call_actor(prompt: str) -> tuple[str, int]:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    
    data = response.json()
    response_text = data.get("response", "")
    
    # Ollama không cung cấp token count, ước tính bằng độ dài
    token_used = len(response_text.split()) // 4  # Ước tính
    
    return response_text, token_used

# Tương tự cho evaluator và reflector...
```

### Bước 3.4: Cập Nhật File Agents

Mở `src/reflexion_lab/agents.py` và tìm chỗ gọi mock_runtime:

```python
# ❌ Cũ
from .mock_runtime import mock_actor_call

# ✅ Mới
from .mock_runtime import call_actor
```

Sau đó cập nhật phần gọi hàm để nhận token count:

```python
# Trong ReflexionAgent class
response_text, token_used = call_actor(prompt)
self.total_tokens += token_used  # Lưu lại token

# Tương tự cho evaluator và reflector
```

---

## 4. Chạy Benchmark Thực Tế

### Bước 4.1: Chuẩn Bị Dataset

Dataset sử dụng là **HotpotQA** - câu hỏi cần kiến thức từ nhiều đoạn văn:

```json
{
  "questions": [
    {
      "id": "1",
      "question": "What is the elevation of the peak that is in the state of Colorado and whose name begins with \"San\"?",
      "answer": "14130",
      "supporting_facts": [...]
    }
  ]
}
```

**Việc cần làm**:
- Tải dataset từ `data/hotpot_mini.json` (nếu có)
- Hoặc tải từ: https://hotpotqa.github.io/

### Bước 4.2: Chạy Benchmark với 100+ Mẫu

```bash
# Kích hoạt venv trước
source .venv/bin/activate  # hoặc .venv\Scripts\activate trên Windows

# Chạy benchmark
python run_benchmark.py \
    --dataset data/hotpot_full.json \
    --out-dir outputs/my_run \
    --num-samples 100 \
    --max-attempts 3
```

**Giải thích tham số**:
- `--dataset`: đường dẫn file dữ liệu
- `--out-dir`: thư mục lưu kết quả
- `--num-samples`: số lượng câu hỏi chạy (tối thiểu 100)
- `--max-attempts`: số lần phản chiếu tối đa cho 1 câu hỏi

### Bước 4.3: Kiểm Tra Quá Trình Chạy

Trong quá trình chạy, bạn sẽ thấy output như:

```
Processing question 1/100: "What is..."
├─ Attempt 1: thought=..., action=...
├─ Evaluation: INCORRECT
├─ Reflection: "Need to search for..."
├─ Attempt 2: thought=..., action=...
├─ Evaluation: CORRECT ✓
│  Tokens used: 3500
└─ Time: 12.5s

[Progress] ████████░░ 50/100 (50%)
```

**Nếu lỗi**:
- Kiểm tra API key trong `.env`
- Kiểm tra kết nối mạng
- Xem thông báo lỗi chi tiết trong terminal

---

## 5. Tính Toán Token Tiêu Thụ Thực Tế

### Bước 5.1: Lấy Token Count Từ API

Mỗi API provider cung cấp token count khác nhau:

#### Claude:
```python
response = client.messages.create(...)
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
total = input_tokens + output_tokens
```

#### OpenAI:
```python
response = client.chat.completions.create(...)
prompt_tokens = response.usage.prompt_tokens
completion_tokens = response.usage.completion_tokens
total = prompt_tokens + completion_tokens
```

#### Ollama:
```python
# Ollama không cung cấp token count chính xác
# Phải ước tính: 1 token ≈ 0.75 từ (hoặc 4 ký tự)
word_count = len(response.split())
token_estimate = int(word_count / 0.75)
```

### Bước 5.2: Ghi Lại Token Cho Mỗi Câu Hỏi

Trong `src/reflexion_lab/agents.py`, cập nhật `Record`:

```python
@dataclass
class Record:
    question: str
    traces: List[Trace]  # Danh sách attempt
    final_answer: str
    is_correct: bool
    token_count: int      # ⭐ Ghi lại tổng token
    attempts: int        # Số lần phản chiếu
    time_taken: float    # Thời gian (giây)
```

### Bước 5.3: Tích Lũy Token Toàn Bộ

```python
class ReflexionAgent:
    def __init__(self):
        self.total_tokens = 0
        self.records = []
    
    def solve(self, question: str) -> Record:
        record_tokens = 0
        
        for attempt in range(self.max_attempts):
            # Gọi Actor
            response, tokens = call_actor(prompt)
            record_tokens += tokens
            
            # Gọi Evaluator
            is_correct, tokens = call_evaluator(response)
            record_tokens += tokens
            
            if is_correct:
                break
            
            # Gọi Reflector
            reflection, tokens = call_reflector(...)
            record_tokens += tokens
        
        # Lưu token cho record này
        record = Record(
            question=question,
            token_count=record_tokens,
            ...
        )
        
        self.total_tokens += record_tokens
        return record
```

---

## 6. Định Dạng báo Cáo

### Bước 6.1: Tạo report.json

File này phải có format như sau:

```json
{
  "metadata": {
    "dataset": "HotpotQA",
    "num_samples": 100,
    "model": "claude-3-5-sonnet-20241022",
    "timestamp": "2024-04-23T10:30:00Z",
    "total_tokens": 45000
  },
  "results": [
    {
      "question_id": "1",
      "question": "What is the elevation...",
      "predicted_answer": "14130",
      "ground_truth": "14130",
      "is_correct": true,
      "attempts": 2,
      "token_count": 2500,
      "time_taken": 15.3,
      "traces": [
        {
          "attempt": 1,
          "thought": "I need to search...",
          "action": "search(San peak Colorado)",
          "observation": "Found: San Juan Mountains..."
        }
      ]
    }
  ],
  "statistics": {
    "accuracy": 0.72,
    "avg_attempts": 1.5,
    "avg_tokens_per_question": 450,
    "total_time": 1234.5
  }
}
```

### Bước 6.2: Tạo report.md

File này là báo cáo dạng text:

```markdown
# Reflexion Agent Benchmark Report

## Metadata
- **Dataset**: HotpotQA
- **Model**: Claude 3.5 Sonnet
- **Samples**: 100
- **Date**: 2024-04-23

## Results Summary
| Metric | Value |
|--------|-------|
| Accuracy | 72% |
| Avg Attempts | 1.5 |
| Total Tokens | 45,000 |
| Avg Time/Q | 12.3s |

## Sample Results
- Q1: "What is the elevation..." → ✓ CORRECT (2 attempts, 2500 tokens)
- Q2: "Who was born in..." → ✗ INCORRECT (3 attempts, 3000 tokens)

## Analysis
...
```

### Bước 6.3: Cập Nhật reporting.py

Mở `src/reflexion_lab/reporting.py` và viết hàm xuất báo cáo:

```python
import json
from datetime import datetime
from pathlib import Path
from typing import List
from .schemas import Record

def generate_report(records: List[Record], output_dir: str, model_name: str):
    """Xuất báo cáo JSON và Markdown"""
    
    # Tính toán thống kê
    correct = sum(1 for r in records if r.is_correct)
    accuracy = correct / len(records) if records else 0
    avg_attempts = sum(r.attempts for r in records) / len(records) if records else 0
    total_tokens = sum(r.token_count for r in records)
    avg_tokens = total_tokens / len(records) if records else 0
    
    # Tạo JSON
    report_json = {
        "metadata": {
            "dataset": "HotpotQA",
            "num_samples": len(records),
            "model": model_name,
            "timestamp": datetime.now().isoformat(),
            "total_tokens": total_tokens
        },
        "results": [
            {
                "question_id": str(i),
                "question": r.question,
                "predicted_answer": r.final_answer,
                "is_correct": r.is_correct,
                "attempts": r.attempts,
                "token_count": r.token_count,
                "time_taken": r.time_taken,
                "traces": [...]  # Từ record.traces
            }
            for i, r in enumerate(records)
        ],
        "statistics": {
            "accuracy": accuracy,
            "avg_attempts": avg_attempts,
            "avg_tokens_per_question": avg_tokens,
            "total_tokens": total_tokens
        }
    }
    
    # Lưu JSON
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    with open(output_path / "report.json", "w") as f:
        json.dump(report_json, f, indent=2)
    
    # Tạo Markdown
    md_content = f"""# Reflexion Agent Benchmark Report

## Metadata
- **Dataset**: HotpotQA
- **Model**: {model_name}
- **Samples**: {len(records)}
- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Results Summary
| Metric | Value |
|--------|-------|
| Accuracy | {accuracy:.1%} |
| Avg Attempts | {avg_attempts:.2f} |
| Total Tokens | {total_tokens:,} |
| Avg Tokens/Q | {avg_tokens:.0f} |

## Sample Results
"""
    
    # Thêm 10 mẫu đầu tiên
    for i, r in enumerate(records[:10]):
        status = "✓" if r.is_correct else "✗"
        md_content += f"- Q{i+1}: {r.question[:50]}... → {status}\n"
    
    with open(output_path / "report.md", "w") as f:
        f.write(md_content)
    
    print(f"✓ Report saved to {output_dir}")
```

---

## 7. Bonus Features

Để được 20% điểm bonus, thực hiện ít nhất **1** trong các tính năng sau:

### 7.1 Structured Evaluator

Thay vì evaluator trả về True/False, trả về chi tiết:

```python
@dataclass
class EvaluationResult:
    is_correct: bool
    confidence: float      # 0.0 - 1.0
    reasoning: str        # Giải thích tại sao
    suggested_action: str # Đề xuất bước tiếp theo
```

### 7.2 Reflection Memory

Lưu lại tất cả reflection trước đó để tránh lặp lại sai lầm:

```python
class ReflexionAgent:
    def __init__(self):
        self.reflection_history = []  # Lưu reflection cũ
    
    def solve(self, question: str):
        for attempt in range(max_attempts):
            # Truyền lịch sử reflection vào prompt
            prompt = f"{base_prompt}\n\n" + \
                     "Previous failed attempts:\n" + \
                     "\n".join(self.reflection_history)
```

### 7.3 Adaptive Max Attempts

Tự động điều chỉnh số lần phản chiếu dựa trên độ khó:

```python
def get_adaptive_max_attempts(question: str) -> int:
    """Các câu khó hơn được phép thử nhiều lần hơn"""
    
    question_len = len(question.split())
    
    if question_len < 15:
        return 2  # Câu đơn giản
    elif question_len < 30:
        return 3  # Câu trung bình
    else:
        return 5  # Câu phức tạp
```

### 7.4 Memory Compression

Nén dài danh sách trace để tiết kiệm token:

```python
def compress_traces(traces: List[Trace]) -> str:
    """Gộp các trace thành summary ngắn"""
    
    summary = "Previous attempts:\n"
    for i, trace in enumerate(traces):
        summary += f"{i+1}. Thought: {trace.thought[:50]}...\n"
    
    return summary
```

### 7.5 Dynamic Prompt Templates

Sử dụng prompt khác nhau dựa trên độ khó câu hỏi:

```python
def get_actor_prompt(question: str, difficulty: str) -> str:
    if difficulty == "easy":
        return SIMPLE_ACTOR_PROMPT
    elif difficulty == "medium":
        return STANDARD_ACTOR_PROMPT
    else:
        return COMPLEX_ACTOR_PROMPT
```

---

## 8. Kiểm Tra & Chấm Điểm

### Bước 8.1: Chạy Autograde

```bash
python autograde.py --report-path outputs/my_run/report.json
```

Output sẽ hiển thị:

```
=== AUTOGRADE RESULTS ===
Core (80 points):
  ✓ Correct flow structure: 20/20
  ✓ Real LLM integration: 20/20
  ✓ Real dataset (100+ samples): 20/20
  ✓ Token calculation: 20/20
  Total Core: 80/80

Bonus (20 points):
  ✓ Structured evaluator: 10/10
  ✓ Reflection memory: 10/10
  Total Bonus: 20/20

FINAL SCORE: 100/100 ✓
```

### Bước 8.2: Kiểm Tra Báo Cáo Thủ Công

```bash
# Xem JSON structure
cat outputs/my_run/report.json | python -m json.tool | head -50

# Xem Markdown
cat outputs/my_run/report.md
```

### Bước 8.3: Gỡ Lỗi Nếu Cần

**Lỗi: "API Key not found"**
```bash
# Kiểm tra file .env
cat .env

# Hoặc set biến môi trường trực tiếp
export ANTHROPIC_API_KEY=your_key
```

**Lỗi: "Report format không khớp"**
- Kiểm tra JSON schema trong `autograde.py`
- Đảm bảo tất cả field bắt buộc đều có

**Lỗi: "Token count = 0"**
- Kiểm tra API response có `usage` field không
- Kiểm tra `call_actor()` đã return token không

---

## 📋 Checklist Hoàn Thành

- [ ] Môi trường setup xong (venv + packages)
- [ ] Hiểu được cấu trúc schemas.py, prompts.py
- [ ] Thay thế mock_runtime.py với LLM thật
  - [ ] Chọn provider (Claude/OpenAI/Ollama)
  - [ ] Tạo file .env với API key
  - [ ] Test gọi API thành công
- [ ] Cập nhật agents.py để nhận token count
- [ ] Chạy benchmark với 100+ mẫu thành công
- [ ] Tính token tiêu thụ chính xác
- [ ] Xuất report.json và report.md đúng format
- [ ] Chạy autograde.py kiểm tra điểm
- [ ] (Tùy chọn) Thực hiện bonus features
- [ ] Commit code lên git

---

## 🆘 Hỗ Trợ Thêm

**Nếu gặp vấn đề**:
1. Xem chi tiết lỗi trong terminal
2. Kiểm tra file `.env` có tồn tại không
3. Test API key bằng curl:
   ```bash
   curl -X POST "https://api.anthropic.com/v1/messages" \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -d '{"model":"claude-3-5-sonnet-20241022","messages":[{"role":"user","content":"Hi"}]}'
   ```
4. Kiểm tra dataset format đúng không
5. Xem log chi tiết: `python run_benchmark.py --debug`

**Liên hệ**: Xem README.md phần "Issues"

