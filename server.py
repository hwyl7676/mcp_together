#!/usr/bin/env python3
"""
Antigravity - Claude Architect MCP Server (Python Edition)
소넷(claude-sonnet-4-6) 협업을 위한 로컬 Stdio MCP 서버 (타임아웃 120초)
"""

import sys
import os
import json
import urllib.request
import urllib.error

# 1. .env 파일 로드
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(CURRENT_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and val and key not in os.environ:
                    os.environ[key] = val

API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "").strip()
DEFAULT_MODEL: str = os.environ.get("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-5").strip()
TIMEOUT_SECONDS: int = 120

MODEL_ALIASES: dict[str, str] = {
    "sonnet": "claude-sonnet-5",
    "sonnet5": "claude-sonnet-5",
    "claude-sonnet": "claude-sonnet-5",
    "claude-sonnet-5": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "opus5": "claude-opus-5",
    "claude-opus": "claude-opus-5",
    "claude-opus-5": "claude-opus-5",
    "fable": "claude-fable-5-1",
    "fable5": "claude-fable-5-1",
    "claude-fable": "claude-fable-5-1",
    "claude-fable-5-1": "claude-fable-5-1",
    "haiku": "claude-haiku-4-5",
    "haiku4": "claude-haiku-4-5",
    "claude-haiku": "claude-haiku-4-5",
    "claude-haiku-4-5": "claude-haiku-4-5",
}

def resolve_model(model_name: str) -> str:
    if not model_name or not model_name.strip():
        return DEFAULT_MODEL
    cleaned: str = model_name.strip().lower()
    return MODEL_ALIASES.get(cleaned, model_name.strip())

SYSTEM_PROMPT = """당신은 최고 수준의 소프트웨어 수석 아키텍트입니다.
Antigravity로부터 전달받은 코드와 문제 요약을 분석하고 리팩토링할 때, 반드시 아래 3대 검증 기준을 엄격히 적용하여 최적의 코드를 작성하세요.

1. 프레임워크 / OS 버전 호환성
   - 타겟 SDK 및 프로젝트 라이브러리 버전에 실제로 존재하는 표준 API만 사용할 것 (가상/환각 API 호출 금지).
   - 비동기/동시성 모델 수명주기(Lifecycle) 및 플랫폼 권한 정합성을 보장할 것.

2. 과잉 엔지니어링 (Over-Engineering) 배제
   - 단순한 로직 대비 불필요하게 복잡한 추상화 레이어, 제네릭 래퍼, 불필요한 디자인 패턴을 남용하지 말 것.
   - 코드 가독성과 유지보수성을 해치는 보일러플레이트를 제거하고 핵심 로직 중심으로 작성할 것.

3. 엣지 케이스 및 사이드 이펙트 완벽 방어
   - Null / Nil 안전성, 옵셔널 언래핑 예외 처리를 누락 없이 완벽히 방어할 것.
   - 메모리 누수(Retain cycle), 동시성 충돌(Race condition/Deadlock), 네트워크 예외 핸들링을 철저히 구현할 것.
"""

def call_anthropic(task_summary: str, context_code: str, model: str = DEFAULT_MODEL) -> str:
    if not API_KEY:
        raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    user_content = f"### 해결 과제 요약:\n{task_summary}\n\n"
    if context_code:
        user_content += f"### 대상 소스코드 및 컨텍스트:\n```\n{context_code}\n```"

    target_model = resolve_model(model)
    payload = {
        "model": target_model,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_content}
        ]
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text_blocks = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
            return "\n".join(text_blocks)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API 오류 ({e.code}): {error_body}")
    except Exception as e:
        raise RuntimeError(f"Claude 호출 중 에러 발생: {str(e)}")

def send_response(response_dict):
    json_str = json.dumps(response_dict, ensure_ascii=False)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()

def handle_message(msg):
    msg_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params", {})

    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "antigravity-claude-architect",
                    "version": "1.0.0"
                }
            }
        })
    elif method == "notifications/initialized":
        # Notification, no response
        pass
    elif method == "ping":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {}
        })
    elif method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "consult_claude_architect",
                        "description": "복잡한 로직 검수 및 리팩토링을 위해 소넷(claude-sonnet-4-6)에 심층 자문을 요청합니다. (120초 타임아웃, 3대 아키텍처 검증 기준 적용)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_summary": {
                                    "type": "string",
                                    "description": "해결해야 할 문제 요약 및 요구사항"
                                },
                                "context_code": {
                                    "type": "string",
                                    "description": "리팩토링 대상 파일 전체 코드 및 연관 인터페이스/타입 정의"
                                },
                                "model": {
                                    "type": "string",
                                    "description": "사용할 모델명 (기본값: claude-sonnet-4-6)",
                                    "default": "claude-sonnet-4-6"
                                }
                            },
                            "required": ["task_summary"]
                        }
                    }
                ]
            }
        })
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        if tool_name == "consult_claude_architect":
            task_summary = tool_args.get("task_summary", "")
            context_code = tool_args.get("context_code", "")
            model = tool_args.get("model", DEFAULT_MODEL)
            try:
                result_text = call_anthropic(task_summary, context_code, model)
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result_text
                            }
                        ],
                        "isError": False
                    }
                })
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error calling Claude Sonnet: {str(e)}"
                            }
                        ],
                        "isError": True
                    }
                })
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            })
    else:
        if msg_id is not None:
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            })

def main():
    sys.stderr.write("[MCP Sonnet Server] Started successfully (120s timeout).\n")
    sys.stderr.flush()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            handle_message(msg)
        except Exception as e:
            sys.stderr.write(f"[MCP Sonnet Server Error] {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
