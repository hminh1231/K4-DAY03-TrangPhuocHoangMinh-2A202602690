"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def _clean_api_key(raw: str | None) -> str:
    """Bỏ khoảng trắng và dấu ngoặc kép quanh API key trong file .env."""
    if not raw:
        return ""
    return raw.strip().strip('"').strip("'").strip()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


TRACKING_CODE_RE = re.compile(r"\b([A-Za-z]{2,}\d{4,})\b")


def extract_tracking_code(prompt: str) -> str:
    """Lấy mã vận đơn từ câu hỏi gốc, không lấy mã trong Observation (tránh trả nhầm SV2026001)."""
    original = re.split(r"\n\[(?:Action|Observation)\]:", prompt, maxsplit=1)[0]
    match = TRACKING_CODE_RE.search(original)
    if match:
        return match.group(1).upper()
    match = TRACKING_CODE_RE.search(prompt)
    return match.group(1).upper() if match else ""


def extract_new_items(prompt: str) -> str:
    """Lấy tên hàng hóa mới từ cụm 'thành ...' trong câu hỏi gốc."""
    original = re.split(r"\n\[(?:Action|Observation)\]:", prompt, maxsplit=1)[0].strip()
    match = re.search(r"thành\s+(.+)$", original, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip(" .")
    return ""


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        entity_id = extract_tracking_code(prompt)
        observation_count = prompt_lower.count("[observation]")

        # Đã có Observation: gọi tool tiếp theo (nếu là bài toán đa bước) hoặc trả lời cuối cùng
        if observation_count >= 1:
            needs_status = any(keyword in prompt_lower for keyword in ["đặt lịch", "cập nhật trạng thái", "đã giao"])
            needs_item_update = any(
                keyword in prompt_lower
                for keyword in ["hàng hóa", "điều chỉnh hàng", "thay đổi hàng", "đổi hàng", "sửa hàng"]
            )
            already_status = "booking_id" in prompt_lower or "schedule_appointment" in prompt_lower
            already_item = "update_shipment" in prompt_lower or "updated_fields" in prompt_lower
            not_found = "not_found" in prompt_lower
            if needs_item_update and not already_item and not not_found and observation_count == 1 and entity_id:
                items = extract_new_items(prompt)
                args = {"student_id": entity_id}
                if items:
                    args["items"] = items
                return {
                    "type": "tool_call",
                    "tool_name": "update_shipment",
                    "arguments": args,
                    "thought": "Đã tra cứu vận đơn. Tiếp tục gọi update_shipment để đổi hàng hóa."
                }
            if needs_status and not already_status and not not_found and observation_count == 1 and entity_id:
                return {
                    "type": "tool_call",
                    "tool_name": "schedule_appointment",
                    "arguments": {
                        "student_id": entity_id,
                        "datetime_str": "14:00 15/09/2026",
                        "advisor_name": "Nguyễn Văn A",
                        "new_status": "Đã giao"
                    },
                    "thought": "Đã nhận Observation tra cứu. Tiếp tục gọi tool cập nhật trạng thái."
                }
            return {
                "type": "text",
                "content": self._final_answer_from_observation(prompt),
                "thought": "Đã đủ Observation, tổng hợp câu trả lời cuối cùng, không bịa dữ liệu."
            }

        needs_item_update = any(
            keyword in prompt_lower
            for keyword in ["hàng hóa", "điều chỉnh hàng", "thay đổi hàng", "đổi hàng", "sửa hàng"]
        )
        if needs_item_update:
            if not entity_id:
                return {
                    "type": "text",
                    "content": "Bạn vui lòng cung cấp mã vận đơn cần điều chỉnh hàng hóa (ví dụ DH2026001).",
                    "thought": "Thiếu mã vận đơn nên không gọi update_shipment."
                }
            items = extract_new_items(prompt)
            args = {"student_id": entity_id}
            if items:
                args["items"] = items
            return {
                "type": "tool_call",
                "tool_name": "update_shipment",
                "arguments": args,
                "thought": f"Người dùng muốn điều chỉnh thông tin vận đơn {entity_id}. Gọi update_shipment."
            }

        if any(keyword in prompt_lower for keyword in ["đặt lịch", "cập nhật trạng thái", "cập nhật vận đơn"]):
            if not entity_id:
                return {
                    "type": "text",
                    "content": "Bạn vui lòng cung cấp mã vận đơn cần cập nhật (ví dụ DH2026001).",
                    "thought": "Thiếu mã vận đơn nên không gọi tool hành động."
                }
            if any(keyword in prompt_lower for keyword in ["kiểm tra", "nếu", "trước"]):
                return {
                    "type": "tool_call",
                    "tool_name": "academic_query",
                    "arguments": {"student_id": entity_id},
                    "thought": "Bài toán đa bước: tra cứu dữ liệu trước, rồi mới cập nhật."
                }
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {
                    "student_id": entity_id,
                    "datetime_str": "14:00 15/09/2026",
                    "advisor_name": "Nguyễn Văn A",
                    "new_status": "Đã giao"
                },
                "thought": f"Người dùng yêu cầu hành động cập nhật/đặt lịch cho mã {entity_id}."
            }
        elif any(keyword in prompt_lower for keyword in ["tra cứu", "kiểm tra"]) or entity_id:
            if not entity_id:
                return {
                    "type": "text",
                    "content": "Bạn vui lòng cung cấp mã vận đơn (ví dụ DH2026001) để hệ thống tra cứu. Em không bịa dữ liệu khi thiếu mã.",
                    "thought": "Người dùng muốn tra cứu nhưng chưa nêu mã vận đơn."
                }
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": entity_id},
                "thought": f"Người dùng muốn tra cứu thông tin của mã {entity_id}. Tôi sẽ gọi tool academic_query."
            }
        else:
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Xin chào! Quy trình kho vận nội bộ gồm nhập kho, lưu kho, vận chuyển và bàn giao. Đơn hàng được cập nhật trạng thái theo thời gian thực.",
                "thought": "Câu hỏi chung, trả lời trực tiếp không cần gọi Tool."
            }

    def _final_answer_from_observation(self, prompt: str) -> str:
        marker = "[Observation]:"
        if marker not in prompt:
            return "Đã nhận kết quả từ công cụ."
        chunk = prompt[prompt.rfind(marker) + len(marker):].strip().split("\n")[0]
        try:
            obs = json.loads(chunk)
        except json.JSONDecodeError:
            return "Đã nhận Observation từ công cụ."
        if obs.get("status") == "NOT_FOUND":
            return obs.get("message", "Không tìm thấy dữ liệu yêu cầu.")
        if obs.get("status") == "SUCCESS" and "data" in obs:
            data = obs["data"]
            return (
                f"Kết quả tra cứu vận đơn {obs.get('tracking_code', obs.get('student_id', ''))}: "
                f"khách {data.get('customer_name', data.get('full_name', ''))}, "
                f"kho {data.get('warehouse', '')}, trạng thái {data.get('status', '')}, "
                f"điều phối {data.get('coordinator', data.get('advisor', ''))}."
            )
        if obs.get("message"):
            return obs["message"]
        return json.dumps(obs, ensure_ascii=False)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    _live_disabled = False

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = _clean_api_key(api_key or os.getenv("GEMINI_API_KEY"))
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def _should_use_mock(self) -> bool:
        if GeminiProvider._live_disabled:
            return True
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return True
        return False

    def _mark_invalid_key(self, error: Exception) -> None:
        text = str(error)
        if any(token in text for token in ["API_KEY_INVALID", "API key not valid"]):
            GeminiProvider._live_disabled = True

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if GeminiProvider._live_disabled:
            print("ℹ️ [Gemini Provider]: Key đã bị Gemini từ chối ở bước trước. Tiếp tục Mock, không gọi lại API.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa thấy GEMINI_API_KEY trong .env. Đang dùng Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            self._mark_invalid_key(e)
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = _clean_api_key(api_key or os.getenv("OPENAI_API_KEY"))
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = _clean_api_key(os.getenv("GEMINI_API_KEY"))
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = _clean_api_key(os.getenv("OPENAI_API_KEY"))
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
