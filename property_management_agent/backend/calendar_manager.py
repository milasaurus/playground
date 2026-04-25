"""
Calendar management module.
Handles CRUD operations and search functionality for calendar events.
"""

import sqlite3
import uuid
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, NewType


EventId = NewType('EventId', str)


@dataclass
class Event:
    """Represents a calendar event."""
    event_id: EventId
    name: str
    start_timestamp: str  # ISO format datetime
    end_timestamp: str    # ISO format datetime
    guests: list[str]     # List of guest email addresses
    created_at: str
    updated_at: str


class CalendarManager:
    """Manages calendar events."""

    def __init__(self, db_path: str = "calendar.db"):
        """
        Initialize the CalendarManager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    start_timestamp TEXT NOT NULL,
                    end_timestamp TEXT NOT NULL,
                    guests TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_start_timestamp
                ON events(start_timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_end_timestamp
                ON events(end_timestamp)
            """)
            conn.commit()

    def _row_to_event(self, row: tuple) -> Event:
        """
        Convert a database row to an Event object.

        Args:
            row: Database row tuple

        Returns:
            Event object
        """
        return Event(
            EventId(row[0]),
            row[1],
            row[2],
            row[3],
            json.loads(row[4]),
            row[5],
            row[6]
        )

    def create_event(
        self,
        name: str,
        start_timestamp: datetime,
        end_timestamp: datetime,
        guests: Optional[list[str]] = None
    ) -> Event:
        """
        Create a new calendar event.

        Args:
            name: Event name/title
            start_timestamp: Event start time
            end_timestamp: Event end time
            guests: List of guest email addresses (optional)

        Returns:
            Created Event object
        """
        event_id = EventId(str(uuid.uuid4()))
        now = datetime.utcnow().isoformat()
        guests = guests or []

        event = Event(
            event_id=event_id,
            name=name,
            start_timestamp=start_timestamp.isoformat(),
            end_timestamp=end_timestamp.isoformat(),
            guests=guests,
            created_at=now,
            updated_at=now
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.name,
                event.start_timestamp,
                event.end_timestamp,
                json.dumps(event.guests),
                event.created_at,
                event.updated_at
            ))
            conn.commit()

        return event

    def get_event(self, event_id: EventId) -> Optional[Event]:
        """
        Retrieve an event by ID.

        Args:
            event_id: Unique event identifier

        Returns:
            Event object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, name, start_timestamp, end_timestamp,
                       guests, created_at, updated_at
                FROM events
                WHERE event_id = ?
            """, (event_id,))

            row = cursor.fetchone()
            if row:
                return self._row_to_event(row)
            return None

    def update_event(
        self,
        event_id: EventId,
        name: Optional[str] = None,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
        guests: Optional[list[str]] = None
    ) -> Optional[Event]:
        """
        Update an event with new values.

        Args:
            event_id: Unique event identifier
            name: New event name (optional)
            start_timestamp: New start time (optional)
            end_timestamp: New end time (optional)
            guests: New guest list (optional)

        Returns:
            Updated Event object if found, None otherwise
        """
        updates = {}

        if name is not None:
            updates['name'] = name
        if start_timestamp is not None:
            updates['start_timestamp'] = start_timestamp.isoformat()
        if end_timestamp is not None:
            updates['end_timestamp'] = end_timestamp.isoformat()
        if guests is not None:
            updates['guests'] = json.dumps(guests)

        if not updates:
            return self.get_event(event_id)

        updates['updated_at'] = datetime.utcnow().isoformat()

        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [event_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE events
                SET {set_clause}
                WHERE event_id = ?
            """, values)
            conn.commit()

            if cursor.rowcount == 0:
                return None

        return self.get_event(event_id)

    def delete_event(self, event_id: EventId) -> bool:
        """
        Delete an event.

        Args:
            event_id: Unique event identifier

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM events
                WHERE event_id = ?
            """, (event_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Event]:
        """
        List all events within a time range.

        Args:
            start_time: Range start time
            end_time: Range end time

        Returns:
            List of Event objects within the range
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, name, start_timestamp, end_timestamp,
                       guests, created_at, updated_at
                FROM events
                WHERE start_timestamp <= ?
                  AND end_timestamp >= ?
                ORDER BY start_timestamp
            """, (
                end_time.isoformat(),
                start_time.isoformat()
            ))

            return [self._row_to_event(row) for row in cursor.fetchall()]

    def search_by_name(self, search_term: str) -> List[Event]:
        """
        Search events by name.

        Args:
            search_term: Text to search for in event names

        Returns:
            List of matching Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, name, start_timestamp, end_timestamp,
                       guests, created_at, updated_at
                FROM events
                WHERE name LIKE ?
                ORDER BY start_timestamp
            """, (f"%{search_term}%",))

            return [self._row_to_event(row) for row in cursor.fetchall()]

    def list_all_events(self) -> List[Event]:
        """
        Get all events.

        Returns:
            List of all Event objects ordered by start time
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, name, start_timestamp, end_timestamp,
                       guests, created_at, updated_at
                FROM events
                ORDER BY start_timestamp
            """)

            return [self._row_to_event(row) for row in cursor.fetchall()]

    def check_availability(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """
        Check if a time slot is available (no conflicting events).

        Args:
            start_time: Proposed start time
            end_time: Proposed end time

        Returns:
            True if the slot is available, False if there are conflicts
        """
        conflicts = self.list_events_in_range(start_time, end_time)
        return len(conflicts) == 0

    def search_by_guest(self, guest_email: str) -> List[Event]:
        """
        Search events by guest email address.

        Args:
            guest_email: Email address to search for in guest lists

        Returns:
            List of Event objects that include the specified guest
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, name, start_timestamp, end_timestamp,
                       guests, created_at, updated_at
                FROM events
                ORDER BY start_timestamp
            """)

            # Filter events where guest_email appears in the guests list
            events = []
            for row in cursor.fetchall():
                event = self._row_to_event(row)
                if guest_email in event.guests:
                    events.append(event)

            return events
