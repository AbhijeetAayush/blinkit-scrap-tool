from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProxyConfig:
    server: str
    username: str
    password: str

    def as_playwright(self) -> dict[str, str]:
        server = self.server if self.server.startswith("http") else f"http://{self.server}"
        return {"server": server, "username": self.username, "password": self.password}
