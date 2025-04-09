import sqlite3
from typing import Iterable, Self, Sequence
from dataclasses import asdict
from pathlib import Path

from .models import MediaItem


class Storage:
    def __init__(self, db_path: str | Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.conn.close()

    def _create_tables(self) -> None:
        """Create the remote_media table if it doesn't exist."""
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS remote_media (
            media_key TEXT PRIMARY KEY,
            file_name TEXT,
            dedup_key TEXT,
            is_canonical BOOL,
            type INTEGER,
            caption TEXT,
            collection_id TEXT,
            size_bytes INTEGER,
            quota_charged_bytes INTEGER,
            origin TEXT,
            content_version INTEGER,
            utc_timestamp INTEGER,
            server_creation_timestamp INTEGER,
            timezone_offset INTEGER,
            width INTEGER,
            height INTEGER,
            remote_url TEXT,
            upload_status INTEGER,
            trash_timestamp INTEGER,
            is_archived INTEGER,
            is_favorite INTEGER,
            is_locked INTEGER,
            is_original_quality INTEGER,
            latitude REAL,
            longitude REAL,
            location_name TEXT,
            location_id TEXT,
            is_edited INTEGER,
            make TEXT,
            model TEXT,
            aperture REAL,
            shutter_speed REAL,
            iso INTEGER,
            focal_length REAL,
            duration INTEGER,
            capture_frame_rate REAL,
            encoded_frame_rate REAL,
            is_micro_video INTEGER,
            micro_video_width INTEGER,
            micro_video_height INTEGER
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_token TEXT,
            page_token TEXT,
            init_complete INTEGER
        )
        """)

        self.conn.execute("""
        INSERT OR IGNORE INTO state (id, state_token, page_token, init_complete)
        VALUES (1, '', '', 0)
        """)
        self.conn.commit()

    def update(self, items: Iterable[MediaItem]) -> None:
        """Insert or update multiple MediaItems in the database."""
        if not items:
            return

        # Convert dataclass objects to dictionaries
        items_dicts = [asdict(item) for item in items]

        # Prepare the SQL statement with all fields
        columns = items_dicts[0].keys()
        placeholders = ", ".join("?" * len(columns))
        columns_str = ", ".join(columns)
        updates = ", ".join(f"{col}=excluded.{col}" for col in columns if col != "media_key")

        sql = f"""
        INSERT INTO remote_media ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT(media_key) DO UPDATE SET {updates}
        """

        # Prepare the values for each item
        values = [tuple(item[col] for col in columns) for item in items_dicts]

        # Execute in a transaction
        with self.conn:
            self.conn.executemany(sql, values)

    def delete(self, media_keys: Sequence[str]) -> None:
        """
        Delete multiple rows by their media_key.

        Args:
            media_keys: A sequence of media_key values to delete
        """
        if not media_keys:
            return

        # Create a temporary table with the keys to delete
        sql = """
        DELETE FROM remote_media
        WHERE media_key IN ({})
        """.format(",".join(["?"] * len(media_keys)))

        # Execute in a transaction
        with self.conn:
            self.conn.execute(sql, media_keys)

    def get_state_tokens(self) -> tuple[str, str]:
        """
        Get both state tokens as a tuple (state_token, page_token).
        Returns ('', '') if no tokens are stored.
        """
        cursor = self.conn.execute("""
        SELECT state_token, page_token FROM state WHERE id = 1
        """)
        return cursor.fetchone() or ("", "")

    def update_state_tokens(self, state_token: str | None = None, page_token: str | None = None) -> None:
        """
        Update one or both state tokens.
        Pass None to leave a token unchanged.
        """
        updates = []
        params = []

        if state_token is not None:
            updates.append("state_token = ?")
            params.append(state_token)
        if page_token is not None:
            updates.append("page_token = ?")
            params.append(page_token)

        if updates:
            sql = f"UPDATE state SET {', '.join(updates)} WHERE id = 1"
            with self.conn:
                self.conn.execute(sql, params)

    def get_init_state(self) -> bool:
        """ """
        cursor = self.conn.execute("""
        SELECT init_complete FROM state WHERE id = 1
        """)
        return cursor.fetchone()[0] or False

    def set_init_state(self, state: int) -> None:
        """ """
        with self.conn:
            self.conn.execute(f"UPDATE state SET init_complete = {state} WHERE id = 1")

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
