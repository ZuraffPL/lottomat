"""Moduł do zarządzania bazą danych archiwum"""
import sqlite3
from datetime import datetime

type Record = tuple[int, str, str, str | None, str | None, str | None, str, float | None, str | None, float | None]


class LottomatDatabase:
    def __init__(self, db_name: str = "lottomat_archive.db") -> None:
        """Inicjalizacja połączenia z bazą danych"""
        self.db_name = db_name
        self.create_tables()
    
    def create_tables(self) -> None:
        """Tworzenie tabel w bazie danych"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_type TEXT NOT NULL,
                    numbers TEXT NOT NULL,
                    extra_numbers TEXT,
                    actual_numbers TEXT,
                    actual_extra_numbers TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            # Migracja: dodaj nowe kolumny jeśli nie istnieją
            self._migrate_database(cursor)
            self._ensure_default_settings(cursor)
    
    def _migrate_database(self, cursor: sqlite3.Cursor) -> None:
        """Migracja bazy danych - dodanie brakujących kolumn"""
        cursor.execute("PRAGMA table_info(archive)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'actual_numbers' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN actual_numbers TEXT")

        if 'actual_extra_numbers' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN actual_extra_numbers TEXT")

        if 'prize_amount' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN prize_amount REAL")

        if 'prize_currency' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN prize_currency TEXT")

        if 'ticket_price' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN ticket_price REAL")
            # Wypełnij istniejące rekordy domyślnymi cenami zakładu
            cursor.execute("UPDATE archive SET ticket_price = 4.0 WHERE game_type = 'Lotto' AND ticket_price IS NULL")
            cursor.execute("UPDATE archive SET ticket_price = 12.5 WHERE game_type = 'Eurojackpot' AND ticket_price IS NULL")

    def _ensure_default_settings(self, cursor: sqlite3.Cursor) -> None:
        """Ustawia domyślne wartości w tabeli settings jeśli nie istnieją"""
        defaults = [("lotto_price", "4.0"), ("eurojackpot_price", "12.5")]
        for key, value in defaults:
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def get_setting(self, key: str) -> str | None:
        """Pobiera wartość ustawienia"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_setting(self, key: str, value: str) -> None:
        """Zapisuje wartość ustawienia"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def get_lotto_price(self) -> float:
        """Pobiera aktualną cenę zakładu Lotto"""
        val = self.get_setting("lotto_price")
        return float(val) if val is not None else 4.0

    def get_eurojackpot_price(self) -> float:
        """Pobiera aktualną cenę zakładu Eurojackpot"""
        val = self.get_setting("eurojackpot_price")
        return float(val) if val is not None else 12.5

    def _get_next_id(self, cursor: sqlite3.Cursor) -> int:
        """Zwraca najniższe wolne ID (wypełnia luki po usuniętych rekordach)"""
        cursor.execute("SELECT id FROM archive ORDER BY id")
        existing: set[int] = {row[0] for row in cursor.fetchall()}
        i = 1
        while i in existing:
            i += 1
        return i
    
    def add_lotto_record(self, sets: list[list[int]], ticket_price: float | None = None) -> int:
        """Dodanie rekordu Lotto do archiwum. `sets` to lista zestawów 6 liczb (maks. 10).
        Format zapisu: zestawy oddzielone '|', liczby wewnątrz zestawu oddzielone ','.
        """
        if ticket_price is None:
            ticket_price = self.get_lotto_price()
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            numbers_str = "|".join(",".join(str(n) for n in s) for s in sets)
            record_id = self._get_next_id(cursor)
            cursor.execute("""
                INSERT INTO archive (id, game_type, numbers, created_date, ticket_price)
                VALUES (?, ?, ?, ?, ?)
            """, (record_id, "Lotto", numbers_str, datetime.now().isoformat(timespec='seconds'), ticket_price))
            return record_id

    def add_eurojackpot_record(self, main_sets: list[list[int]], star_sets: list[list[int]], ticket_price: float | None = None) -> int:
        """Dodanie rekordu Eurojackpot do archiwum.
        `main_sets` – lista zestawów liczb głównych; `star_sets` – lista zestawów gwiazd.
        Zestawy main_sets[i] i star_sets[i] tworzą parę. Maks. 10 zestawów.
        """
        if ticket_price is None:
            ticket_price = self.get_eurojackpot_price()
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            main_str = "|".join(",".join(str(n) for n in s) for s in main_sets)
            stars_str = "|".join(",".join(str(n) for n in s) for s in star_sets)
            record_id = self._get_next_id(cursor)
            cursor.execute("""
                INSERT INTO archive (id, game_type, numbers, extra_numbers, created_date, ticket_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (record_id, "Eurojackpot", main_str, stars_str, datetime.now().isoformat(timespec='seconds'), ticket_price))
            return record_id
    def get_all_records(self) -> list[Record]:
        """Pobranie wszystkich rekordów z archiwum"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, game_type, numbers, extra_numbers, actual_numbers, actual_extra_numbers, created_date,
                       prize_amount, prize_currency, ticket_price
                FROM archive
                ORDER BY created_date DESC
            """)
            return cursor.fetchall()
    
    def get_records_by_game(self, game_type: str) -> list[Record]:
        """Pobranie rekordów dla konkretnej gry"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, game_type, numbers, extra_numbers, actual_numbers, actual_extra_numbers, created_date,
                       prize_amount, prize_currency, ticket_price
                FROM archive
                WHERE game_type = ?
                ORDER BY created_date DESC
            """, (game_type,))
            return cursor.fetchall()
    
    def delete_record(self, record_id: int) -> None:
        """Usunięcie rekordu z archiwum"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM archive WHERE id = ?", (record_id,))
    
    def clear_all(self) -> None:
        """Wyczyszczenie całego archiwum"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM archive")
    
    def update_actual_result(self, record_id: int, actual_numbers: str, actual_extra_numbers: str | None = None) -> None:
        """Aktualizacja faktycznego wyniku losowania"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE archive 
                SET actual_numbers = ?, actual_extra_numbers = ?
                WHERE id = ?
            """, (actual_numbers, actual_extra_numbers, record_id))

    def update_prize_amount(self, record_id: int, prize_amount: float, prize_currency: str) -> None:
        """Aktualizacja kwoty wygranej dla rekordu"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE archive
                SET prize_amount = ?, prize_currency = ?
                WHERE id = ?
            """, (prize_amount, prize_currency, record_id))
