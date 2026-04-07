import os
from typing import TypedDict, Annotated, Literal

import structlog
from langgraph.graph import StateGraph, START, END
from langchain_xai import ChatXAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

logger = structlog.get_logger()

SYSTEM_PROMPT = """

You are a prompt clarity validator. Your job is to read a prompt cold — with zero context about the project, codebase, or history — and evaluate whether a developer tool (like Claude Code) could execute it successfully on the first try.
You are the "outside guy." You have never seen this project before. You don't know the file structure, the tech stack, or what happened in previous conversations. Evaluate the prompt purely on what is written.

Rate the prompt with one of three classifications:

1. **fuzzy** — The prompt is too vague or ambiguous to execute. Key information is missing. Multiple interpretations are possible. A developer tool would either guess wrong or ask for clarification, wasting tokens.

2. **partial** — The prompt has a clear goal but is missing some specifics. The intent is understandable, but there are gaps that could lead to wrong assumptions. A developer tool might get it 60-70% right but would likely need a follow-up round.

3. **very_clear** — The prompt is specific, unambiguous, and actionable. File paths, expected behavior, constraints, and success criteria are stated. A developer tool could execute this on the first pass with high confidence.

Respond ONLY in this JSON format:

{
  "rating": "fuzzy | partial | very_clear",
  "description": "2-3 sentence summary of the prompt's intent as you understand it",
  "issues": ["list of specific problems, ambiguities, or missing details"],
  "suggestions": ["list of specific improvements to make the prompt clearer"]
}

Rules:
- If the rating is "very_clear", issues and suggestions can be empty arrays
- Be specific in issues — don't say "too vague", say "which file should be modified?"
- Be actionable in suggestions — don't say "add more detail", say "specify the database table name"
- Assume the prompt will be executed by an AI coding tool with file system access but no project context
- Do not execute the prompt. Do not write code. Only evaluate clarity.
    """


class StructuredResponse(BaseModel):
    summary: str = Field(..., description="Description of the issues when reading the prompt")
    classification: Literal["fuzzy", "partial", "very_clear"] = Field(
        ..., description="How clear the prompt is"
    )


class State(TypedDict):
    messages: Annotated[list, "add_messages"]
    structured_output: StructuredResponse | None


_graph = None


def _get_graph():
    global _graph
    if _graph is not None:
        return _graph

    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        raise RuntimeError("GROK_API_KEY environment variable is not set")

    from utils.config_loader import load_config
    cfg = load_config()

    structured_llm = ChatXAI(
        model=cfg.grok.model,
        temperature=0,
        api_key=api_key,
    ).with_structured_output(StructuredResponse, method="json_schema")

    def call_grok_structured(state: State) -> dict:
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        response = structured_llm.invoke(messages)
        return {
            "messages": [AIMessage(content=response.model_dump_json())],
            "structured_output": response,
        }

    graph = StateGraph(State)
    graph.add_node("grok_structured", call_grok_structured)
    graph.add_edge(START, "grok_structured")
    graph.add_edge("grok_structured", END)
    _graph = graph.compile()
    return _graph


def register(mcp):

    @mcp.tool()
    async def prompt_check(prompt: str) -> dict:
        """Evaluate a prompt's clarity using Grok. Returns a classification
        (fuzzy, partial, or very_clear) and a summary of issues.

        Args:
            prompt: The prompt text to evaluate.
        """
        try:
            graph = _get_graph()
        except RuntimeError as e:
            logger.error("grok_check_init_failed", error=str(e))
            return {"error": str(e)}

        try:
            result = graph.invoke({"messages": [HumanMessage(content=prompt)]})
            output: StructuredResponse = result["structured_output"]
            logger.info("prompt_check", classification=output.classification)
            return {
                "classification": output.classification,
                "summary": output.summary,
            }
        except Exception as e:
            logger.error("grok_check_failed", error=str(e))
            return {"error": f"Grok API call failed: {e}"}

