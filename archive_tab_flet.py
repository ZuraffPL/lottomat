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

        # Tworzenie tabeli
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Gra", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Twoje liczby", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Dodatkowe", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Wynik losowania", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Wynik extra", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Trafność", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Data", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Akcje", weight=ft.FontWeight.BOLD, size=12)),
            ],
            rows=[],
            border_radius=10,
            heading_row_height=50,
            data_row_min_height=60,
            data_row_max_height=80,
        )
        # Inicjalizacja rows bez adnotacji typu
        self.data_table.rows = []

        self.stats_text = ft.Text("Rekordów w archiwum: 0", size=13)
        self.stats_column = ft.Column([], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        # Nie przypisuj nowej listy do self.page.overlay, overlay jest zarządzane przez Flet
        # Możesz bezpośrednio używać self.page.overlay.append(...)
    
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

            tier_counts: dict[str, dict[str, Any]] = {}
            wins = 0

            for rec in with_result:
                _, _, numbers, extra_numbers, actual_numbers, actual_extra_numbers, _ = rec
                gen_nums = set(numbers.split(",")) if numbers else set()
                act_nums = set(actual_numbers.split(",")) if actual_numbers else set()
                hits = gen_nums & act_nums

                if game_type == "Lotto":
                    tier_name, tier_color = self._lotto_prize_tier(len(hits))
                else:
                    gen_extra = set(extra_numbers.split(",")) if extra_numbers else set()
                    act_extra = set(actual_extra_numbers.split(",")) if actual_extra_numbers else set()
                    tier_name, tier_color = self._eurojackpot_prize_tier(
                        len(hits), len(gen_extra & act_extra)
                    )

                if tier_name:
                    wins += 1
                    if tier_name not in tier_counts:
                        tier_counts[tier_name] = {"count": 0, "color": tier_color}
                    tier_counts[tier_name]["count"] += 1

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

        # Lotto: zlicz 0..6 trafień
        lotto_hits: dict[int, int] = {i: 0 for i in range(7)}
        lotto_res = [r for r in all_records if r[1] == "Lotto" and r[4]]
        for rec in lotto_res:
            _, _, numbers, _, actual_numbers, _, _ = rec
            gen_nums = set(numbers.split(",")) if numbers else set()
            act_nums = set(actual_numbers.split(",")) if actual_numbers else set()
            lotto_hits[len(gen_nums & act_nums)] += 1

        lotto_total = len(lotto_res)
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

        # Eurojackpot: zlicz (main, extra) trafień
        euro_hits: dict[tuple[int, int], int] = {}
        euro_res = [r for r in all_records if r[1] == "Eurojackpot" and r[4]]
        for rec in euro_res:
            _, _, numbers, extra_numbers, actual_numbers, actual_extra_numbers, _ = rec
            gen_nums = set(numbers.split(",")) if numbers else set()
            gen_extra = set(extra_numbers.split(",")) if extra_numbers else set()
            act_nums = set(actual_numbers.split(",")) if actual_numbers else set()
            act_extra = set(actual_extra_numbers.split(",")) if actual_extra_numbers else set()
            key = (len(gen_nums & act_nums), len(gen_extra & act_extra))
            euro_hits[key] = euro_hits.get(key, 0) + 1

        euro_total = len(euro_res)
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

        # --- Najczęstsze liczby (prawa kolumna) ---
        freq: dict[str, dict[str, dict[str, int]]] = {
            "Lotto":       {"main": {}},
            "Eurojackpot": {"main": {}, "extra": {}},
        }
        draws: dict[str, int] = {"Lotto": 0, "Eurojackpot": 0}

        for rec in all_records:
            _, rec_game, _, _, actual_numbers, actual_extra_numbers, _ = rec
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
    
    def refresh_archive(self):
        """Odświeżenie listy rekordów"""
        # Pobierz rekordy
        records: list[tuple[int, str, str, str | None, str | None, str | None, str]]
        if self.filter_value == "Wszystkie":
            records = self.database.get_all_records()
        else:
            records = self.database.get_records_by_game(self.filter_value)
        
        # Czyszczenie tabeli
        self.data_table.rows = []
        
        # Wypełnienie tabeli
        for record in records:
            record_id, game_type, numbers, extra_numbers, actual_numbers, actual_extra_numbers, created_date = record
            
            # Konwersja liczb
            gen_nums: set[str] = set(numbers.split(",")) if numbers else set()
            gen_extra: set[str] = set(extra_numbers.split(",")) if extra_numbers else set()
            act_nums: set[str] = set(actual_numbers.split(",")) if actual_numbers else set()
            act_extra: set[str] = set(actual_extra_numbers.split(",")) if actual_extra_numbers else set()
            
            # Oblicz trafienia
            matches_main = gen_nums & act_nums
            matches_extra = gen_extra & act_extra
            
            # Formatowanie liczb z podświetleniem trafień
            numbers_display = self.format_numbers_with_highlights(numbers, matches_main)
            extra_display = self.format_numbers_with_highlights(extra_numbers, matches_extra) if extra_numbers else ft.Row([ft.Text("-", size=12)])
            
            # Wynik losowania
            result_display = actual_numbers.replace(",", ", ") if actual_numbers else "-"
            result_extra_display = actual_extra_numbers.replace(",", ", ") if actual_extra_numbers else "-"
            
            # Trafność
            if actual_numbers:
                if game_type == "Lotto":
                    tier_name, tier_color = self._lotto_prize_tier(len(matches_main))
                    if tier_name:
                        accuracy = tier_name
                        accuracy_color = tier_color
                    else:
                        accuracy = f"{len(matches_main)}/6"
                        accuracy_color = "#6b7280"
                else:
                    tier_name, tier_color = self._eurojackpot_prize_tier(len(matches_main), len(matches_extra))
                    if tier_name:
                        accuracy = tier_name
                        accuracy_color = tier_color
                    else:
                        accuracy = f"{len(matches_main)}+{len(matches_extra)}"
                        accuracy_color = "#6b7280"
            else:
                accuracy = "-"
                accuracy_color = "#6b7280"
            
            # Formatowanie daty
            try:
                date_obj = datetime.fromisoformat(created_date)
                date_display = date_obj.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                date_display = created_date
            
            # Kolor tła w zależności od typu gry i motywu
            if self.page.theme_mode == ft.ThemeMode.DARK:
                # Tryb ciemny - subtelne ciemne kolory
                bg_color = self.LOTTO_BG_DARK if game_type == "Lotto" else self.EURO_BG_DARK
            else:
                # Tryb jasny - jasne kolory
                bg_color = self.LOTTO_BG_LIGHT if game_type == "Lotto" else self.EURO_BG_LIGHT
            
            # Tworzenie wiersza
            row = ft.DataRow(
                color={ft.ControlState.DEFAULT: bg_color},
                cells=[
                    ft.DataCell(ft.Text(str(record_id), size=12)),
                    ft.DataCell(ft.Text(game_type, size=12, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(numbers_display),
                    ft.DataCell(extra_display),
                    ft.DataCell(ft.Text(result_display, size=12)),
                    ft.DataCell(ft.Text(result_extra_display, size=12)),
                    ft.DataCell(ft.Text(accuracy, size=12, weight=ft.FontWeight.BOLD, color=accuracy_color)),
                    ft.DataCell(ft.Text(date_display, size=12)),
                    ft.DataCell(
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
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color="#b91c1c",
                                    tooltip="Usuń",
                                    data=record_id,
                                    on_click=self.handle_delete,
                                ),
                            ],
                            spacing=5,
                        )
                    ),
                ],
            )
            
            self.data_table.rows.append(row)  # type: ignore
        
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
        """Dialog do wprowadzenia własnych liczb do archiwum"""
        game_dropdown = ft.Dropdown(
            label="Wybierz grę",
            value="Lotto",
            options=[
                ft.dropdown.Option("Lotto"),
                ft.dropdown.Option("Eurojackpot"),
            ],
            width=250,
        )

        main_entry = ft.TextField(
            label="Liczby Lotto (6 liczb z 1-49)",
            hint_text="Przykład: 1 12 23 34 45 49",
            width=400,
        )

        extra_entry = ft.TextField(
            label="Gwiazdy (2 liczby z 1-12)",
            hint_text="Przykład: 3 7",
            width=400,
            visible=False,
        )

        def on_game_change(ev: Any) -> None:  # type: ignore
            if game_dropdown.value == "Eurojackpot":
                main_entry.label = "Liczby główne (5 liczb z 1-50)"
                main_entry.hint_text = "Przykład: 1 12 23 34 45"
                extra_entry.visible = True
            else:
                main_entry.label = "Liczby Lotto (6 liczb z 1-49)"
                main_entry.hint_text = "Przykład: 1 12 23 34 45 49"
                extra_entry.visible = False
            self.page.update()  # type: ignore

        game_dropdown.on_select = on_game_change

        def save_custom(ev: Any) -> None:  # type: ignore
            try:
                game_type = game_dropdown.value
                main_text = (main_entry.value or "").strip()
                if not main_text:
                    self.show_snackbar("Wprowadź liczby!", "#b91c1c")
                    return
                main_nums = [int(x) for x in main_text.split()]

                if game_type == "Lotto":
                    if len(main_nums) != 6:
                        self.show_snackbar("Lotto wymaga dokładnie 6 liczb!", "#b91c1c")
                        return
                    if any(n < 1 or n > 49 for n in main_nums):
                        self.show_snackbar("Liczby Lotto muszą być z zakresu 1-49!", "#b91c1c")
                        return
                    if len(set(main_nums)) != 6:
                        self.show_snackbar("Liczby nie mogą się powtarzać!", "#b91c1c")
                        return
                    self.database.add_lotto_record(sorted(main_nums))
                else:  # Eurojackpot
                    if len(main_nums) != 5:
                        self.show_snackbar("Eurojackpot wymaga dokładnie 5 liczb głównych!", "#b91c1c")
                        return
                    if any(n < 1 or n > 50 for n in main_nums):
                        self.show_snackbar("Liczby główne muszą być z zakresu 1-50!", "#b91c1c")
                        return
                    if len(set(main_nums)) != 5:
                        self.show_snackbar("Liczby główne nie mogą się powtarzać!", "#b91c1c")
                        return

                    extra_text = (extra_entry.value or "").strip()
                    if not extra_text:
                        self.show_snackbar("Wprowadź gwiazdy!", "#b91c1c")
                        return
                    extra_nums = [int(x) for x in extra_text.split()]

                    if len(extra_nums) != 2:
                        self.show_snackbar("Eurojackpot wymaga dokładnie 2 gwiazd!", "#b91c1c")
                        return
                    if any(n < 1 or n > 12 for n in extra_nums):
                        self.show_snackbar("Gwiazdy muszą być z zakresu 1-12!", "#b91c1c")
                        return
                    if len(set(extra_nums)) != 2:
                        self.show_snackbar("Gwiazdy nie mogą się powtarzać!", "#b91c1c")
                        return

                    self.database.add_eurojackpot_record(sorted(main_nums), sorted(extra_nums))

                self.refresh_archive()
                dialog.open = False
                self.page.update()  # type: ignore
                self.show_snackbar(f"Własne liczby {game_type} dodane do archiwum!", "#15803d")

            except ValueError:
                self.show_snackbar("Wprowadź poprawne liczby całkowite oddzielone spacjami!", "#b91c1c")

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
                        main_entry,
                        ft.Container(height=5),
                        extra_entry,
                    ],
                    tight=True,
                    spacing=5,
                ),
                width=450,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=cancel_dialog),
                ft.Button("✓ Dodaj", on_click=save_custom, bgcolor="#15803d", color="white"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore

    def show_snackbar(self, message: str, color: str) -> None:
        """Pokazanie komunikatu snackbar"""
        self.page.snack_bar = ft.SnackBar(  # type: ignore
            content=ft.Text(message, color="white"),
            bgcolor=color,
            duration=2000,
        )
        self.page.snack_bar.open = True  # type: ignore
        self.page.update()  # type: ignore
    
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
                    
                    # Tabela + Panel statystyk
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [self.data_table],
                                    scroll=ft.ScrollMode.AUTO,
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
