from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


class WebSearchError(RuntimeError):
    pass


@dataclass
class WebSearchClient:
    """Wyszukiwanie WWW przez jawnie skonfigurowany dostawca API."""

    provider: str = ""
    api_key: str = ""
    timeout: float = 12.0
    max_results: int = 5

    @classmethod
    def from_env(cls) -> "WebSearchClient":
        try:
            timeout = float(os.getenv("AI_WEB_SEARCH_TIMEOUT", "12"))
        except ValueError:
            timeout = 12.0
        try:
            max_results = int(os.getenv("AI_WEB_SEARCH_MAX_RESULTS", "5"))
        except ValueError:
            max_results = 5
        return cls(
            provider=os.getenv("AI_WEB_SEARCH_PROVIDER", "").strip().lower(),
            api_key=os.getenv("AI_WEB_SEARCH_API_KEY", "").strip(),
            timeout=max(1.0, min(timeout, 60.0)),
            max_results=max(1, min(max_results, 10)),
        )

    @property
    def enabled(self) -> bool:
        return self.provider in {"tavily", "brave"} and bool(self.api_key)

    def search(self, query: str) -> list[dict[str, str]]:
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise ValueError("Zapytanie musi mieć od 1 do 500 znaków.")
        if not self.enabled:
            raise WebSearchError(
                "Wyszukiwanie WWW jest wyłączone. Ustaw AI_WEB_SEARCH_PROVIDER "
                "na tavily lub brave oraz AI_WEB_SEARCH_API_KEY."
            )
        count = max(1, min(self.max_results, 10))
        try:
            if self.provider == "tavily":
                response = httpx.post(
                    "https://api.tavily.com/search",
                    json={"api_key": self.api_key, "query": query.strip(),
                          "search_depth": "basic", "max_results": count,
                          "include_answer": False},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                raw = response.json().get("results", [])
            else:
                response = httpx.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query.strip(), "count": count},
                    headers={"X-Subscription-Token": self.api_key,
                             "Accept": "application/json"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                raw = response.json().get("web", {}).get("results", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise WebSearchError(f"Dostawca wyszukiwania zwrócił błąd: {exc}") from exc
        results: list[dict[str, str]] = []
        for item in raw[:count] if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            title, url = item.get("title"), item.get("url")
            snippet = item.get("content") or item.get("description") or ""
            if isinstance(title, str) and isinstance(url, str) and url.startswith(("https://", "http://")):
                results.append({"title": title[:300], "url": url[:2000],
                                "snippet": str(snippet)[:1200]})
        return results
