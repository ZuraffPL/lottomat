# 🎰 Lottomat

**Generator szczęśliwych liczb do gier losowych** — nowoczesna aplikacja desktopowa z archiwum wyników.

![Version](https://img.shields.io/badge/wersja-1.2-6366f1)
![Python](https://img.shields.io/badge/Python-3.14-15803d)
![License](https://img.shields.io/badge/licencja-CC%20BY%204.0-blue)

---

## Funkcje

- **Lotto** — generuje 6 losowych liczb z zakresu 1–49 (bez powtórzeń)
- **Eurojackpot** — generuje 5 liczb z zakresu 1–50 oraz 2 gwiazdy z zakresu 1–12 (bez powtórzeń)
- **Kupony wielozestawowe** — do 10 zestawów liczb w jednym zakładzie; każdy zestaw porównywany z wynikiem osobno
- **Archiwum** — zapis i przeglądanie historii zakładów z bazą SQLite; rekordy automatycznie dopasowują wysokość do liczby zestawów
- **Dodawanie własnych liczb** — możliwość ręcznego wprowadzenia zestawu zamiast losowania
- **Kopiowanie do schowka** — szybkie skopiowanie wylosowanych liczb
- **Tryb jasny / ciemny** — przełączanie motywu
- **Splash screen** — ekran powitalny z informacjami o aplikacji

---

## Stack technologiczny

| Warstwa   | Technologia                     |
|-----------|---------------------------------|
| Język     | Python 3.14                     |
| UI        | Flet (Flutter-based, cross-platform) |
| Baza danych | SQLite3 (stdlib)              |
| Launcher  | `.bat` (Windows)                |

---

## Wymagania

- Python 3.12+
- [Flet](https://flet.dev/) (`pip install flet`)

---

## Uruchomienie

### Windows (zalecane)

Uruchom plik `Uruchom_Lottomat.bat` — automatycznie aktywuje środowisko wirtualne i startuje aplikację.

### Ręcznie (PowerShell / bash)

```bash
# Klonuj repozytorium
git clone https://github.com/ZuraffPL/lottomat.git
cd lottomat

# Utwórz i aktywuj środowisko wirtualne
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # Linux/macOS

# Zainstaluj zależności
pip install flet

# Uruchom
python lottomat_flet.py
```

---

## Struktura projektu

```
lottomat_flet.py      → główna klasa LottomatApp (UI + logika)
archive_tab_flet.py   → widok archiwum (ArchiveTabFlet)
database.py           → warstwa danych SQLite (LottomatDatabase)
Uruchom_Lottomat.bat  → launcher Windows
```

---

## Autor

**Marcin Żurawicz**

---

## Historia wersji

| Wersja | Zmiany |
|--------|--------|
| 1.2 | Kupony wielozestawowe (do 10 zestawów/zakład), auto-wysokość wierszy w archiwum, zastąpienie DataTable niestandardową listą |
| 1.1 | Archiwum zakładów, statystyki, dodawanie własnych liczb, tryb ciemny |
| 1.0 | Pierwsza wersja: generator Lotto i Eurojackpot |

---

## Licencja

Ten projekt jest udostępniony na licencji [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).  
Możesz swobodnie używać, kopiować, modyfikować i dystrybuować projekt, pod warunkiem podania autorstwa.
