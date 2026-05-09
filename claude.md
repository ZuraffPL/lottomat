# Lottomat – Wytyczne projektowe dla AI

## Stack technologiczny

| Warstwa       | Technologia                        |
|---------------|------------------------------------|
| Język         | Python 3.14                        |
| UI Framework  | Flet (Flutter-based, cross-platform) |
| Baza danych   | SQLite3 (wbudowany moduł Python)    |
| Stdlib        | `random`, `datetime`, `typing`      |
| Launcher      | Plik `.bat` (Windows)              |

---

## Architektura aplikacji

```
lottomat_flet.py      → główna klasa LottomatApp (UI + logika generowania)
archive_tab_flet.py   → klasa ArchiveTabFlet (widok archiwum)
database.py           → klasa LottomatDatabase (warstwa danych, SQLite)
```

**Zasada separacji odpowiedzialności (SoC):**
- UI nie trafia do `database.py`
- Logika biznesowa (np. obliczanie trafień) należy do warstwy logiki, nie do UI
- Nowe funkcjonalności powinny trzymać się tego podziału

---

## Wytyczne dla kodu Python

### Ogólne
- Używaj **Python 3.14+** – korzystaj z nowoczesnej składni (`match/case`, `X | Y` zamiast `Union`, słowo kluczowe `type` zamiast `TypeAlias`)
- Stosuj **type hints** we wszystkich sygnaturach funkcji i metod
- Nazwy zmiennych, metod i klas w języku **angielskim** (komentarze i docstringi mogą być po polsku)
- Jedna klasa per plik – nie łącz niezwiązanych klas w jednym module
- Unikaj globalnych zmiennych; stan aplikacji trzymaj w instancji klasy

### Typowanie
```python
# Dobrze
def add_record(self, numbers: list[int]) -> int:

# Źle
def add_record(self, numbers, id):
```
- Nie używaj `Any` bez uzasadnienia; `# type: ignore` tylko gdy Flet wymaga (brak stubów)
- Nie używaj `from __future__ import annotations` – od Python 3.14 leniwa ewaluacja adnotacji (PEP 649) jest domyślna
- Importuj typy z `typing` tylko jeśli nie są dostępne natywnie (Python < 3.9)
- Używaj słowa kluczowego `type` do definiowania aliasów typów:
  ```python
  # Dobrze (Python 3.12+)
  type Record = tuple[int, str, str, str | None, str | None, str | None, str]

  # Źle
  Record = tuple[int, str, str, str | None, str | None, str | None, str]
  ```

### Obsługa błędów
- Łap wyjątki **konkretnych typów** (`sqlite3.Error`, `ValueError`), nie gołego `Exception`
- Błędy bazy danych loguj, nie cicho ignoruj
- Metody UI nigdy nie powinny rzucać wyjątków do użytkownika bez snackbara/dialogu

---

## Wytyczne dla Flet

### Zarządzanie widokami
- Każdy większy widok (zakładka) to osobna klasa z metodą `build() -> ft.Control`
- Nie twórz anonimowych lambda ze złożoną logiką – wydzielaj metody
- Po każdej zmianie kontrolek wywołuj `self.page.update()` **raz na końcu** metody, nie po każdej zmianie

```python
# Dobrze
def refresh_ui(self):
    self.container.controls.clear()
    for item in data:
        self.container.controls.append(self._build_row(item))
    self.page.update()

# Źle
for item in data:
    self.container.controls.append(...)
    self.page.update()  # ← zbędne wielokrotne wywołania
```

### Komponenty
- Wizualnie powtarzające się elementy (np. kulki) wydzielaj do metod fabrycznych (`create_ball()`)
- Kolory definiuj jako stałe klasowe, nie inline hex w każdym miejscu
- Nie używaj `page.overlay` bezpośrednio przez przypisanie – tylko `.append()` i `.remove()`
- Używaj `ft.run(main)` zamiast `ft.app(target=main)` (deprecated od 0.80)
- Używaj `ft.alignment.Alignment.CENTER` zamiast `ft.alignment.center` (zmiana w 0.80+)
- Używaj `ft.Padding.only(...)` zamiast `ft.padding.only(...)` (zmiana w 0.80+)
- Używaj `ft.Padding.symmetric(...)` zamiast `ft.padding.symmetric(...)` (zmiana w 0.80+)
- Używaj `content=` zamiast `text=` w przyciskach (`ElevatedButton`, `OutlinedButton`, `TextButton`) – `text=` usunięte w 0.80+
- Używaj `ft.Button` zamiast `ft.ElevatedButton` – `ElevatedButton` deprecated od 0.80, usunięte w 1.0
- Używaj `on_select=` zamiast `on_change=` w `ft.Dropdown` (zmiana w 0.80+)
- Używaj `ft.Icons.ICON_NAME` zamiast stringa `"icon_name"` w `IconButton` i innych miejscach z ikonami (zmiana w 0.80+)

