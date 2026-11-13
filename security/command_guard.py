from __future__ import annotations

import shlex


class CommandGuard:
    """Allowlista wyłącznie diagnostycznych, niezmieniających stanu komend."""

    @staticmethod
    def parse(command: str) -> list[str]:
        if not isinstance(command, str) or not command.strip() or len(command) > 1000:
            raise ValueError("Komenda musi mieć od 1 do 1000 znaków.")
        if any(char in command for char in (";", "|", "&", ">", "<", "`", "$", "\n", "\r")):
            raise PermissionError("Operatory powłoki i podstawianie zmiennych są zabronione.")
        try:
            args = shlex.split(command, posix=True)
        except ValueError as exc:
            raise ValueError("Nie można sparsować komendy.") from exc
        if not args:
            raise ValueError("Komenda jest pusta.")
        CommandGuard.validate(args)
        return args

    @staticmethod
    def validate(args: list[str]) -> None:
        if args[0] in {"git", "git.exe"}:
            allowed = {
                ("status",), ("status", "--short"),
                ("diff", "--stat"),
                ("branch", "--show-current"),
                ("rev-parse", "--show-toplevel"),
                ("log", "--oneline"),
            }
            if tuple(args[1:]) in allowed:
                return
            if (len(args) == 5 and args[1:3] == ["log", "--oneline"]
                    and args[3] == "-n" and args[4].isdigit()
                    and 1 <= int(args[4]) <= 20):
                return
        elif args[0] in {"ollama", "ollama.exe"}:
            if args[1:] in (["list"], ["ps"]):
                return
            if len(args) == 3 and args[1] == "show" and not args[2].startswith("-"):
                return
        elif args[0] in {"python", "python.exe", "python3"} and args[1:] in (["--version"], ["-V"]):
            return
        raise PermissionError("Ta komenda nie znajduje się na bezpiecznej allowliście.")


