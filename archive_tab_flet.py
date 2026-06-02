import flet as ft  # type: ignore
from database import LottomatDatabase
from datetime import datetime
from typing import Any


class ArchiveTabFlet:
    # Kolory tła rekordów
    LOTTO_BG_LIGHT = "#EEF2FF"
    EURO_BG_LIGHT = "#F0FDF4"
    LOTTO_BG_DARK = "#1a2332"
    EURO_BG_DARK = "#1a2b23"
    MATCH_HIGHLIGHT_COLOR = "#F59E0B"

    def __init__(self, page: ft.Page, database: LottomatDatabase):
        self.page = page
        self.database = database
        self.filter_value = "Wszystkie"

        # Nagłówek listy rekordów (stały, nie scrolluje)
        self.records_header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(ft.Text("ID",              size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), width=32),
                    ft.Container(ft.Text("Gra",             size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), width=95),
                    ft.Container(ft.Text("Twoje liczby",    size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), expand=3),
                    ft.Container(ft.Text("Dodatkowe",       size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), expand=2),
                    ft.Container(ft.Text("Wynik losowania", size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), expand=2),
                    ft.Container(ft.Text("Wynik extra",     size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), expand=1),
                    ft.Container(ft.Text("Trafność",        size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), expand=2),
                    ft.Container(ft.Text("Wygrana",         size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), expand=1),
                    ft.Container(ft.Text("Data",            size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), width=125),
                    ft.Container(ft.Text("Akcje",           size=11, weight=ft.FontWeight.BOLD, color="#6b7280"), width=105),
                ],
                spacing=8,
            ),
            bgcolor="#f1f5f9",
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
            padding=ft.Padding.symmetric(horizontal=10, vertical=10),
        )

        # Lista rekordów (scrolluje niezależnie od nagłówka)
        self.records_list = ft.ListView(spacing=1, expand=True)

        self.stats_text = ft.Text("Rekordów w archiwum: 0", size=13)
        self.stats_column = ft.Column([], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
    
    def _lotto_prize_tier(self, matched: int) -> tuple[str, str]:
        """Zwraca (nazwa stopnia, kolor) dla Lotto. Pusty string = brak wygranej."""
        tiers = {6: ("szóstka", "#15803d"), 5: ("piątka", "#1d4ed8"),
                 4: ("czwórka", "#7c3aed"), 3: ("trójka", "#92400e")}
        return tiers.get(matched, ("", ""))

    def _eurojackpot_prize_tier(self, matched_main: int, matched_extra: int) -> tuple[str, str]:
        """Zwraca (nazwa stopnia, kolor) dla Eurojackpot. Pusty string = brak wygranej."""
        tiers: dict[tuple[int, int], tuple[str, str]] = {
            (5, 2): ("I (5+2)",  "#7f1d1d"),
            (5, 1): ("II (5+1)", "#991b1b"),
            (5, 0): ("III (5+0)","#15803d"),
            (4, 2): ("IV (4+2)", "#1d4ed8"),
            (4, 1): ("V (4+1)",  "#1e40af"),
            (3, 2): ("VI (3+2)", "#7c3aed"),
            (4, 0): ("VII (4+0)","#5b21b6"),
            (2, 2): ("VIII (2+2)","#92400e"),
            (3, 1): ("IX (3+1)", "#b45309"),
            (3, 0): ("X (3+0)",  "#a16207"),
            (1, 2): ("XI (1+2)", "#374151"),
            (2, 1): ("XII (2+1)","#4b5563"),
        }
        return tiers.get((matched_main, matched_extra), ("", ""))

    def _refresh_stats(self) -> None:
        """Aktualizacja panelu statystyk na podstawie wszystkich danych z bazy"""
        self.stats_column.controls.clear()
        all_records = self.database.get_all_records()

        # --- Win Ratio (lewa kolumna) ---
        win_ratio_controls: list[ft.Control] = [
            ft.Text("📊 Win Ratio", size=15, weight=ft.FontWeight.BOLD),
            ft.Container(height=6),
        ]

        for game_type, color in (("Lotto", "#ef4444"), ("Eurojackpot", "#3b82f6")):
            icon = "🔴" if game_type == "Lotto" else "🔵"
            game_recs = [r for r in all_records if r[1] == game_type]
            total = len(game_recs)
            with_result = [r for r in game_recs if r[4]]
            n_res = len(with_result)

            # Rankingi stopni wygranych (wyższy = lepsza wygrana)
            lotto_tier_rank: dict[str, int] = {"szóstka": 4, "piątka": 3, "czwórka": 2, "trójka": 1}
            euro_tier_rank: dict[str, int] = {
                "I (5+2)": 12, "II (5+1)": 11, "III (5+0)": 10, "IV (4+2)": 9,
                "V (4+1)": 8, "VI (3+2)": 7, "VII (4+0)": 6, "VIII (2+2)": 5,
                "IX (3+1)": 4, "X (3+0)": 3, "XI (1+2)": 2, "XII (2+1)": 1,
            }

            tier_counts: dict[str, dict[str, Any]] = {}
            wins = 0

            for rec in with_result:
                _, _, numbers, extra_numbers, actual_numbers, actual_extra_numbers, _, _, _, _ = rec
                act_nums = set(actual_numbers.split(",")) if actual_numbers else set()
                main_sets = numbers.split("|") if numbers else []
                extra_sets = extra_numbers.split("|") if extra_numbers else []

                # Najlepsza wygrana w tym rekordzie (spośród wszystkich zestawów)
                best_rank = 0
                best_tier_name = ""
                best_tier_color = ""

                for idx, s in enumerate(main_sets):
                    gen_nums = set(s.split(","))
                    if game_type == "Lotto":
                        tier_name, tier_color = self._lotto_prize_tier(len(gen_nums & act_nums))
                        rank = lotto_tier_rank.get(tier_name, 0)
                    else:
                        act_extra = set(actual_extra_numbers.split(",")) if actual_extra_numbers else set()
                        gen_extra = set(extra_sets[idx].split(",")) if idx < len(extra_sets) else set()
                        tier_name, tier_color = self._eurojackpot_prize_tier(
                            len(gen_nums & act_nums), len(gen_extra & act_extra)
                        )
                        rank = euro_tier_rank.get(tier_name, 0)
                    if rank > best_rank:
                        best_rank = rank
                        best_tier_name = tier_name
                        best_tier_color = tier_color

                if best_tier_name:
                    wins += 1
                    if best_tier_name not in tier_counts:
                        tier_counts[best_tier_name] = {"count": 0, "color": best_tier_color}
                    tier_counts[best_tier_name]["count"] += 1

            win_pct = wins / n_res * 100 if n_res > 0 else 0.0

            section: list[ft.Control] = [
                ft.Text(f"{icon} {game_type}", size=13, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(f"Kupony: {total}  |  Z wynikiem: {n_res}", size=11, color="#6b7280"),
                ft.Text(
                    f"Wygrane: {wins}/{n_res}  ({win_pct:.1f}%)",
                    size=12, weight=ft.FontWeight.W_500,
                    color="#15803d" if wins > 0 else "#6b7280",
                ),
            ]
            for tier_name, info in tier_counts.items():
                pct = info["count"] / n_res * 100 if n_res > 0 else 0.0
                section.append(
                    ft.Row([
                        ft.Container(
                            content=ft.Text(tier_name, size=10, color=info["color"]),
                            width=110,
                        ),
                        ft.Text(f"{info['count']}× ({pct:.1f}%)", size=10, color="#374151"),
                    ], spacing=4)
                )

            win_ratio_controls.append(
                ft.Row([
                    ft.Container(width=3, bgcolor=color, border_radius=2),
                    ft.Container(
                        content=ft.Column(section, spacing=3, tight=True),
                        expand=True,
                        padding=ft.Padding.only(left=8, top=4, bottom=4),
                    ),
                ], spacing=0)
            )
            win_ratio_controls.append(ft.Container(height=8))

        # --- Trafność ---
        win_ratio_controls.append(ft.Container(height=2, bgcolor="#e5e7eb"))
        win_ratio_controls.append(ft.Container(height=8))
        win_ratio_controls.append(
            ft.Text("🎯 Trafność", size=15, weight=ft.FontWeight.BOLD)
        )
        win_ratio_controls.append(ft.Container(height=6))

        # Lotto: zlicz 0..6 trafień (per zestaw – jeden rekord z 3 zestawami daje 3 punkty danych)
        lotto_hits: dict[int, int] = {i: 0 for i in range(7)}
        lotto_res = [r for r in all_records if r[1] == "Lotto" and r[4]]
        lotto_sets_total = 0
        for rec in lotto_res:
            _, _, numbers, _, actual_numbers, _, _, _, _, _ = rec
            act_nums = set(actual_numbers.split(",")) if actual_numbers else set()
            for s in (numbers.split("|") if numbers else []):
                gen_nums = set(s.split(",")) if s else set()
                lotto_hits[len(gen_nums & act_nums)] += 1
                lotto_sets_total += 1

        lotto_total = lotto_sets_total
        lotto_section: list[ft.Control] = [
            ft.Text("🔴 Lotto", size=12, weight=ft.FontWeight.BOLD, color="#ef4444"),
        ]
        for k in range(6, -1, -1):
            cnt = lotto_hits[k]
            if cnt == 0 and k == 0:
                continue
            pct = cnt / lotto_total * 100 if lotto_total > 0 else 0.0
            lotto_section.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(f"{k}/6", size=10, color="#374151"),
                        width=28,
                    ),
                    ft.Text(f"{cnt}×", size=10, weight=ft.FontWeight.W_500, color="#111827"),
                    ft.Text(f"({pct:.0f}%)", size=10, color="#6b7280"),
                ], spacing=6)
            )

        win_ratio_controls.append(
            ft.Row([
                ft.Container(width=3, bgcolor="#ef4444", border_radius=2),
                ft.Container(
                    content=ft.Column(lotto_section, spacing=3, tight=True),
                    expand=True,
                    padding=ft.Padding.only(left=8, top=4, bottom=4),
                ),
            ], spacing=0)
        )
        win_ratio_controls.append(ft.Container(height=8))

        # Eurojackpot: zlicz (main, extra) trafień (per zestaw)
        euro_hits: dict[tuple[int, int], int] = {}
        euro_res = [r for r in all_records if r[1] == "Eurojackpot" and r[4]]
        euro_sets_total = 0
        for rec in euro_res:
            _, _, numbers, extra_numbers, actual_numbers, actual_extra_numbers, _, _, _, _ = rec
            act_nums = set(actual_numbers.split(",")) if actual_numbers else set()
            act_extra = set(actual_extra_numbers.split(",")) if actual_extra_numbers else set()
            main_sets = numbers.split("|") if numbers else []
            extra_sets = extra_numbers.split("|") if extra_numbers else []
            for idx, s in enumerate(main_sets):
                gen_nums = set(s.split(","))
                gen_extra = set(extra_sets[idx].split(",")) if idx < len(extra_sets) else set()
                key = (len(gen_nums & act_nums), len(gen_extra & act_extra))
                euro_hits[key] = euro_hits.get(key, 0) + 1
                euro_sets_total += 1

        euro_total = euro_sets_total
        euro_section: list[ft.Control] = [
            ft.Text("🔵 Eurojackpot", size=12, weight=ft.FontWeight.BOLD, color="#3b82f6"),
        ]
        for key in sorted(euro_hits.keys(), reverse=True):
            cnt = euro_hits[key]
            pct = cnt / euro_total * 100 if euro_total > 0 else 0.0
            euro_section.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(f"{key[0]}/5+{key[1]}/2", size=10, color="#374151"),
                        width=50,
                    ),
                    ft.Text(f"{cnt}×", size=10, weight=ft.FontWeight.W_500, color="#111827"),
                    ft.Text(f"({pct:.0f}%)", size=10, color="#6b7280"),
                ], spacing=6)
            )

        win_ratio_controls.append(
            ft.Row([
                ft.Container(width=3, bgcolor="#3b82f6", border_radius=2),
                ft.Container(
                    content=ft.Column(euro_section, spacing=3, tight=True),
                    expand=True,
                    padding=ft.Padding.only(left=8, top=4, bottom=4),
                ),
            ], spacing=0)
        )
        win_ratio_controls.append(ft.Container(height=8))

        # --- Finanse ---
        win_ratio_controls.append(ft.Container(height=2, bgcolor="#e5e7eb"))
        win_ratio_controls.append(ft.Container(height=8))
        win_ratio_controls.append(
            ft.Text("💰 Finanse", size=15, weight=ft.FontWeight.BOLD)
        )
        win_ratio_controls.append(ft.Container(height=6))

        lotto_price_label = self.database.get_lotto_price()
        euro_price_label = self.database.get_eurojackpot_price()

        for game_type, color, icon in (
            ("Lotto", "#ef4444", "🔴"),
            ("Eurojackpot", "#3b82f6", "🔵"),
        ):
            game_recs_fin = [r for r in all_records if r[1] == game_type]
            n_coupons = len(game_recs_fin)
            n_sets = sum(
                len(r[2].split("|")) if r[2] else 1
                for r in game_recs_fin
            )
            spent = sum(
                (len(r[2].split("|")) if r[2] else 1) * (r[9] if r[9] is not None else (lotto_price_label if game_type == "Lotto" else euro_price_label))
                for r in game_recs_fin
            )
            won_pln = sum(r[7] for r in game_recs_fin if r[7] is not None and r[8] == "PLN")
            won_eur = sum(r[7] for r in game_recs_fin if r[7] is not None and r[8] == "EUR")
            balance_pln = won_pln - spent

            fin_section: list[ft.Control] = [
                ft.Text(f"{icon} {game_type}", size=13, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(f"Kupony: {n_coupons}  |  Zakłady: {n_sets}", size=11, color="#6b7280"),
                ft.Text(f"Wydano: {spent:,.2f} PLN", size=11, color="#374151"),
            ]
            if won_pln > 0 or won_eur > 0:
                if won_pln > 0:
                    fin_section.append(ft.Text(f"Wygrano: {won_pln:,.2f} PLN", size=11, color="#15803d"))
                if won_eur > 0:
                    fin_section.append(ft.Text(f"Wygrano: {won_eur:,.2f} EUR", size=11, color="#15803d"))
            else:
                fin_section.append(ft.Text("Wygrano: 0,00 PLN", size=11, color="#6b7280"))
            fin_section.append(
                ft.Text(
                    f"Bilans PLN: {balance_pln:+,.2f}",
                    size=12, weight=ft.FontWeight.W_500,
                    color="#15803d" if balance_pln >= 0 else "#b91c1c",
                )
            )
            win_ratio_controls.append(
                ft.Row([
                    ft.Container(width=3, bgcolor=color, border_radius=2),
                    ft.Container(
                        content=ft.Column(fin_section, spacing=3, tight=True),
                        expand=True,
                        padding=ft.Padding.only(left=8, top=4, bottom=4),
                    ),
                ], spacing=0)
            )
            win_ratio_controls.append(ft.Container(height=8))

        # Łączne finanse
        total_spent = sum(
            (len(r[2].split("|")) if r[2] else 1) * (r[9] if r[9] is not None else (lotto_price_label if r[1] == "Lotto" else euro_price_label))
            for r in all_records
        )
        total_won_pln = sum(r[7] for r in all_records if r[7] is not None and r[8] == "PLN")
        total_won_eur = sum(r[7] for r in all_records if r[7] is not None and r[8] == "EUR")
        total_balance = total_won_pln - total_spent

        summary: list[ft.Control] = [
            ft.Text("📊 Łącznie", size=13, weight=ft.FontWeight.BOLD),
            ft.Text(f"Wydano: {total_spent:,.2f} PLN", size=11, color="#374151"),
        ]
        if total_won_pln > 0:
            summary.append(ft.Text(f"Wygrano: {total_won_pln:,.2f} PLN", size=11, color="#15803d"))
        if total_won_eur > 0:
            summary.append(ft.Text(f"Wygrano: {total_won_eur:,.2f} EUR", size=11, color="#15803d"))
        if total_won_pln == 0 and total_won_eur == 0:
            summary.append(ft.Text("Wygrano: 0,00 PLN", size=11, color="#6b7280"))
        summary.append(
            ft.Text(
                f"Bilans PLN: {total_balance:+,.2f}",
                size=12, weight=ft.FontWeight.BOLD,
                color="#15803d" if total_balance >= 0 else "#b91c1c",
            )
        )
        win_ratio_controls.append(
            ft.Row([
                ft.Container(width=3, bgcolor="#6366f1", border_radius=2),
                ft.Container(
                    content=ft.Column(summary, spacing=3, tight=True),
                    expand=True,
                    padding=ft.Padding.only(left=8, top=4, bottom=4),
                ),
            ], spacing=0)
        )

        # --- Najczęstsze liczby (prawa kolumna) ---
        freq: dict[str, dict[str, dict[str, int]]] = {
            "Lotto":       {"main": {}},
            "Eurojackpot": {"main": {}, "extra": {}},
        }
        draws: dict[str, int] = {"Lotto": 0, "Eurojackpot": 0}

        for rec in all_records:
            _, rec_game, _, _, actual_numbers, actual_extra_numbers, _, _, _, _ = rec
            if not actual_numbers or rec_game not in freq:
                continue
            draws[rec_game] += 1
            for num in actual_numbers.split(","):
                num = num.strip()
                if num:
                    freq[rec_game]["main"][num] = freq[rec_game]["main"].get(num, 0) + 1
            if rec_game == "Eurojackpot" and actual_extra_numbers:
                for num in actual_extra_numbers.split(","):
                    num = num.strip()
                    if num:
                        freq["Eurojackpot"]["extra"][num] = freq["Eurojackpot"]["extra"].get(num, 0) + 1

        freq_sections: list[tuple[str, str, str, str]] = [
            ("🔴 Lotto – główne", "Lotto", "main", "#ef4444"),
            ("🔵 Eurojackpot – główne", "Eurojackpot", "main", "#3b82f6"),
            ("⭐ Eurojackpot – gwiazdy", "Eurojackpot", "extra", "#fbbf24"),
        ]

        freq_controls: list[ft.Control] = [
            ft.Text("🔢 Najczęstsze liczby", size=15, weight=ft.FontWeight.BOLD),
            ft.Container(height=6),
        ]

        for label, game, key, color in freq_sections:
            counts = freq[game][key]
            if not counts:
                continue
            total_draws = draws[game]
            sorted_nums = sorted(counts.items(), key=lambda kv: -kv[1])[:10]
            max_c = sorted_nums[0][1]

            freq_rows: list[ft.Control] = [
                ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=color),
            ]
            for num_str, count in sorted_nums:
                pct = count / total_draws * 100 if total_draws > 0 else 0.0
                bar_w = max(4, int(count / max_c * 150))
                freq_rows.append(
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(num_str.rjust(2), size=10, color="#111827"),
                                width=22,
                            ),
                            ft.Container(
                                bgcolor=color, width=bar_w, height=8,
                                border_radius=3, opacity=0.65,
                            ),
                            ft.Text(f"{count}× ({pct:.0f}%)", size=10, color="#6b7280"),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )

            freq_controls.append(
                ft.Container(
                    content=ft.Column(freq_rows, spacing=3, tight=True),
                    padding=ft.Padding.only(top=4, bottom=8),
                )
            )

        # --- Składanie obu kolumn obok siebie ---
        self.stats_column.controls.append(
            ft.Row(
                [
                    ft.Column(win_ratio_controls, spacing=0, tight=True, expand=True),
                    ft.Container(width=1, bgcolor="#e5e7eb"),
                    ft.Column(freq_controls, spacing=0, tight=True, expand=True,
                               scroll=ft.ScrollMode.AUTO),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=True,
            )
        )

    def format_numbers_with_highlights(self, numbers_str: str, matches: set[str]) -> ft.Row:  # type: ignore
        """Formatuje liczby z wizualnym oznaczeniem trafień w złotych kółeczkach"""
        if not numbers_str:
            return ft.Row([ft.Text("-", size=12)])
        
        nums = numbers_str.split(",")
        controls: list[ft.Control] = []
        for i, num in enumerate(nums):
            num = num.strip()
            if num in matches:
                # Trafiona liczba w złotym kółku
                controls.append(  # type: ignore
                    ft.Container(
                        content=ft.Text(num, size=10, weight=ft.FontWeight.BOLD, color="white"),
                        bgcolor=self.MATCH_HIGHLIGHT_COLOR,
                        width=24,
                        height=24,
                        border_radius=12,
                        alignment=ft.alignment.Alignment.CENTER,
                    )
                )
            else:
                # Zwykła liczba
                controls.append(ft.Text(num, size=12))  # type: ignore
            
            # Dodaj przecinek i spację między liczbami (ale nie po ostatniej)
            if i < len(nums) - 1:
                controls.append(ft.Text(", ", size=12))  # type: ignore
        
        return ft.Row(controls, spacing=2, wrap=False)
    
    def _build_sets_display(
        self,
        sets: list[str],
        act_nums: set[str],
    ) -> ft.Control:
        """Buduje widget wyświetlający jeden lub wiele zestawów liczb z podświetlonymi trafieniami."""
        if not sets:
            return ft.Row([ft.Text("-", size=12)])
        if len(sets) == 1:
            matches = set(sets[0].split(",")) & act_nums
            return self.format_numbers_with_highlights(sets[0], matches)
        rows: list[ft.Control] = []
        for idx, s in enumerate(sets):
            matches = set(s.split(",")) & act_nums
            rows.append(
                ft.Row(
                    [
                        ft.Text(f"{idx + 1}.", size=10, color="#9ca3af", width=16),
                        self.format_numbers_with_highlights(s, matches),
                    ],
                    spacing=2,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return ft.Column(rows, spacing=3, tight=True)

    def _build_accuracy_display(
        self,
        game_type: str,
        main_sets: list[str],
        extra_sets: list[str],
        act_nums: set[str],
        act_extra: set[str],
    ) -> ft.Control:
        """Buduje widget trafności dla jednego lub wielu zestawów."""
        if not main_sets:
            return ft.Text("-", size=12, color="#6b7280")

        def lotto_acc(s: str) -> tuple[str, str]:
            hits = len(set(s.split(",")) & act_nums)
            tier_name, tier_color = self._lotto_prize_tier(hits)
            return (tier_name if tier_name else f"{hits}/6"), (tier_color if tier_color else "#6b7280")

        def euro_acc(idx: int) -> tuple[str, str]:
            hits_m = len(set(main_sets[idx].split(",")) & act_nums)
            hits_e = len(set(extra_sets[idx].split(",")) & act_extra) if idx < len(extra_sets) else 0
            tier_name, tier_color = self._eurojackpot_prize_tier(hits_m, hits_e)
            return (tier_name if tier_name else f"{hits_m}+{hits_e}"), (tier_color if tier_color else "#6b7280")

        if len(main_sets) == 1:
            text, color = lotto_acc(main_sets[0]) if game_type == "Lotto" else euro_acc(0)
            return ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color=color)

        rows: list[ft.Control] = []
        for idx in range(len(main_sets)):
            text, color = lotto_acc(main_sets[idx]) if game_type == "Lotto" else euro_acc(idx)
            rows.append(
                ft.Row(
                    [
                        ft.Text(f"{idx + 1}.", size=10, color="#9ca3af", width=16),
                        ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=color),
                    ],
                    spacing=2,
                )
            )
        return ft.Column(rows, spacing=3, tight=True)

    def _record_has_prize_tier(
        self,
        game_type: str,
        main_sets: list[str],
        extra_sets: list[str],
        act_nums: set[str],
        act_extra: set[str],
    ) -> bool:
        """Sprawdza czy co najmniej jeden zestaw w rekordzie trafia w stopień wygranej"""
        for idx, s in enumerate(main_sets):
            if game_type == "Lotto":
                tier_name, _ = self._lotto_prize_tier(len(set(s.split(",")) & act_nums))
            else:
                hits_m = len(set(s.split(",")) & act_nums)
                hits_e = len(set(extra_sets[idx].split(",")) & act_extra) if idx < len(extra_sets) else 0
                tier_name, _ = self._eurojackpot_prize_tier(hits_m, hits_e)
            if tier_name:
                return True
        return False

    def refresh_archive(self):
        """Odświeżenie listy rekordów"""
        from database import Record  # type: ignore
        records: list[Record]
        if self.filter_value == "Wszystkie":
            records = self.database.get_all_records()
        else:
            records = self.database.get_records_by_game(self.filter_value)

        # Czyszczenie listy rekordów
        self.records_list.controls.clear()

        # Wypełnienie listy
        for record in records:
            record_id, game_type, numbers, extra_numbers, actual_numbers, actual_extra_numbers, created_date, prize_amount, prize_currency, ticket_price = record

            # Parsowanie zestawów (separator '|'; stare rekordy bez '|' = jeden zestaw)
            main_sets: list[str] = numbers.split("|") if numbers else []
            extra_sets: list[str] = extra_numbers.split("|") if extra_numbers else []
            act_nums: set[str] = set(actual_numbers.split(",")) if actual_numbers else set()
            act_extra: set[str] = set(actual_extra_numbers.split(",")) if actual_extra_numbers else set()

            # Wyświetlanie zestawów z podświetleniem trafień
            numbers_display = self._build_sets_display(main_sets, act_nums)
            extra_display = self._build_sets_display(extra_sets, act_extra) if extra_sets else ft.Row([ft.Text("-", size=12)])

            # Wynik losowania
            result_display = actual_numbers.replace(",", ", ") if actual_numbers else "-"
            result_extra_display = actual_extra_numbers.replace(",", ", ") if actual_extra_numbers else "-"

            # Trafność (osobno dla każdego zestawu, jeśli podano wynik)
            if actual_numbers:
                accuracy_display = self._build_accuracy_display(
                    game_type, main_sets, extra_sets, act_nums, act_extra
                )
            else:
                accuracy_display: ft.Control = ft.Text("-", size=12, color="#6b7280")

            # Wyświetlanie wygranej
            has_prize_tier = bool(actual_numbers) and self._record_has_prize_tier(
                game_type, main_sets, extra_sets, act_nums, act_extra
            )
            if prize_amount is not None and prize_currency is not None:
                prize_display: ft.Control = ft.Text(
                    f"{prize_amount:,.2f} {prize_currency}",
                    size=11, weight=ft.FontWeight.BOLD, color="#15803d",
                )
            elif has_prize_tier:
                prize_display = ft.Text("— dodaj →", size=10, color="#b45309", italic=True)
            else:
                prize_display = ft.Text("-", size=12, color="#9ca3af")

            # Formatowanie daty
            try:
                date_obj = datetime.fromisoformat(created_date)
                date_display = date_obj.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                date_display = created_date

            # Kolor tła i kolor nazwy gry
            if self.page.theme_mode == ft.ThemeMode.DARK:
                bg_color = self.LOTTO_BG_DARK if game_type == "Lotto" else self.EURO_BG_DARK
            else:
                bg_color = self.LOTTO_BG_LIGHT if game_type == "Lotto" else self.EURO_BG_LIGHT
            game_color = "#ef4444" if game_type == "Lotto" else "#3b82f6"

            # Wiersz jako Container – wysokość dopasowuje się automatycznie do zawartości
            row_widget = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            ft.Text(str(record_id), size=12, color="#374151"),
                            width=32,
                        ),
                        ft.Container(
                            ft.Text(game_type, size=12, weight=ft.FontWeight.BOLD, color=game_color),
                            width=95,
                        ),
                        ft.Container(numbers_display, expand=3),
                        ft.Container(extra_display, expand=2),
                        ft.Container(ft.Text(result_display, size=12), expand=2),
                        ft.Container(ft.Text(result_extra_display, size=12), expand=1),
                        ft.Container(accuracy_display, expand=2),
                        ft.Container(prize_display, expand=1),
                        ft.Container(ft.Text(date_display, size=11, color="#6b7280"), width=125),
                        ft.Container(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                        icon_color="#1d4ed8",
                                        tooltip="Dodaj wynik",
                                        data={"id": record_id, "type": game_type},
                                        on_click=self.handle_add_result,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ATTACH_MONEY,
                                        icon_color="#15803d",
                                        tooltip="Wpisz kwotę wygranej",
                                        data={"id": record_id, "type": game_type},
                                        on_click=self.handle_add_prize,
                                        visible=has_prize_tier,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color="#b91c1c",
                                        tooltip="Usuń",
                                        data=record_id,
                                        on_click=self.handle_delete,
                                    ),
                                ],
                                spacing=0,
                            ),
                            width=105,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor=bg_color,
                border_radius=6,
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            )
            self.records_list.controls.append(row_widget)  # type: ignore

        # Aktualizuj statystyki
        self.stats_text.value = f"Rekordów w archiwum: {len(records)}"
        self._refresh_stats()
        self.page.update()  # type: ignore
    
    def filter_changed(self, e: Any) -> None:  # type: ignore
        """Zmiana filtra"""
        self.filter_value = e.control.value
        self.refresh_archive()
    
    def handle_add_result(self, e: Any) -> None:  # type: ignore
        """Handler dla przycisku dodaj wynik"""
        data = e.control.data
        self.add_actual_result(data["id"], data["type"])
    
    def handle_delete(self, e: Any) -> None:  # type: ignore
        """Handler dla przycisku usuń"""
        record_id = e.control.data
        self.delete_record(record_id)

    def handle_add_prize(self, e: Any) -> None:  # type: ignore
        """Handler dla przycisku wpisz kwotę wygranej"""
        data = e.control.data
        self.add_prize_dialog(data["id"], data["type"])
    
    def clear_archive(self, e: Any) -> None:  # type: ignore
        """Wyczyszczenie całego archiwum"""
        def confirm_clear(e: Any) -> None:  # type: ignore
            self.database.clear_all()
            self.refresh_archive()
            dialog.open = False
            self.page.update()  # type: ignore
            self.show_snackbar("Archiwum wyczyszczone!", "#15803d")
        
        def cancel_clear(e: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Potwierdzenie"),
            content=ft.Text("Czy na pewno chcesz usunąć wszystkie rekordy z archiwum?\nTej operacji nie można cofnąć!"),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_clear),
                ft.TextButton("Usuń wszystko", on_click=confirm_clear, style=ft.ButtonStyle(color="#b91c1c")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore
    
    def delete_record(self, record_id: int) -> None:
        """Usunięcie wybranego rekordu"""
        def confirm_delete(e: Any) -> None:  # type: ignore
            self.database.delete_record(record_id)
            self.refresh_archive()
            dialog.open = False
            self.page.update()  # type: ignore
            self.show_snackbar("Rekord usunięty!", "#15803d")
        
        def cancel_delete(e: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Potwierdzenie"),
            content=ft.Text(f"Czy na pewno chcesz usunąć rekord #{record_id}?"),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_delete),
                ft.TextButton("Usuń", on_click=confirm_delete, style=ft.ButtonStyle(color="#b91c1c")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore
    
    def add_actual_result(self, record_id: int, game_type: str) -> None:
        """Dodanie faktycznego wyniku losowania"""
        main_entry = ft.TextField(  # type: ignore
            label="Liczby główne" if game_type == "Eurojackpot" else "Liczby (oddzielone spacjami)",
            hint_text="Przykład: 1 12 23 34 45 49",
            width=400,
        )
        
        extra_entry = None
        if game_type == "Eurojackpot":
            extra_entry = ft.TextField(  # type: ignore
                label="Gwiazdy (oddzielone spacjami)",
                hint_text="Przykład: 3 7",
                width=400,
            )
        
        def save_result(e: Any) -> None:  # type: ignore
            try:
                # Pobierz i waliduj liczby główne
                main_text = (main_entry.value or "").strip()
                main_nums = [int(x) for x in main_text.split()]
                
                if game_type == "Lotto":
                    if len(main_nums) != 6:
                        self.show_snackbar("Lotto wymaga dokładnie 6 liczb!", "#b91c1c")
                        return
                    actual_main = ",".join(str(x) for x in sorted(main_nums))
                    actual_extra = None
                else:  # Eurojackpot
                    if len(main_nums) != 5:
                        self.show_snackbar("Eurojackpot wymaga dokładnie 5 liczb głównych!", "#b91c1c")
                        return
                    
                    assert extra_entry is not None
                    extra_text = (extra_entry.value or "").strip()
                    extra_nums = [int(x) for x in extra_text.split()]
                    
                    if len(extra_nums) != 2:
                        self.show_snackbar("Eurojackpot wymaga dokładnie 2 gwiazd!", "#b91c1c")
                        return
                    
                    actual_main = ",".join(str(x) for x in sorted(main_nums))
                    actual_extra = ",".join(str(x) for x in sorted(extra_nums))
                
                # Zapisz do bazy
                self.database.update_actual_result(record_id, actual_main, actual_extra)
                self.refresh_archive()
                dialog.open = False
                self.page.update()  # type: ignore
                self.show_snackbar("Faktyczny wynik dodany! Trafności obliczone automatycznie!", "#15803d")
                
            except ValueError:
                self.show_snackbar("Wprowadź poprawne liczby całkowite!", "#b91c1c")
        
        def cancel_dialog(e: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore
        
        # Zawartość dialogu
        content_items: list[ft.Control] = [
            ft.Text(f"Wprowadź faktyczny wynik losowania {game_type}", size=16, weight=ft.FontWeight.BOLD),  # type: ignore
            ft.Container(height=10),  # type: ignore
            main_entry,
        ]
        
        if extra_entry:
            content_items.append(ft.Container(height=10))  # type: ignore
            content_items.append(extra_entry)  # type: ignore
        
        dialog = ft.AlertDialog(  # type: ignore
            modal=True,
            title=ft.Text(f"Dodaj faktyczny wynik - {game_type}"),
            content=ft.Container(
                content=ft.Column(
                    content_items,
                    tight=True,
                    spacing=5,
                ),
                width=450,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_dialog),
                ft.Button("✓ Zapisz", on_click=save_result, bgcolor="#15803d", color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore
    
    def add_custom_numbers_dialog(self, e: Any) -> None:
        """Dialog do wprowadzenia własnych liczb do archiwum (obsługuje wiele zestawów)"""
        game_dropdown = ft.Dropdown(
            label="Wybierz grę",
            value="Lotto",
            options=[
                ft.dropdown.Option("Lotto"),
                ft.dropdown.Option("Eurojackpot"),
            ],
            width=250,
        )

        # Dynamiczna lista wpisów: każdy wpis to dict {"main": TextField, "extra": TextField | None}
        entries: list[dict] = []
        entries_column = ft.Column(spacing=8, tight=True, scroll=ft.ScrollMode.AUTO)

        def is_euro() -> bool:
            return game_dropdown.value == "Eurojackpot"

        def make_entry_row(idx: int) -> None:
            main_f = ft.TextField(
                label=f"Zestaw {idx + 1} – " + ("główne (5 z 1-50)" if is_euro() else "Lotto (6 z 1-49)"),
                hint_text="np. 1 12 23 34 45" if is_euro() else "np. 1 12 23 34 45 49",
                width=290,
            )
            extra_f: ft.TextField | None = None
            if is_euro():
                extra_f = ft.TextField(
                    label=f"Gwiazdy {idx + 1}",
                    hint_text="np. 3 7",
                    width=130,
                )
            entry: dict = {"main": main_f, "extra": extra_f}
            entries.append(entry)

            def on_delete(ev: Any, ent: dict = entry) -> None:  # type: ignore
                if len(entries) <= 1:
                    return
                i = entries.index(ent)
                entries.remove(ent)
                entries_column.controls.pop(i)
                # Przenumerowanie etykiet
                for j, en in enumerate(entries):
                    en["main"].label = f"Zestaw {j + 1} – " + ("główne (5 z 1-50)" if is_euro() else "Lotto (6 z 1-49)")
                    if en["extra"]:
                        en["extra"].label = f"Gwiazdy {j + 1}"
                self.page.update()  # type: ignore

            del_btn = ft.IconButton(
                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                icon_color="#ef4444",
                on_click=on_delete,
                icon_size=16,
                tooltip="Usuń zestaw",
            )
            row_controls: list[ft.Control] = [main_f]
            if extra_f:
                row_controls.append(extra_f)
            row_controls.append(del_btn)
            entries_column.controls.append(
                ft.Row(row_controls, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        def on_add_entry(ev: Any) -> None:  # type: ignore
            if len(entries) >= 10:
                self.show_snackbar("Maksymalnie 10 zestawów w kuponie!", "#b91c1c")
                return
            make_entry_row(len(entries))
            self.page.update()  # type: ignore

        def on_game_change(ev: Any) -> None:  # type: ignore
            entries.clear()
            entries_column.controls.clear()
            make_entry_row(0)
            self.page.update()  # type: ignore

        game_dropdown.on_select = on_game_change

        # Inicjalizacja pierwszego wpisu
        make_entry_row(0)

        def save_custom(ev: Any) -> None:  # type: ignore
            try:
                game = game_dropdown.value
                main_sets_list: list[list[int]] = []
                star_sets_list: list[list[int]] = []

                for i, ent in enumerate(entries):
                    main_text = (ent["main"].value or "").strip()
                    if not main_text:
                        continue  # Pomiń puste zestawy
                    main_nums = [int(x) for x in main_text.split()]

                    if game == "Lotto":
                        if len(main_nums) != 6:
                            self.show_snackbar(f"Zestaw {i + 1}: Lotto wymaga dokładnie 6 liczb!", "#b91c1c")
                            return
                        if any(n < 1 or n > 49 for n in main_nums):
                            self.show_snackbar(f"Zestaw {i + 1}: liczby muszą być z zakresu 1-49!", "#b91c1c")
                            return
                        if len(set(main_nums)) != 6:
                            self.show_snackbar(f"Zestaw {i + 1}: liczby nie mogą się powtarzać!", "#b91c1c")
                            return
                        main_sets_list.append(sorted(main_nums))
                    else:  # Eurojackpot
                        if len(main_nums) != 5:
                            self.show_snackbar(f"Zestaw {i + 1}: Eurojackpot wymaga 5 liczb głównych!", "#b91c1c")
                            return
                        if any(n < 1 or n > 50 for n in main_nums):
                            self.show_snackbar(f"Zestaw {i + 1}: liczby główne muszą być z zakresu 1-50!", "#b91c1c")
                            return
                        if len(set(main_nums)) != 5:
                            self.show_snackbar(f"Zestaw {i + 1}: liczby główne nie mogą się powtarzać!", "#b91c1c")
                            return
                        extra_text = (ent["extra"].value or "").strip() if ent["extra"] else ""
                        if not extra_text:
                            self.show_snackbar(f"Zestaw {i + 1}: wprowadź gwiazdy!", "#b91c1c")
                            return
                        extra_nums = [int(x) for x in extra_text.split()]
                        if len(extra_nums) != 2:
                            self.show_snackbar(f"Zestaw {i + 1}: Eurojackpot wymaga dokładnie 2 gwiazd!", "#b91c1c")
                            return
                        if any(n < 1 or n > 12 for n in extra_nums):
                            self.show_snackbar(f"Zestaw {i + 1}: gwiazdy muszą być z zakresu 1-12!", "#b91c1c")
                            return
                        if len(set(extra_nums)) != 2:
                            self.show_snackbar(f"Zestaw {i + 1}: gwiazdy nie mogą się powtarzać!", "#b91c1c")
                            return
                        main_sets_list.append(sorted(main_nums))
                        star_sets_list.append(sorted(extra_nums))

                if not main_sets_list:
                    self.show_snackbar("Wprowadź przynajmniej jeden zestaw liczb!", "#b91c1c")
                    return

                if game == "Lotto":
                    self.database.add_lotto_record(main_sets_list)
                else:
                    self.database.add_eurojackpot_record(main_sets_list, star_sets_list)

                self.refresh_archive()
                dialog.open = False
                self.page.update()  # type: ignore
                n = len(main_sets_list)
                label = f"{n} zestawy" if n in (2, 3, 4) else (f"{n} zestawów" if n > 4 else "1 zestaw")
                self.show_snackbar(f"Kupon {game} ({label}) dodany do archiwum!", "#15803d")

            except ValueError:
                self.show_snackbar("Wprowadź poprawne liczby całkowite oddzielone spacjami!", "#b91c1c")
            except Exception as ex:
                self.show_snackbar(f"Błąd: {ex}", "#b91c1c")

        def cancel_dialog(ev: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Dodaj własne liczby do archiwum"),
            content=ft.Container(
                content=ft.Column(
                    [
                        game_dropdown,
                        ft.Container(height=10),
                        entries_column,
                        ft.Container(height=6),
                        ft.TextButton(
                            "➕ Dodaj kolejny zestaw (maks. 10)",
                            on_click=on_add_entry,
                        ),
                    ],
                    tight=True,
                    spacing=0,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=520,
                height=420,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_dialog),
                ft.Button("✓ Archiwizuj kupon", on_click=save_custom, bgcolor="#15803d", color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore

    def add_prize_dialog(self, record_id: int, game_type: str) -> None:
        """Dialog do wpisania kwoty wygranej"""
        amount_field = ft.TextField(
            label="Kwota wygranej",
            hint_text="np. 150.00",
            width=220,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        currency_dropdown = ft.Dropdown(
            label="Waluta",
            value="PLN",
            options=[
                ft.dropdown.Option("PLN"),
                ft.dropdown.Option("EUR"),
            ],
            width=110,
        )

        def save_prize(e: Any) -> None:  # type: ignore
            try:
                text = (amount_field.value or "").strip().replace(",", ".")
                if not text:
                    self.show_snackbar("Wprowadź kwotę wygranej!", "#b91c1c")
                    return
                amount = float(text)
                if amount < 0:
                    self.show_snackbar("Kwota nie może być ujemna!", "#b91c1c")
                    return
                currency = currency_dropdown.value or "PLN"
                self.database.update_prize_amount(record_id, amount, currency)
                self.refresh_archive()
                dialog.open = False
                self.page.update()  # type: ignore
                self.show_snackbar(f"Wygrana {amount:,.2f} {currency} zapisana!", "#15803d")
            except ValueError:
                self.show_snackbar("Wprowadź poprawną kwotę (np. 150.00)!", "#b91c1c")

        def cancel_dialog(e: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Wpisz kwotę wygranej – #{record_id} ({game_type})"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Podaj kwotę wygranej i walutę.", size=13),
                        ft.Container(height=10),
                        ft.Row([amount_field, currency_dropdown], spacing=10),
                    ],
                    tight=True,
                    spacing=5,
                ),
                width=380,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_dialog),
                ft.Button("✓ Zapisz", on_click=save_prize, bgcolor="#15803d", color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore

    def show_price_settings_dialog(self, e: Any) -> None:  # type: ignore
        """Dialog do zmiany cen zakładów"""
        lotto_field = ft.TextField(
            label="Cena zakładu Lotto (PLN)",
            value=str(self.database.get_lotto_price()),
            width=220,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        euro_field = ft.TextField(
            label="Cena zakładu Eurojackpot (PLN)",
            value=str(self.database.get_eurojackpot_price()),
            width=220,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def save_prices(ev: Any) -> None:  # type: ignore
            try:
                lotto_val = float((lotto_field.value or "").strip().replace(",", "."))
                euro_val = float((euro_field.value or "").strip().replace(",", "."))
                if lotto_val <= 0 or euro_val <= 0:
                    self.show_snackbar("Ceny muszą być większe od zera!", "#b91c1c")
                    return
                self.database.set_setting("lotto_price", str(lotto_val))
                self.database.set_setting("eurojackpot_price", str(euro_val))
                self.refresh_archive()
                dialog.open = False
                self.page.update()  # type: ignore
                self.show_snackbar("Ceny zakładów zaktualizowane! Nowe kupony będą naliczane wg nowych cen.", "#15803d")
            except ValueError:
                self.show_snackbar("Wprowadź poprawne wartości liczbowe!", "#b91c1c")

        def cancel_dialog(ev: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ustawienia cen zakładów"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Zmiana cen dotyczy wyłącznie nowych kuponów.\n"
                            "Kupony już dodane zachowają cenę z momentu dodania.",
                            size=12, color="#6b7280",
                        ),
                        ft.Container(height=12),
                        lotto_field,
                        ft.Container(height=8),
                        euro_field,
                    ],
                    tight=True,
                    spacing=5,
                ),
                width=280,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_dialog),
                ft.Button("✓ Zapisz", on_click=save_prices, bgcolor="#6366f1", color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore

    def show_snackbar(self, message: str, color: str) -> None:
        """Pokazanie komunikatu snackbar"""
        self.page.show_dialog(  # type: ignore
            ft.SnackBar(
                content=ft.Text(message, color="white"),
                bgcolor=color,
                duration=2000,
            )
        )
    
    def build(self) -> ft.Container:
        """Budowanie interfejsu zakładki archiwum"""
        # Początkowe załadowanie danych
        self.refresh_archive()
        
        return ft.Container(
            content=ft.Column(
                [
                    # Nagłówek
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    "📚 Archiwum wylosowanych liczb",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color="#111827",
                                ),
                                ft.Row(
                                    [
                                        ft.Button(
                                            content="✏️ Własne liczby",
                                            on_click=self.add_custom_numbers_dialog,
                                            style=ft.ButtonStyle(
                                                bgcolor="#d1fae5",
                                                color="#065f46",
                                            ),
                                        ),
                                        ft.Button(
                                            content="⚙️ Ceny zakładów",
                                            on_click=self.show_price_settings_dialog,
                                            style=ft.ButtonStyle(
                                                bgcolor="#ede9fe",
                                                color="#4c1d95",
                                            ),
                                        ),
                                        ft.Button(
                                            content="🔄 Odśwież",
                                            on_click=lambda e: self.refresh_archive(),
                                            style=ft.ButtonStyle(
                                                bgcolor="#e0e7ff",
                                                color="#312e81",
                                            ),
                                        ),
                                        ft.Button(
                                            content="🗑️ Wyczyść archiwum",
                                            on_click=self.clear_archive,
                                            style=ft.ButtonStyle(
                                                bgcolor="#fee2e2",
                                                color="#7f1d1d",
                                            ),
                                        ),
                                    ],
                                    spacing=10,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=15,
                        border_radius=10,
                    ),
                    ft.Container(height=15),
                    
                    # Filtr
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text("Filtruj:", size=14, weight=ft.FontWeight.BOLD),
                                ft.Dropdown(
                                    value=self.filter_value,
                                    options=[
                                        ft.dropdown.Option("Wszystkie"),
                                        ft.dropdown.Option("Lotto"),
                                        ft.dropdown.Option("Eurojackpot"),
                                    ],
                                    on_select=self.filter_changed,
                                    width=200,
                                ),
                            ],
                            spacing=15,
                        ),
                        padding=15,
                        border_radius=10,
                    ),
                    ft.Container(height=15),
                    
                    # Lista rekordów + Panel statystyk
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        self.records_header,
                                        self.records_list,
                                    ],
                                    spacing=0,
                                    expand=True,
                                ),
                                border_radius=10,
                                padding=15,
                                expand=3,
                            ),
                            ft.Container(
                                content=self.stats_column,
                                expand=2,
                                padding=ft.Padding.only(left=16, right=8),
                            ),
                        ],
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        spacing=0,
                    ),
                    ft.Container(height=10),
                    
                    # Statystyki
                    ft.Container(
                        content=self.stats_text,
                        padding=10,
                        border_radius=10,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            padding=20,
            expand=True,
        )
