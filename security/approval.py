from __future__ import annotations

import json
from typing import Any, Callable


class ConsoleApproval:
    """Ask the local user before an approval-gated tool is executed.

    The default decision is always deny. This helper is intended for an
    interactive terminal; APIs and background workers should inject their own
    approval callback or leave it unset.
    """

    def __init__(
        self,
        input_fn: Callable[[str], str] | None = None,
        output_fn: Callable[[str], Any] | None = None,
    ) -> None:
        self._input = input_fn or input
        self._output = output_fn or print

    def approve(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        preview = json.dumps(arguments, ensure_ascii=False, indent=2, default=str)
        if len(preview) > 3000:
            preview = preview[:3000] + "\n… (podgląd skrócony)"
        self._output("\nWymagana zgoda na wykonanie narzędzia:")
        self._output(f"Narzędzie: {tool_name}")
        self._output(f"Argumenty:\n{preview}")
        answer = self._input("Zezwolić? [t/N]: ").strip().lower()
        return answer in {"t", "tak", "y", "yes"}
