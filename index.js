import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import Anthropic from "@anthropic-ai/sdk";

// 소넷 Latest - 1 단일 모델 화이트리스트 정책 (비용 보호를 위해 고가 모델 원천 차단)
const ALLOWED_MODELS = ["claude-3-5-sonnet-20241022"];
const DEFAULT_MODEL = "claude-3-5-sonnet-20241022";

// API 키 사전 유효성 검증
const apiKey = process.env.ANTHROPIC_API_KEY;
if (!apiKey || apiKey.trim() === "") {
  console.error("[오류] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.");
  process.exit(1);
}

// Anthropic 클라이언트 초기화 (30초 타임아웃 방어벽)
const anthropic = new Anthropic({
  apiKey: apiKey.trim(),
  timeout: 30000,
});

// MCP Stdio 서버 인스턴스 생성
const server = new Server(
  {
    name: "antigravity-claude-architect",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 3대 교차 검증 시스템 프롬프트 정의
const SYSTEM_PROMPT = `
당신은 최고 수준의 소프트웨어 수석 아키텍트입니다.
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
`;

// 1. 도구 명세 등록 (ListTools)
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "consult_claude_architect",
        description:
          "사용자의 명시적 요청 시, 복잡한 로직 검수 및 리팩토링을 위해 소넷 Latest - 1 모델에 심층 자문을 요청합니다. (전달 시 리팩토링 대상 파일 전체 코드 및 연관 인터페이스 정의를 온전히 포함할 것)",
        inputSchema: {
          type: "object",
          properties: {
            task_summary: {
              type: "string",
              description: "해결해야 할 문제 요약 및 요구사항",
            },
            context_code: {
              type: "string",
              description: "리팩토링 대상 파일 전체 코드 및 연관 인터페이스/타입 정의",
            },
            model: {
              type: "string",
              description: "호출할 모델 (소넷 Latest - 1 고정: claude-3-5-sonnet-20241022)",
              enum: ALLOWED_MODELS,
            },
          },
          required: ["task_summary", "context_code"],
        },
      },
    ],
  };
});

// 2. 도구 실행 핸들러 (CallTool)
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "consult_claude_architect") {
    const args = request.params.arguments || {};
    const taskSummary = args.task_summary;
    const contextCode = args.context_code;
    const requestedModel = args.model;

    // 입력값 무결성 검증
    if (!taskSummary || typeof taskSummary !== "string" || taskSummary.trim() === "") {
      return {
        isError: true,
        content: [{ type: "text", text: "오류: task_summary가 비어 있거나 올바르지 않습니다." }],
      };
    }

    if (!contextCode || typeof contextCode !== "string" || contextCode.trim() === "") {
      return {
        isError: true,
        content: [{ type: "text", text: "오류: context_code가 비어 있거나 올바르지 않습니다." }],
      };
    }

    // 허용 모델 검증 및 고가 모델 방어 (소넷 Latest - 1 강제 고정)
    let targetModel = DEFAULT_MODEL;
    if (requestedModel && !ALLOWED_MODELS.includes(requestedModel)) {
      console.warn(`[비용 보호 경고] 비허용 모델(${requestedModel}) 요청 감지 -> 소넷 Latest - 1(${DEFAULT_MODEL})로 자동 대체.`);
    }

    try {
      const response = await anthropic.messages.create({
        model: targetModel,
        max_tokens: 4096,
        system: SYSTEM_PROMPT.trim(),
        messages: [
          {
            role: "user",
            content: `[문제 요약]\n${taskSummary.trim()}\n\n[대상 코드 및 컨텍스트]\n${contextCode.trim()}`,
          },
        ],
      });

      const responseText =
        response.content && response.content[0] && response.content[0].type === "text"
          ? response.content[0].text
          : "응답 텍스트를 추출할 수 없습니다.";

      return {
        content: [
          {
            type: "text",
            text: responseText,
          },
        ],
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`[Claude API 호출 오류] ${errorMessage}`);
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Claude API 호출 실패: ${errorMessage}`,
          },
        ],
      };
    }
  }

  throw new Error(`지원하지 않는 도구 이름입니다: ${request.params.name}`);
});

// 3. Stdio 전송 계층 연결
const transport = new StdioServerTransport();
await server.connect(transport);
