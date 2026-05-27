"""Moduł do zarządzania bazą danych archiwum"""
import sqlite3
from datetime import datetime

type Record = tuple[int, str, str, str | None, str | None, str | None, str]


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
            # Migracja: dodaj nowe kolumny jeśli nie istnieją
            self._migrate_database(cursor)
    
    def _migrate_database(self, cursor: sqlite3.Cursor) -> None:
        """Migracja bazy danych - dodanie brakujących kolumn"""
        # Pobierz listę kolumn z tabeli archive
        cursor.execute("PRAGMA table_info(archive)")
        columns = [column[1] for column in cursor.fetchall()]

        # Dodaj kolumnę actual_numbers jeśli nie istnieje
        if 'actual_numbers' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN actual_numbers TEXT")

        # Dodaj kolumnę actual_extra_numbers jeśli nie istnieje
        if 'actual_extra_numbers' not in columns:
            cursor.execute("ALTER TABLE archive ADD COLUMN actual_extra_numbers TEXT")

    def _get_next_id(self, cursor: sqlite3.Cursor) -> int:
        """Zwraca najniższe wolne ID (wypełnia luki po usuniętych rekordach)"""
        cursor.execute("SELECT id FROM archive ORDER BY id")
        existing: set[int] = {row[0] for row in cursor.fetchall()}
        i = 1
        while i in existing:
            i += 1
        return i
    
    def add_lotto_record(self, sets: list[list[int]]) -> int:
        """Dodanie rekordu Lotto do archiwum. `sets` to lista zestawów 6 liczb (maks. 10).
        Format zapisu: zestawy oddzielone '|', liczby wewnątrz zestawu oddzielone ','.
        """
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            numbers_str = "|".join(",".join(str(n) for n in s) for s in sets)
            record_id = self._get_next_id(cursor)
            cursor.execute("""
                INSERT INTO archive (id, game_type, numbers, created_date)
                VALUES (?, ?, ?, ?)
            """, (record_id, "Lotto", numbers_str, datetime.now().isoformat(timespec='seconds')))
            return record_id

    def add_eurojackpot_record(self, main_sets: list[list[int]], star_sets: list[list[int]]) -> int:
        """Dodanie rekordu Eurojackpot do archiwum.
        `main_sets` – lista zestawów liczb głównych; `star_sets` – lista zestawów gwiazd.
        Zestawy main_sets[i] i star_sets[i] tworzą parę. Maks. 10 zestawów.
        """
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            main_str = "|".join(",".join(str(n) for n in s) for s in main_sets)
            stars_str = "|".join(",".join(str(n) for n in s) for s in star_sets)
            record_id = self._get_next_id(cursor)
            cursor.execute("""
                INSERT INTO archive (id, game_type, numbers, extra_numbers, created_date)
                VALUES (?, ?, ?, ?, ?)
            """, (record_id, "Eurojackpot", main_str, stars_str, datetime.now().isoformat(timespec='seconds')))
            return record_id
    def get_all_records(self) -> list[Record]:
        """Pobranie wszystkich rekordów z archiwum"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, game_type, numbers, extra_numbers, actual_numbers, actual_extra_numbers, created_date
                FROM archive
                ORDER BY created_date DESC
            """)
            return cursor.fetchall()
    
    def get_records_by_game(self, game_type: str) -> list[Record]:
        """Pobranie rekordów dla konkretnej gry"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, game_type, numbers, extra_numbers, actual_numbers, actual_extra_numbers, created_date
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
