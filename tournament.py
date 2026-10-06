import asyncio
import contextlib
import sys
from collections import defaultdict
from dataclasses import dataclass, field

import httpx

from arena import MatchResult, play_match

MATCHES_PER_PAIR = 2  # чётное число — каждый участник пары по разу стреляет первым


@dataclass
class Standings:
    wins: dict = field(default_factory=lambda: defaultdict(int))
    losses: dict = field(default_factory=lambda: defaultdict(int))

    def record(self, result: MatchResult) -> None:
        self.wins[result.winner] += 1
        self.losses[result.loser] += 1

    def rows(self, names: list[str]) -> list[tuple[str, int, int]]:
        rows = [(name, self.wins[name], self.losses[name]) for name in names]
        return sorted(rows, key=lambda row: (-row[1], row[2]))


async def play_series(
    client_a: httpx.AsyncClient, name_a: str,
    client_b: httpx.AsyncClient, name_b: str,
    matches_per_pair: int = MATCHES_PER_PAIR,
) -> list[MatchResult]:
    results = []
    for i in range(matches_per_pair):
        if i % 2 == 0:
            results.append(await play_match(client_a, name_a, client_b, name_b))
        else:
            results.append(await play_match(client_b, name_b, client_a, name_a))
    return results


async def run_tournament(
    services: dict[str, str], matches_per_pair: int = MATCHES_PER_PAIR,
) -> list[MatchResult]:
    """Круговой турнир: каждый сервис играет с каждым серию из matches_per_pair партий."""
    names = list(services)
    all_results: list[MatchResult] = []

    async with contextlib.AsyncExitStack() as stack:
        clients = {
            name: await stack.enter_async_context(httpx.AsyncClient(base_url=url))
            for name, url in services.items()
        }
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                all_results.extend(
                    await play_series(clients[name_a], name_a, clients[name_b], name_b, matches_per_pair)
                )

    return all_results


def format_table(results: list[MatchResult], names: list[str]) -> str:
    standings = Standings()
    for result in results:
        standings.record(result)

    lines = [f"{'Сервис':<20}{'Победы':>8}{'Поражения':>12}"]
    for name, wins, losses in standings.rows(names):
        lines.append(f"{name:<20}{wins:>8}{losses:>12}")
    return "\n".join(lines)


def _parse_services(args: list[str]) -> dict[str, str]:
    services = {}
    for arg in args:
        name, sep, url = arg.partition("=")
        if not sep or not name or not url:
            raise ValueError(f"ожидался аргумент вида name=url, получено {arg!r}")
        services[name] = url
    return services


async def _main(args: list[str]) -> None:
    services = _parse_services(args)
    if len(services) < 2:
        raise ValueError("нужно хотя бы два сервиса вида name=url")

    results = await run_tournament(services)

    print(format_table(results, list(services)))
    print()
    for result in results:
        print(f"{result.winner} beat {result.loser}: {result.reason}")


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1:]))
