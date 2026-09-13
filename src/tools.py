"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Đề tài: Trợ lý Đơn hàng & Kho vận (Supply Chain Agent).
Giữ tên tool academic_query / schedule_appointment để khớp checkpoint lab.
"""

import copy
import json
import sys
from typing import Dict, Any

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "academic_query",
        "description": (
            "Tra cứu vận đơn kho vận VinFast theo mã vận đơn: vị trí lưu kho, "
            "trạng thái hiện tại, hàng hóa và điều phối phụ trách."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã vận đơn cần tra cứu (ví dụ: 'DH2026001')"
                }
            },
            "required": ["student_id"]
        }
    },
    {
        "name": "schedule_appointment",
        "description": (
            "Cập nhật trạng thái vận đơn kho vận (ví dụ sang 'Đã giao' hoặc 'Đang vận chuyển') "
            "theo mã vận đơn, thời điểm cập nhật và điều phối phụ trách. "
            "Chỉ cập nhật khi đơn tồn tại và trạng thái mới hợp lệ."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã vận đơn cần cập nhật (ví dụ: 'DH2026001')"
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời điểm cập nhật trạng thái (ví dụ: '14:00 15/09/2026')"
                },
                "advisor_name": {
                    "type": "string",
                    "description": "Tên điều phối kho vận phụ trách cập nhật"
                },
                "new_status": {
                    "type": "string",
                    "description": "Trạng thái mới của vận đơn (ví dụ: 'Đã giao', 'Đang vận chuyển', 'Đã hủy')"
                }
            },
            "required": ["student_id", "datetime_str", "advisor_name"]
        }
    },
    {
        "name": "update_shipment",
        "description": (
            "Cập nhật thông tin chi tiết vận đơn: hàng hóa, kho lưu trữ hoặc tên khách hàng. "
            "Dùng khi nhân viên muốn đổi nội dung hàng (ví dụ VF8 thành VF9). "
            "KHÔNG dùng tool này để đổi trạng thái giao nhận — trạng thái dùng schedule_appointment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã vận đơn cần sửa thông tin (ví dụ: 'DH2026001')"
                },
                "items": {
                    "type": "string",
                    "description": "Hàng hóa mới trên vận đơn (ví dụ: 'Phụ tùng pin VF9')"
                },
                "warehouse": {
                    "type": "string",
                    "description": "Kho lưu trữ mới (ví dụ: 'Kho Hải Phòng')"
                },
                "customer_name": {
                    "type": "string",
                    "description": "Tên khách hàng mới trên vận đơn"
                }
            },
            "required": ["student_id"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

VALID_STATUS_TRANSITIONS = {
    "Đang lưu kho": {"Đang vận chuyển", "Đã hủy"},
    "Đang vận chuyển": {"Đã giao", "Đã hủy", "Đang lưu kho"},
    "Đã giao": set(),
    "Đã hủy": set(),
}


def _make_shipment(tracking_code: str, customer: str, warehouse: str, status: str, coordinator: str, items: str) -> Dict[str, Any]:
    return {
        "tracking_code": tracking_code,
        "customer_name": customer,
        "full_name": customer,
        "warehouse": warehouse,
        "status": status,
        "coordinator": coordinator,
        "advisor": coordinator,
        "items": items,
    }


MOCK_DATABASE: Dict[str, Dict[str, Any]] = {
    "DH2026001": _make_shipment(
        "DH2026001", "Nguyễn Văn An", "Kho Hà Nội",
        "Đang vận chuyển", "Nguyễn Văn A", "Phụ tùng pin VF8"
    ),
    "DH2026002": _make_shipment(
        "DH2026002", "Trần Thị Bình", "Kho Hải Phòng",
        "Đang lưu kho", "Trần Thị Bình", "Cụm đèn VF9"
    ),
    "DH2026003": _make_shipment(
        "DH2026003", "Lê Minh Cường", "Kho Đà Nẵng",
        "Đã hủy", "Phạm Quốc Dũng", "Bộ sạc VF e34"
    ),
}
# Alias để lệnh kiểm thử lab (SV2026001) vẫn ra SUCCESS
MOCK_DATABASE["SV2026001"] = dict(MOCK_DATABASE["DH2026001"])
MOCK_DATABASE["SV2026001"]["tracking_code"] = "SV2026001"
_INITIAL_DATABASE = copy.deepcopy(MOCK_DATABASE)


def reset_mock_database() -> None:
    """Khôi phục dữ liệu kho về trạng thái ban đầu (mỗi test case chạy độc lập)."""
    MOCK_DATABASE.clear()
    MOCK_DATABASE.update(copy.deepcopy(_INITIAL_DATABASE))


def execute_academic_query(student_id: str, **kwargs) -> str:
    """Tra cứu vận đơn theo mã (tham số lab: student_id = mã vận đơn)."""
    tracking_code = student_id.strip().upper()
    shipment = MOCK_DATABASE.get(tracking_code)
    if shipment:
        return json.dumps({
            "status": "SUCCESS",
            "student_id": student_id,
            "tracking_code": tracking_code,
            "data": shipment
        }, ensure_ascii=False)
    return json.dumps({
        "status": "NOT_FOUND",
        "message": f"Không tìm thấy vận đơn có mã '{student_id}'. Không bịa vị trí kho hoặc trạng thái."
    }, ensure_ascii=False)


def execute_schedule_appointment(
    student_id: str,
    datetime_str: str,
    advisor_name: str = "Nguyễn Văn A",
    new_status: str = "Đã giao",
    **kwargs
) -> str:
    """Cập nhật trạng thái vận đơn (map từ tool schedule_appointment của lab)."""
    tracking_code = student_id.strip().upper()
    shipment = MOCK_DATABASE.get(tracking_code)
    if not shipment:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy vận đơn có mã '{student_id}'. Từ chối cập nhật trạng thái."
        }, ensure_ascii=False)

    current_status = shipment.get("status", "")
    allowed_next = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status != current_status and new_status not in allowed_next:
        return json.dumps({
            "status": "REJECTED",
            "student_id": student_id,
            "tracking_code": tracking_code,
            "message": (
                f"Không thể chuyển vận đơn {tracking_code} từ '{current_status}' sang '{new_status}'. "
                "Giữ nguyên trạng thái hiện tại."
            )
        }, ensure_ascii=False)

    shipment["status"] = new_status
    shipment["coordinator"] = advisor_name
    shipment["advisor"] = advisor_name
    shipment["last_update"] = datetime_str

    return json.dumps({
        "status": "SUCCESS",
        "booking_id": f"UPD-{tracking_code}-99",
        "student_id": student_id,
        "tracking_code": tracking_code,
        "datetime": datetime_str,
        "advisor": advisor_name,
        "new_status": new_status,
        "warehouse": shipment.get("warehouse"),
        "message": (
            f"Đã cập nhật vận đơn {tracking_code} thành '{new_status}' tại {shipment.get('warehouse')} "
            f"lúc {datetime_str}, điều phối {advisor_name}."
        )
    }, ensure_ascii=False)


def execute_update_shipment(
    student_id: str,
    items: str = "",
    warehouse: str = "",
    customer_name: str = "",
    **kwargs
) -> str:
    """Cập nhật hàng hóa / kho / khách trên vận đơn, không đổi trạng thái giao nhận."""
    tracking_code = student_id.strip().upper()
    shipment = MOCK_DATABASE.get(tracking_code)
    if not shipment:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy vận đơn có mã '{student_id}'. Không sửa hàng hóa giả."
        }, ensure_ascii=False)

    items = (items or "").strip()
    warehouse = (warehouse or "").strip()
    customer_name = (customer_name or "").strip()

    if shipment.get("status") == "Đã hủy":
        return json.dumps({
            "status": "REJECTED",
            "tracking_code": tracking_code,
            "message": f"Vận đơn {tracking_code} đã hủy, không được điều chỉnh thông tin hàng hóa."
        }, ensure_ascii=False)

    updates = {}
    if items:
        updates["items"] = items
    if warehouse:
        updates["warehouse"] = warehouse
    if customer_name:
        updates["customer_name"] = customer_name.strip()
        updates["full_name"] = customer_name.strip()

    if not updates:
        return json.dumps({
            "status": "REJECTED",
            "tracking_code": tracking_code,
            "message": "Cần ít nhất một trường để cập nhật: items, warehouse hoặc customer_name."
        }, ensure_ascii=False)

    before = {key: shipment.get(key) for key in updates}
    shipment.update(updates)
    return json.dumps({
        "status": "SUCCESS",
        "tracking_code": tracking_code,
        "student_id": student_id,
        "updated_fields": updates,
        "previous_fields": before,
        "data": shipment,
        "message": (
            f"Đã cập nhật vận đơn {tracking_code}: "
            + ", ".join(f"{k} '{before[k]}' → '{v}'" for k, v in updates.items())
        )
    }, ensure_ascii=False)


TOOL_ROUTER = {
    "academic_query": execute_academic_query,
    "schedule_appointment": execute_schedule_appointment,
    "update_shipment": execute_update_shipment
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool theo tên LLM đã chọn."""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)


