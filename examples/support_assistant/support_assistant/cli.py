"""CLI entry point for the support assistant example."""
from __future__ import annotations

import argparse
import asyncio
from typing import Callable

from support_assistant.runtime import build_request_context, build_runtime


async def run_once(
    message: str,
    session_id: str,
    use_llm: bool,
    llm_provider: Callable[[], object] | None,
) -> None:
    runtime = build_runtime(use_llm=use_llm, llm_provider=llm_provider)
    request = build_request_context(message, session_id=session_id, use_llm=use_llm)
    result = await runtime.execute(request)
    print(result.to_response_dict())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Support assistant CLI")
    parser.add_argument("message", nargs="?", help="User message")
    parser.add_argument("--session-id", default="demo", help="Session identifier")
    parser.add_argument("--llm", action="store_true", help="Enable LLM-based routing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    message = args.message or input("Message: ").strip()
    if not message:
        raise SystemExit("Message is required")
    if args.llm:
        raise SystemExit(
            "LLM routing requires an injected llm_provider. "
            "Use build_runtime(use_llm=True, llm_provider=...) in code."
        )
    asyncio.run(run_once(message, args.session_id, args.llm, llm_provider=None))


if __name__ == "__main__":
    main()