### Motywy i styl
- Trzymaj się istniejącej palety kolorów:
  - Lotto: `#ef4444` (czerwony)
  - Eurojackpot: `#3b82f6` (niebieski)
  - Gwiazdki: `#fbbf24` (złoty)
  - Akcent główny: `#6366f1` (indygo)
- Nowe gry lub elementy UI powinny dostawać unikalny, spójny kolor

---

## Wytyczne dla SQLite / database.py

### Bezpieczeństwo i poprawność
- **Zawsze** używaj parametryzowanych zapytań (`?`) – nigdy f-stringów w SQL
- Każde połączenie otwieraj i zamykaj w tej samej metodzie (lub używaj context managera `with`)
- Preferuj context manager zamiast ręcznego `conn.close()`:

```python
# Preferowany wzorzec
with sqlite3.connect(self.db_name) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...", (param,))
    return cursor.fetchall()
```

### Migracje
- Każda zmiana schematu bazy musi mieć odpowiednią migrację w `_migrate_database()`
- Migracje są addytywne – nie usuwaj kolumn, tylko dodawaj lub oznaczaj jako przestarzałe
- Nowe kolumny muszą mieć wartość domyślną (`DEFAULT NULL` lub konkretną wartość)

### ID rekordów
- Obecna logika wypełnia luki w ID (`_get_next_id`). Zachowaj tę logikę przy nowych tabelach
- Nigdy nie polegaj na `lastrowid` bez sprawdzenia, czy ID było ręcznie ustawione

---

## Konwencje nazewnictwa

| Element           | Konwencja         | Przykład                   |
|-------------------|-------------------|----------------------------|
| Klasy             | PascalCase        | `LottomatDatabase`         |
| Metody/funkcje    | snake_case        | `get_all_records()`        |
| Stałe             | UPPER_SNAKE_CASE  | `VERSION = "0.9"`          |
| Zmienne prywatne  | `_` prefix        | `_migrate_database()`      |
| Pliki modułów     | snake_case        | `archive_tab_flet.py`      |

---

## Dodawanie nowych gier

Przy dodawaniu nowej gry (np. Keno, Multi Multi) trzymaj się wzorca:

1. Dodaj stałą koloru w `LottomatApp.__init__`
2. Zaimplementuj metodę `generate_<game>(self, e)` i `copy_<game>_to_clipboard(self, e)`
3. Dodaj metodę `add_<game>_record()` w `LottomatDatabase`
4. Zdefiniuj poziomy wygranych w `ArchiveTabFlet` (analogicznie do `_lotto_prize_tier`)
5. Zaktualizuj filtr gier w `ArchiveTabFlet`
6. Zaktualizuj README.md

---

## Czego unikać

- `# type: ignore` w nowym kodzie bez komentarza wyjaśniającego dlaczego
- Tworzenie nowych połączeń SQLite poza `LottomatDatabase`
- Umieszczanie logiki UI w `database.py`
- Używania `hasattr()` jako substytutu prawidłowej inicjalizacji atrybutów
- Inlinowania długich łańcuchów SQL bezpośrednio w metodach UI
- Ręcznego budowania HTML/SQL przez konkatenację stringów

---

## Uruchamianie i środowisko

- Środowisko wirtualne: `.venv` w katalogu projektu
- Aktywacja: `.venv\Scripts\Activate.ps1` (PowerShell) lub `Uruchom_Lottomat.bat`
- Wersja aplikacji jest trzymana w stałej `VERSION` w `lottomat_flet.py`
- Plik bazy danych: `lottomat_archive.db` (tworzony automatycznie, **nie commituj do VCS**)
