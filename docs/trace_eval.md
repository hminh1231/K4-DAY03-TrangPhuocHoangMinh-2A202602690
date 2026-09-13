# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Trang Phước Hoàng Minh 
> **Mã Sinh Viên / Mã Học viên:** 2A202602690  
> **Chủ đề Lựa chọn:** *Trợ lý Đơn hàng & Kho vận (Supply Chain Agent):* Tra cứu mã vận đơn, vị trí lưu kho và cập nhật trạng thái đơn hàng. 

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | **4 / 5** | Cập nhật đơn hàng không làm 1 bước. Agent phải tách chuỗi: nhận mã vận đơn → tra cứu vị trí kho và trạng thái hiện tại → đối chiếu trạng thái mới có hợp lệ không → mới ghi nhận. Không cho 5 vì câu hỏi FAQ kho vận (quy trình giao hàng chung) có thể trả lời trực tiếp, không cần suy luận đa bước. |
| **2. Tool Interaction** | **5 / 5** | Vị trí lưu kho và trạng thái đơn là dữ liệu thời gian thực, không được nhét vào System Prompt. Hệ thống bắt buộc kết nối MCP Server: 1 tool tra cứu vận đơn theo mã và 1 tool hành động cập nhật trạng thái. Thiếu tool thì Agent sẽ bịa đơn hoặc không ghi được trạng thái. |
| **3. Dynamic Decision** | **4 / 5** | Bước tiếp theo phụ thuộc Observation. Đơn `Đang vận chuyển` mới được cập nhật `Đã giao`; đơn `NOT_FOUND` thì dừng và báo không tìm thấy, không bịa; đơn `Đã hủy` thì từ chối chuyển sang `Đã giao`. Không cho 5 vì tập nhánh quyết định còn hẹp (hợp lệ / không hợp lệ / không tồn tại). |
| **4. Long Horizon Goal** | **4 / 5** | Mục tiêu xuyên suốt là “cập nhật đúng trạng thái cho đúng mã vận đơn”. Agent phải giữ mã đơn, kho hiện tại và trạng thái đích qua nhiều lượt Thought → Action → Observation, không được quên mục tiêu sau khi tra cứu xong. Không cho 5 vì horizon ngắn (một phiên, 2–3 tool call), chưa phải quy trình nhiều ngày. |
| **TỔNG ĐIỂM AGENTIC FIT** | **17 / 20** | *Nếu tổng điểm > 12/20: Bài toán rất phù hợp triển khai Agentic System.* Tổng 17/20 — đề Kho vận đủ điều kiện dùng ReAct Agent, không nên làm Chatbot FAQ. |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
{
  "step": 1,
  "query": "Hãy tra cứu thông tin vận đơn DH2026001: vị trí lưu kho và trạng thái hiện tại.",
  "action_type": "TOOL_EXECUTION",
  "tool_name": "academic_query",
  "arguments": {
    "student_id": "DH2026001"
  },
  "observation": {
    "status": "SUCCESS",
    "tracking_code": "DH2026001",
    "data": {
      "warehouse": "Kho Hà Nội",
      "status": "Đang vận chuyển",
      "coordinator": "Nguyễn Văn A",
      "items": "Phụ tùng pin VF8"
    }
  }
}
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 5 lượt (`academic_query` × 3, `schedule_appointment` × 2).
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

Repo nộp bài: https://github.com/hminh1231/K4-DAY03-TrangPhuocHoangMinh-2A202602690

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