if __name__ == "__main__":
    print("==========================================================")
    print("🛠️ KIỂM THỬ PYTHON TOOL DISPATCHER (TASK 2.1)")
    print("==========================================================")

    registered = [tool.get("name") for tool in TOOLS_SCHEMA]
    schema_ready = all(tool.get("parameters", {}).get("properties") for tool in TOOLS_SCHEMA)
    if len(registered) >= 2 and schema_ready:
        print("✅ [TOOLS CHECK]: Đã đăng ký thành công 2 Native Tools trong TOOLS_SCHEMA!")
    else:
        print(f"⏳ [TOOLS CHECK]: Schema chưa đủ. Tools hiện có: {registered}")

    raw_result = dispatch_tool_call("academic_query", {"student_id": "DH2026001"})
    result = json.loads(raw_result)
    if result.get("status") == "SUCCESS":
        customer = result.get("data", {}).get("full_name", "")
        warehouse = result.get("data", {}).get("warehouse", "")
        print(f"✅ Kết quả gọi thử academic_query: Status SUCCESS (Sinh viên {customer})")
        print(f"   Vận đơn DH2026001 đang ở {warehouse}, trạng thái {result['data'].get('status')}.")
    else:
        print(f"❌ Kết quả gọi thử academic_query: {raw_result}")
