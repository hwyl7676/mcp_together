# Antigravity + 소넷 Latest - 1 MCP 협업 서버

Antigravity의 빠른 에디터 코딩과 **소넷 Latest - 1(최신 직전 안정화 모델)**의 정밀 검수를 결합한 로컬 Stdio MCP 서버입니다.

## 1. 운영 원칙

1. **평소 코딩**: Antigravity와 무료/상시로 빠르게 코딩을 진행합니다.
2. **독립 리뷰 요청**: 사용자가 "소넷으로 리뷰해줘"라고 지시할 때만 소넷 Latest - 1(`claude-3-5-sonnet-20241022`)을 호출합니다.
3. **2차 검수 및 안전 반영**: 소넷이 반환한 수정 코드를 Antigravity가 [로컬 호환성 교정 ➡️ 과잉 엔지니어링 쳐내기 ➡️ 누락 방지 안전 병합] 후 에디터 파일에 반영합니다.
4. **비용 보호**: 오퍼스 및 5시리즈 등 고비용 모델을 원천 차단하여 1회당 약 35~80원 선으로 비용을 엄격히 통제합니다.

## 2. 의존성 설치

프로젝트 디렉토리에서 아래 명령어를 실행합니다:

```bash
cd /Users/taehwankim/Desktop/Antigravity_Projects/mcp_together
npm install
```

## 3. Antigravity MCP 설정 등록

Antigravity의 MCP 설정 파일에 아래 내용을 등록하고 `ANTHROPIC_API_KEY`에 실제 발급받은 키를 입력합니다:

```json
{
  "mcpServers": {
    "claude-architect": {
      "command": "node",
      "args": [
        "/Users/taehwankim/Desktop/Antigravity_Projects/mcp_together/index.js"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-api03-실제키입력"
      }
    }
  }
}
```

## 4. 실전 사용 지시

Antigravity 대화창에서 다음과 같이 요청하시면 됩니다:

> "이 파일의 비동기 처리 구조를 분석하고, 소넷으로 3대 기준(호환성, 과잉 엔지니어링 배제, 엣지 케이스) 리뷰를 돌려서 안전하게 파일에 반영해 줘."
