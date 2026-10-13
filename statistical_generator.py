"""Generator liczb oparty na statystykach z faktycznych wyników losowań zapisanych w bazie"""
import random
from collections import Counter
from itertools import combinations
from database import LottomatDatabase, Record

type Draw = tuple[str, str | None]  # (liczby główne "1,2,3", gwiazdy "4,5" lub None)
type Profile = tuple[frozenset[int], frozenset[int], int, int, int]  # (nieparzyste, niskie, suma min, suma max, kolejne maks.)


class StatisticalGenerator:
    """Losuje zestawy ważone historią losowań, a następnie odrzuca te, których struktura odbiega od historycznej.

    Uwzględnia m.in. (także statystyki niewyświetlane w archiwum):
    - częstotliwość liczb względem wartości oczekiwanej,
    - zaległość liczby (ile losowań minęło od jej ostatniego wystąpienia),
    - rozkład parzyste/nieparzyste oraz niskie/wysokie,
    - zakres sumy liczb w zestawie (10.–90. percentyl historii),
    - dopuszczalną liczbę kolejnych liczb (np. 17, 18),
    - częstość występowania par liczb (wybór zestawu z krótkiej listy poprawnych kandydatów).
    Statystyka nie zwiększa szans na wygraną – losowania są niezależne.
    """

    MIN_DRAWS = 10  # minimalna liczba losowań w bazie potrzebna do wygenerowania zestawu
    MAX_ATTEMPTS = 4000
    SHORTLIST_SIZE = 25
    FREQ_WEIGHT = 0.5
    OVERDUE_WEIGHT = 0.5
    OVERDUE_CAP = 2.5
    MIN_SHARE = 0.10  # minimalny udział w historii, by dany rozkład uznać za typowy
    LOTTO_POOL, LOTTO_SIZE = 49, 6
    EURO_POOL, EURO_SIZE = 50, 5
    STAR_POOL, STAR_SIZE = 12, 2

    def __init__(self, database: LottomatDatabase) -> None:
        self.database = database

    @staticmethod
    def collect_draws(database: LottomatDatabase, all_records: list[Record] | None = None) -> dict[str, list[Draw]]:
        """Zbiera losowania (liczby, gwiazdy) z kuponów z wynikiem oraz z samych wyników losowań,
        od najnowszych. Identyczne wyniki (np. kilka kuponów na to samo losowanie) liczone są jako jedno.
        """
        records = database.get_all_records() if all_records is None else all_records
        raw: list[tuple[str, str, str, str | None]] = []
        for rec in records:
            if rec[4]:
                raw.append((rec[6][:10], rec[1], rec[4], rec[5]))
        for _, game, draw_date, numbers, extra in database.get_draw_results():
            raw.append((draw_date[:10], game, numbers, extra))
        raw.sort(key=lambda item: item[0], reverse=True)

        draws: dict[str, list[Draw]] = {"Lotto": [], "Eurojackpot": []}
        seen: set[tuple[str, str, str]] = set()
        for _, game, numbers, extra in raw:
            if game not in draws or not numbers:
                continue
            main = ",".join(sorted((n.strip() for n in numbers.split(",") if n.strip()), key=int))
            stars = ",".join(sorted((n.strip() for n in extra.split(",") if n.strip()), key=int)) if extra else ""
            key = (game, main, stars)
            if key in seen:
                continue
            seen.add(key)
            draws[game].append((main, stars or None))
        return draws

    def generate_lotto(self) -> list[int] | None:
        """Zestaw Lotto (6 z 49) albo None, gdy w bazie jest za mało losowań"""
        draws = self.collect_draws(self.database)["Lotto"]
        if len(draws) < self.MIN_DRAWS:
            return None
        history = [self._parse(main) for main, _ in draws]
        return self._pick_set(history, self.LOTTO_POOL, self.LOTTO_SIZE)

    def generate_eurojackpot(self) -> tuple[list[int], list[int]] | None:
        """Zestaw Eurojackpot (5 z 50 + 2 z 12) albo None, gdy w bazie jest za mało losowań"""
        draws = self.collect_draws(self.database)["Eurojackpot"]
        main_history = [self._parse(main) for main, stars in draws if stars]
        star_history = [self._parse(stars) for _, stars in draws if stars]
        if len(star_history) < self.MIN_DRAWS:
            return None
        main = self._pick_set(main_history, self.EURO_POOL, self.EURO_SIZE)
        stars = self._pick_set(star_history, self.STAR_POOL, self.STAR_SIZE)
        return main, stars

    @staticmethod
    def _parse(numbers: str) -> list[int]:
        return sorted(int(n) for n in numbers.split(",") if n.strip())

    def _number_weights(self, history: list[list[int]], pool: int, size: int) -> dict[int, float]:
        """Waga liczby = częstotliwość względem oczekiwanej + zaległość względem średniego odstępu.
        `history` jest uporządkowana od najnowszego losowania.
        """
        total = len(history)
        counts = Counter(num for draw in history for num in draw)
        expected_hits = total * size / pool
        expected_gap = pool / size
        weights: dict[int, float] = {}
        for num in range(1, pool + 1):
            freq_ratio = (counts[num] + 1) / (expected_hits + 1)
            gap = next((i for i, draw in enumerate(history) if num in draw), total)
            overdue_ratio = min(gap / expected_gap, self.OVERDUE_CAP)
            weights[num] = max(0.1, self.FREQ_WEIGHT * freq_ratio + self.OVERDUE_WEIGHT * overdue_ratio)
        return weights

    @staticmethod
    def _structure(numbers: list[int], pool: int) -> tuple[int, int, int, int]:
        """(liczba nieparzystych, liczba niskich, suma, liczba par kolejnych liczb)"""
        odd = sum(1 for n in numbers if n % 2)
        low = sum(1 for n in numbers if n <= pool // 2)
        consecutive = sum(1 for a, b in zip(numbers, numbers[1:]) if b - a == 1)
        return odd, low, sum(numbers), consecutive

    def _build_profile(self, history: list[list[int]], pool: int) -> Profile:
        """Typowa struktura zestawu wyznaczona z historii losowań"""
        structures = [self._structure(draw, pool) for draw in history]
        total = len(structures)

        def typical(index: int) -> frozenset[int]:
            counts = Counter(s[index] for s in structures)
            common = frozenset(v for v, c in counts.items() if c / total >= self.MIN_SHARE)
            return common or frozenset(counts)

        sums = sorted(s[2] for s in structures)
        consecutives = sorted(s[3] for s in structures)
        low_idx, high_idx = int(0.1 * (total - 1)), round(0.9 * (total - 1))
        return typical(0), typical(1), sums[low_idx], sums[high_idx], consecutives[high_idx]

    def _violations(self, numbers: list[int], profile: Profile, pool: int) -> int:
        """Liczba kryteriów strukturalnych, których zestaw nie spełnia"""
        odd_ok, low_ok, sum_min, sum_max, max_consecutive = profile
        odd, low, total, consecutive = self._structure(numbers, pool)
        failed = 0
        failed += odd not in odd_ok
        failed += low not in low_ok
        failed += not (sum_min <= total <= sum_max)
        failed += consecutive > max_consecutive
        return failed

    @staticmethod
    def _sample(weights: dict[int, float], size: int) -> list[int]:
        """Losowanie bez zwracania z wagami (metoda Efraimidisa–Spirakisa)"""
        keyed = sorted(weights, key=lambda n: random.random() ** (1.0 / weights[n]), reverse=True)
        return sorted(keyed[:size])

    @staticmethod
    def _pair_counts(history: list[list[int]]) -> Counter[tuple[int, int]]:
        return Counter(pair for draw in history for pair in combinations(draw, 2))

    def _pick_set(self, history: list[list[int]], pool: int, size: int) -> list[int]:
        weights = self._number_weights(history, pool, size)
        profile = self._build_profile(history, pool)

        shortlist: list[list[int]] = []
        fallback_violations = size + 4
        fallback = self._sample(weights, size)
        for _ in range(self.MAX_ATTEMPTS):
            candidate = self._sample(weights, size)
            violations = self._violations(candidate, profile, pool)
            if violations == 0:
                shortlist.append(candidate)
                if len(shortlist) >= self.SHORTLIST_SIZE:
                    break
            elif violations < fallback_violations:
                fallback_violations, fallback = violations, candidate

        if not shortlist:
            return fallback
        pair_counts = self._pair_counts(history)
        scores = [
            1.0 + sum(pair_counts[pair] for pair in combinations(candidate, 2)) / len(history)
            for candidate in shortlist
        ]
        return random.choices(shortlist, weights=scores, k=1)[0]
