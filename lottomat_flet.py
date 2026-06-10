import asyncio
import subprocess
import flet as ft  # type: ignore
import random
from database import LottomatDatabase
from archive_tab_flet import ArchiveTabFlet
from typing import Any

VERSION = "1.4"


class LottomatApp:
    def __init__(self, page: ft.Page):  # type: ignore
        self.page = page
        self.page.title = f"Lottomat v{VERSION} - Generator liczb losowych"
        self.page.window_width = 1600  # type: ignore
        self.page.window_height = 1400  # type: ignore
        self.page.window_min_width = 1300  # type: ignore
        self.page.window_min_height = 1300  # type: ignore
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.bgcolor = "#ffffff"  # Białe dla jasnego trybu
        
        # Niestandardowy motyw ciemny (grafitowy zamiast czarnego)
        self.page.theme = ft.Theme(
            color_scheme_seed="#6366f1",
        )
        self.page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                surface="#1e293b",
                primary="#6366f1",
            )
        )
        
        # Kolory
        self.lotto_color = "#ef4444"
        self.euro_color = "#3b82f6"
        self.star_color = "#fbbf24"
        
        # Zmienne do przechowywania wylosowanych liczb
        self.lotto_numbers: list[int] = []
        self.euro_main_numbers: list[int] = []
        self.euro_star_numbers: list[int] = []

        # Pending sets (bufor kuponu – wiele zestawów przed archiwizacją)
        self.lotto_pending_sets: list[list[int]] = []
        # Każdy element: (main_numbers, star_numbers)
        self.euro_pending_sets: list[tuple[list[int], list[int]]] = []

        # Kontenery i teksty dla pending sets
        self.lotto_pending_container = ft.Column(spacing=4)
        self.lotto_pending_count_text = ft.Text("Zestawy w kuponie: 0/10", size=12, color="#6b7280")
        self.euro_pending_container = ft.Column(spacing=4)
        self.euro_pending_count_text = ft.Text("Zestawy w kuponie: 0/10", size=12, color="#6b7280")
        
        # Baza danych
        self.database = LottomatDatabase()
        
        # Widok archiwum (inicjalizowany przy tworzeniu zakładki)
        self.archive_view: ArchiveTabFlet | None = None
        
        # Kontenery na kulki
        self.lotto_balls_container = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        self.euro_main_balls_container = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        self.euro_star_balls_container = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        
        # Tworzenie interfejsu
        self.create_ui()
    
    def create_ball(self, number: int, color: str) -> ft.Container:
        """Tworzenie kulki z numerem"""
        return ft.Container(
            content=ft.Text(
                str(number),
                size=22,
                weight=ft.FontWeight.BOLD,
                color="white",
                text_align=ft.TextAlign.CENTER,
            ),
            width=70,
            height=70,
            border_radius=35,
            bgcolor=color,
            alignment=ft.alignment.Alignment.CENTER,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color="#00000040",
                offset=ft.Offset(2, 4),
            ),
        )
    
    def generate_lotto(self, e: Any) -> None:  # type: ignore
        """Generowanie liczb dla gry Lotto"""
        self.lotto_numbers = sorted(random.sample(range(1, 50), 6))
        
        # Czyszczenie i dodanie nowych kulek
        self.lotto_balls_container.controls.clear()
        for num in self.lotto_numbers:
            self.lotto_balls_container.controls.append(self.create_ball(num, self.lotto_color))
        
        self.page.update()  # type: ignore
    
    def generate_eurojackpot(self, e: Any) -> None:  # type: ignore
        """Generowanie liczb dla gry Eurojackpot"""
        self.euro_main_numbers = sorted(random.sample(range(1, 51), 5))
        self.euro_star_numbers = sorted(random.sample(range(1, 13), 2))
        
        # Czyszczenie i dodanie nowych kulek - liczby główne
        self.euro_main_balls_container.controls.clear()
        for num in self.euro_main_numbers:
            self.euro_main_balls_container.controls.append(self.create_ball(num, self.euro_color))
        
        # Czyszczenie i dodanie gwiazd
        self.euro_star_balls_container.controls.clear()
        for num in self.euro_star_numbers:
            self.euro_star_balls_container.controls.append(self.create_ball(num, self.star_color))
        
        self.page.update()  # type: ignore
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Kopiuje tekst do schowka systemowego (Windows)"""
        proc = subprocess.Popen(
            ["clip"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        proc.communicate(text.encode("utf-16"))

    def copy_lotto_to_clipboard(self, e: Any) -> None:  # type: ignore
        """Kopiowanie liczb Lotto do schowka"""
        if not self.lotto_numbers:
            return
        
        text = " ".join(str(num) for num in self.lotto_numbers)
        self._copy_to_clipboard(text)
        self.show_snackbar("Liczby Lotto skopiowane do schowka! ✓", "#15803d")
    
    def copy_euro_to_clipboard(self, e: Any) -> None:  # type: ignore
        """Kopiowanie liczb Eurojackpot do schowka"""
        if not self.euro_main_numbers or not self.euro_star_numbers:
            return
        
        main_text = " ".join(str(num) for num in self.euro_main_numbers)
        stars_text = " ".join(str(num) for num in self.euro_star_numbers)
        text = f"{main_text} | {stars_text}"
        self._copy_to_clipboard(text)
        self.show_snackbar("Liczby Eurojackpot skopiowane do schowka! ✓", "#15803d")
    
    def _refresh_lotto_pending_display(self) -> None:
        """Odświeża widok zestawów oczekujących w kuponie Lotto"""
        self.lotto_pending_container.controls.clear()
        for i, numbers in enumerate(self.lotto_pending_sets):
            balls: list[ft.Control] = [
                ft.Container(
                    content=ft.Text(str(n), size=11, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor=self.lotto_color,
                    width=30, height=30, border_radius=15,
                    alignment=ft.alignment.Alignment.CENTER,
                )
                for n in numbers
            ]

            def make_remove_lotto(idx: int):
                def on_remove(e: Any) -> None:  # type: ignore
                    self.lotto_pending_sets.pop(idx)
                    self._refresh_lotto_pending_display()
                    self.page.update()  # type: ignore
                return on_remove

            row: ft.Control = ft.Row(
                [
                    ft.Text(f"{i + 1}.", size=11, color="#6b7280", width=18),
                    *balls,
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=14,
                        icon_color="#9ca3af",
                        on_click=make_remove_lotto(i),
                        tooltip="Usuń zestaw",
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.lotto_pending_container.controls.append(row)
        count = len(self.lotto_pending_sets)
        self.lotto_pending_count_text.value = f"Zestawy w kuponie: {count}/10"

    def _add_to_lotto_pending(self, e: Any) -> None:  # type: ignore
        """Dodaje bieżący zestaw Lotto do kuponu"""
        if not self.lotto_numbers:
            self.show_snackbar("Najpierw wygeneruj liczby!", "#b91c1c")
            return
        if len(self.lotto_pending_sets) >= 10:
            self.show_snackbar("Maksymalnie 10 zestawów w kuponie!", "#b91c1c")
            return
        self.lotto_pending_sets.append(self.lotto_numbers[:])
        self._refresh_lotto_pending_display()
        self.lotto_numbers = []
        self.lotto_balls_container.controls.clear()
        self.page.update()  # type: ignore

    def _clear_lotto_pending(self, e: Any) -> None:  # type: ignore
        """Czyści kupon Lotto"""
        self.lotto_pending_sets.clear()
        self._refresh_lotto_pending_display()
        self.page.update()  # type: ignore

    def _refresh_euro_pending_display(self) -> None:
        """Odświeża widok zestawów oczekujących w kuponie Eurojackpot"""
        self.euro_pending_container.controls.clear()
        for i, (main_nums, star_nums) in enumerate(self.euro_pending_sets):
            main_balls: list[ft.Control] = [
                ft.Container(
                    content=ft.Text(str(n), size=11, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor=self.euro_color,
                    width=30, height=30, border_radius=15,
                    alignment=ft.alignment.Alignment.CENTER,
                )
                for n in main_nums
            ]
            star_balls: list[ft.Control] = [
                ft.Container(
                    content=ft.Text(str(n), size=11, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor=self.star_color,
                    width=30, height=30, border_radius=15,
                    alignment=ft.alignment.Alignment.CENTER,
                )
                for n in star_nums
            ]

            def make_remove_euro(idx: int):
                def on_remove(e: Any) -> None:  # type: ignore
                    self.euro_pending_sets.pop(idx)
                    self._refresh_euro_pending_display()
                    self.page.update()  # type: ignore
                return on_remove

            row: ft.Control = ft.Row(
                [
                    ft.Text(f"{i + 1}.", size=11, color="#6b7280", width=18),
                    *main_balls,
                    ft.Text("|", size=12, color="#9ca3af"),
                    *star_balls,
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=14,
                        icon_color="#9ca3af",
                        on_click=make_remove_euro(i),
                        tooltip="Usuń zestaw",
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            self.euro_pending_container.controls.append(row)
        count = len(self.euro_pending_sets)
        self.euro_pending_count_text.value = f"Zestawy w kuponie: {count}/10"

    def _add_to_euro_pending(self, e: Any) -> None:  # type: ignore
        """Dodaje bieżący zestaw Eurojackpot do kuponu"""
        if not self.euro_main_numbers or not self.euro_star_numbers:
            self.show_snackbar("Najpierw wygeneruj liczby!", "#b91c1c")
            return
        if len(self.euro_pending_sets) >= 10:
            self.show_snackbar("Maksymalnie 10 zestawów w kuponie!", "#b91c1c")
            return
        self.euro_pending_sets.append((self.euro_main_numbers[:], self.euro_star_numbers[:]))
        self._refresh_euro_pending_display()
        self.euro_main_numbers = []
        self.euro_star_numbers = []
        self.euro_main_balls_container.controls.clear()
        self.euro_star_balls_container.controls.clear()
        self.page.update()  # type: ignore

    def _clear_euro_pending(self, e: Any) -> None:  # type: ignore
        """Czyści kupon Eurojackpot"""
        self.euro_pending_sets.clear()
        self._refresh_euro_pending_display()
        self.page.update()  # type: ignore

    def archive_lotto(self, e: Any) -> None:  # type: ignore
        """Archiwizuje kupon Lotto (wszystkie zestawy z kuponu lub bieżący)"""
        if self.lotto_pending_sets:
            sets_to_save = self.lotto_pending_sets[:]
        elif self.lotto_numbers:
            sets_to_save = [self.lotto_numbers[:]]
        else:
            self.show_snackbar("Najpierw wygeneruj lub dodaj liczby do kuponu!", "#b91c1c")
            return

        self.database.add_lotto_record(sets_to_save)
        self.lotto_pending_sets.clear()
        self._refresh_lotto_pending_display()
        self.lotto_numbers = []
        self.lotto_balls_container.controls.clear()
        n = len(sets_to_save)
        label = f"{n} zestawy" if n in (2, 3, 4) else (f"{n} zestawów" if n > 4 else "1 zestaw")
        self.show_snackbar(f"Kupon Lotto ({label}) dodany do archiwum! 💾", "#1d4ed8")
        if self.archive_view is not None:
            self.archive_view.refresh_archive()
        self.page.update()  # type: ignore

    def archive_eurojackpot(self, e: Any) -> None:  # type: ignore
        """Archiwizuje kupon Eurojackpot (wszystkie zestawy z kuponu lub bieżący)"""
        if self.euro_pending_sets:
            main_sets = [m for m, _ in self.euro_pending_sets]
            star_sets = [s for _, s in self.euro_pending_sets]
        elif self.euro_main_numbers and self.euro_star_numbers:
            main_sets = [self.euro_main_numbers[:]]
            star_sets = [self.euro_star_numbers[:]]
        else:
            self.show_snackbar("Najpierw wygeneruj lub dodaj liczby do kuponu!", "#b91c1c")
            return

        self.database.add_eurojackpot_record(main_sets, star_sets)
        self.euro_pending_sets.clear()
        self._refresh_euro_pending_display()
        self.euro_main_numbers = []
        self.euro_star_numbers = []
        self.euro_main_balls_container.controls.clear()
        self.euro_star_balls_container.controls.clear()
        n = len(main_sets)
        label = f"{n} zestawy" if n in (2, 3, 4) else (f"{n} zestawów" if n > 4 else "1 zestaw")
        self.show_snackbar(f"Kupon Eurojackpot ({label}) dodany do archiwum! 💾", "#1d4ed8")
        if self.archive_view is not None:
            self.archive_view.refresh_archive()
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
    
    def create_lotto_section(self) -> ft.Container:
        """Tworzenie sekcji dla gry Lotto"""
        return ft.Container(
            content=ft.Column(
                [
                    # Nagłówek
                    ft.Row(
                        [
                            ft.Text("🔴 Lotto", size=24, weight=ft.FontWeight.BOLD, color=self.lotto_color),
                            ft.Text("6 liczb z 49", size=14, color="#6b7280"),
                        ],
                        spacing=15,
                    ),
                    ft.Container(height=10),
                    
                    # Przycisk generowania
                    ft.Button(
                        content="🎲 Generuj liczby",
                        on_click=self.generate_lotto,
                        style=ft.ButtonStyle(
                            bgcolor=self.lotto_color,
                            color="white",
                            padding=ft.Padding.symmetric(horizontal=30, vertical=18),
                            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
                        ),
                        height=55,
                    ),
                    ft.Container(height=15),
                    
                    # Kontener na kulki
                    ft.Container(
                        content=self.lotto_balls_container,
                        bgcolor="#f8fafc",
                        border_radius=10,
                        padding=20,
                        height=120,
                        alignment=ft.alignment.Alignment.CENTER,
                    ),
                    ft.Container(height=15),
                    
                    # Przyciski akcji
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                content="📋 Kopiuj",
                                on_click=self.copy_lotto_to_clipboard,
                                style=ft.ButtonStyle(
                                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                                ),
                            ),
                            ft.OutlinedButton(
                                content="➕ Dodaj do kuponu",
                                on_click=self._add_to_lotto_pending,
                                style=ft.ButtonStyle(
                                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                                ),
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(height=12),

                    # Kupon – lista zestawów oczekujących na archiwizację
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        self.lotto_pending_count_text,
                                        ft.TextButton(
                                            "Czyść kupon",
                                            on_click=self._clear_lotto_pending,
                                            style=ft.ButtonStyle(color="#9ca3af"),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                self.lotto_pending_container,
                            ],
                            spacing=4,
                            tight=True,
                        ),
                        bgcolor="#f8fafc",
                        border_radius=10,
                        padding=10,
                    ),
                    ft.Container(height=10),

                    # Przycisk archiwizacji kuponu
                    ft.Button(
                        content="💾 Archiwizuj kupon",
                        on_click=self.archive_lotto,
                        style=ft.ButtonStyle(
                            bgcolor="#1d4ed8",
                            color="white",
                            padding=ft.Padding.symmetric(horizontal=30, vertical=15),
                            text_style=ft.TextStyle(size=15, weight=ft.FontWeight.BOLD),
                        ),
                        height=50,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            padding=25,

            border_radius=15,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color="#0000001A",
                offset=ft.Offset(0, 2),
            ),
        )
    
    def create_eurojackpot_section(self) -> ft.Container:
        """Tworzenie sekcji dla gry Eurojackpot"""
        return ft.Container(
            content=ft.Column(
                [
                    # Nagłówek
                    ft.Row(
                        [
                            ft.Text("⭐ Eurojackpot", size=24, weight=ft.FontWeight.BOLD, color=self.euro_color),
                            ft.Text("5 z 50 + 2 z 12", size=14, color="#6b7280"),
                        ],
                        spacing=15,
                    ),
                    ft.Container(height=10),
                    
                    # Przycisk generowania
                    ft.Button(
                        content="🎲 Generuj liczby",
                        on_click=self.generate_eurojackpot,
                        style=ft.ButtonStyle(
                            bgcolor=self.euro_color,
                            color="white",
                            padding=ft.Padding.symmetric(horizontal=30, vertical=18),
                            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
                        ),
                        height=55,
                    ),
                    ft.Container(height=15),
                    
                    # Liczby główne
                    ft.Text("Liczby główne:", size=13, weight=ft.FontWeight.BOLD, color="#1f2937"),
                    ft.Container(height=5),
                    ft.Container(
                        content=self.euro_main_balls_container,
                        bgcolor="#f8fafc",
                        border_radius=10,
                        padding=20,
                        height=120,
                        alignment=ft.alignment.Alignment.CENTER,
                    ),
                    ft.Container(height=15),
                    
                    # Gwiazdy
                    ft.Text("Gwiazdy:", size=13, weight=ft.FontWeight.BOLD, color="#1f2937"),
                    ft.Container(height=5),
                    ft.Container(
                        content=self.euro_star_balls_container,
                        bgcolor="#f8fafc",
                        border_radius=10,
                        padding=20,
                        height=120,
                        alignment=ft.alignment.Alignment.CENTER,
                    ),
                    ft.Container(height=15),
                    
                    # Przyciski akcji
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                content="📋 Kopiuj",
                                on_click=self.copy_euro_to_clipboard,
                                style=ft.ButtonStyle(
                                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                                ),
                            ),
                            ft.OutlinedButton(
                                content="➕ Dodaj do kuponu",
                                on_click=self._add_to_euro_pending,
                                style=ft.ButtonStyle(
                                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                                ),
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(height=12),

                    # Kupon – lista zestawów oczekujących na archiwizację
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        self.euro_pending_count_text,
                                        ft.TextButton(
                                            "Czyść kupon",
                                            on_click=self._clear_euro_pending,
                                            style=ft.ButtonStyle(color="#9ca3af"),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                self.euro_pending_container,
                            ],
                            spacing=4,
                            tight=True,
                        ),
                        bgcolor="#f8fafc",
                        border_radius=10,
                        padding=10,
                    ),
                    ft.Container(height=10),

                    # Przycisk archiwizacji kuponu
                    ft.Button(
                        content="💾 Archiwizuj kupon",
                        on_click=self.archive_eurojackpot,
                        style=ft.ButtonStyle(
                            bgcolor="#1d4ed8",
                            color="white",
                            padding=ft.Padding.symmetric(horizontal=30, vertical=15),
                            text_style=ft.TextStyle(size=15, weight=ft.FontWeight.BOLD),
                        ),
                        height=50,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color="#0000001A",
                offset=ft.Offset(0, 2),
            ),
        )
    
    def create_generator_tab(self) -> ft.Container:
        """Tworzenie zakładki generatora"""
        return ft.Container(
            content=ft.Column(
                [
                    # Tytuł
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "🎰 Lottomat 🎰",
                                    size=32,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    "Generator szczęśliwych liczb",
                                    size=15,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        padding=ft.Padding.only(top=20, bottom=30),
                        alignment=ft.alignment.Alignment.CENTER,
                    ),
                    
                    # Sekcje gier obok siebie (2 kolumny)
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=self.create_lotto_section(),
                                col={"sm": 12, "md": 6},
                                padding=10,
                            ),
                            ft.Container(
                                content=self.create_eurojackpot_section(),
                                col={"sm": 12, "md": 6},
                                padding=10,
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
            ),
            padding=ft.Padding.symmetric(horizontal=20),
            expand=True,
        )
    
    def create_archive_tab(self) -> ft.Container:
        """Tworzenie zakładki archiwum"""
        self.archive_view = ArchiveTabFlet(self.page, self.database)
        return self.archive_view.build()
    
    def switch_tab(self, e: Any) -> None:  # type: ignore
        """Przełączanie między zakładkami"""
        if e.control.data == "generator":
            self.generator_container.visible = True
            self.archive_container.visible = False
            self.generator_btn.style = ft.ButtonStyle(bgcolor="#6366f1", color="white")
            self.archive_btn.style = ft.ButtonStyle(bgcolor="transparent", color="#6366f1")
        else:
            self.generator_container.visible = False
            self.archive_container.visible = True
            self.generator_btn.style = ft.ButtonStyle(bgcolor="transparent", color="#6366f1")
            self.archive_btn.style = ft.ButtonStyle(bgcolor="#6366f1", color="white")
        self.page.update()  # type: ignore
    
    def toggle_theme(self, e: Any) -> None:  # type: ignore
        """Przełączanie trybu jasny/ciemny"""
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = "#1e293b"
            e.control.icon = ft.Icons.DARK_MODE
            e.control.tooltip = "Przełącz na tryb jasny"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = "#ffffff"
            e.control.icon = ft.Icons.LIGHT_MODE
            e.control.tooltip = "Przełącz na tryb ciemny"
        # Odśwież archiwum, aby zaktualizować kolory tła rekordów
        self.archive_view.refresh_archive()
        self.page.update()  # type: ignore

    def show_about(self, e: Any) -> None:  # type: ignore
        """Dialog O programie"""
        def close(ev: Any) -> None:  # type: ignore
            dialog.open = False
            self.page.update()  # type: ignore

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Lottomat v{VERSION}", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Generator liczb losowych dla gier liczbowych", size=13, color="#6b7280"),
                    ft.Container(height=12),
                    ft.Text("Stack technologiczny", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(height=4),
                    ft.Text("• Python 3.14", size=12),
                    ft.Text("• Flet (Flutter-based UI)", size=12),
                    ft.Text("• SQLite3", size=12),
                    ft.Container(height=12),
                    ft.Text("Autor", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(height=4),
                    ft.Text("Marcin Żurawicz", size=12),
                ],
                tight=True,
                spacing=2,
            ),
            actions=[
                ft.TextButton("Zamknij", on_click=close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)  # type: ignore
        dialog.open = True
        self.page.update()  # type: ignore

    def create_ui(self) -> None:
        """Tworzenie interfejsu użytkownika"""
        # Tworzenie kontenerów dla zakładek
        self.generator_container = self.create_generator_tab()
        self.archive_container = self.create_archive_tab()
        self.archive_container.visible = False
        
        # Przyciski nawigacji
        self.generator_btn = ft.Button(
            content="🎰 Generator",
            data="generator",
            on_click=self.switch_tab,
            style=ft.ButtonStyle(bgcolor="#6366f1", color="white"),
            height=50,
        )
        
        self.archive_btn = ft.Button(
            content="📚 Archiwum",
            data="archive",
            on_click=self.switch_tab,
            style=ft.ButtonStyle(bgcolor="transparent", color="#6366f1"),
            height=50,
        )
        
        theme_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE,
            icon_color="#6366f1",
            tooltip="Przełącz na tryb ciemny",
            on_click=self.toggle_theme,
        )

        about_btn = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            icon_color="#6366f1",
            tooltip="O programie",
            on_click=self.show_about,
        )
        
        # Layout
        nav_bar = ft.Row(
            [
                ft.Row(
                    [self.generator_btn, self.archive_btn],
                    spacing=10,
                ),
                ft.Row([about_btn, theme_btn], spacing=4),
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        content = ft.Column(
            [
                ft.Container(content=nav_bar, padding=10),
                ft.Stack(
                    [
                        self.generator_container,
                        self.archive_container,
                    ],
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        )
        
        self.page.add(content)
        self.page.run_task(self._show_splash)  # type: ignore

    async def _show_splash(self) -> None:
        """Splash screen przy starcie aplikacji"""

        def tech_chip(label: str, color: str) -> ft.Container:
            return ft.Container(
                content=ft.Text(label, size=11, color="white", weight=ft.FontWeight.W_500),
                bgcolor=color,
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=12, vertical=5),
            )

        progress = ft.ProgressBar(
            value=0,
            bgcolor="#ffffff25",
            color="#a5b4fc",
            width=280,
            height=4,
            border_radius=2,
        )

        splash = ft.Container(
            content=ft.Column(
                [
                    ft.Container(expand=True),
                    ft.Text("🎰", size=72, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Text(
                        "Lottomat",
                        size=54,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Text(
                            f"v{VERSION}",
                            size=15,
                            color="#1e1b4b",
                            weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor="#a5b4fc",
                        border_radius=20,
                        padding=ft.Padding.symmetric(horizontal=14, vertical=5),
                    ),
                    ft.Container(height=40),
                    ft.Text(
                        "Stack technologiczny",
                        size=12,
                        color="#818cf8",
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            tech_chip("Python 3.14", "#15803d"),
                            tech_chip("Flet (Flutter)", "#1d4ed8"),
                            tech_chip("SQLite3", "#b45309"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Container(height=50),
                    ft.Text(
                        "autor: Marcin Żurawicz",
                        size=13,
                        color="#c7d2fe",
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(expand=True),
                    progress,
                    ft.Container(height=44),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
                spacing=0,
            ),
            bgcolor="#1e1b4b",
            expand=True,
            alignment=ft.alignment.Alignment.CENTER,
        )

        self.page.overlay.append(splash)  # type: ignore
        self.page.update()  # type: ignore

        steps = 40
        total_duration = 2.5
        for i in range(steps + 1):
            progress.value = i / steps
            self.page.update()  # type: ignore
            await asyncio.sleep(total_duration / steps)

        self.page.overlay.remove(splash)  # type: ignore
        self.page.update()  # type: ignore


def main(page: ft.Page):  # type: ignore
    LottomatApp(page)


if __name__ == "__main__":
    ft.run(main)  # type: ignore
