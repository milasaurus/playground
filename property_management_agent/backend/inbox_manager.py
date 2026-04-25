"""
Inbox management module.
Handles CRUD operations and search functionality for email messages.
"""

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class EmailMessage:
    """Represents an email message."""
    message_id: str
    contact_email: str  # The other person (sender if incoming, recipient if outgoing)
    is_incoming: bool   # True if received, False if sent
    subject: str
    body: str
    timestamp: str      # ISO format datetime


class InboxManager:
    """Manages email messages for a user's inbox."""

    def __init__(self, db_path: str = "inbox.db"):
        """
        Initialize the InboxManager.

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
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    contact_email TEXT NOT NULL,
                    is_incoming INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contact_email
                ON messages(contact_email)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON messages(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_incoming
                ON messages(is_incoming)
            """)
            conn.commit()

    def _row_to_message(self, row: tuple) -> EmailMessage:
        """
        Convert a database row to an EmailMessage object.

        Args:
            row: Database row tuple

        Returns:
            EmailMessage object
        """
        return EmailMessage(
            message_id=row[0],
            contact_email=row[1],
            is_incoming=bool(row[2]),
            subject=row[3],
            body=row[4],
            timestamp=row[5]
        )

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        timestamp: Optional[datetime] = None
    ) -> EmailMessage:
        """
        Send an email (create outgoing message).

        Args:
            recipient: Email address of the recipient
            subject: Email subject
            body: Email body
            timestamp: Message timestamp (defaults to now)

        Returns:
            Created EmailMessage object
        """
        message_id = str(uuid.uuid4())
        if timestamp is None:
            timestamp = datetime.utcnow()

        message = EmailMessage(
            message_id=message_id,
            contact_email=recipient,
            is_incoming=False,
            subject=subject,
            body=body,
            timestamp=timestamp.isoformat()
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.contact_email,
                int(message.is_incoming),
                message.subject,
                message.body,
                message.timestamp
            ))
            conn.commit()

        return message

    def receive_email(
        self,
        sender: str,
        subject: str,
        body: str,
        timestamp: Optional[datetime] = None
    ) -> EmailMessage:
        """
        Receive an email (create incoming message).

        Args:
            sender: Email address of the sender
            subject: Email subject
            body: Email body
            timestamp: Message timestamp (defaults to now)

        Returns:
            Created EmailMessage object
        """
        message_id = str(uuid.uuid4())
        if timestamp is None:
            timestamp = datetime.utcnow()

        message = EmailMessage(
            message_id=message_id,
            contact_email=sender,
            is_incoming=True,
            subject=subject,
            body=body,
            timestamp=timestamp.isoformat()
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.contact_email,
                int(message.is_incoming),
                message.subject,
                message.body,
                message.timestamp
            ))
            conn.commit()

        return message

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """
        Retrieve a message by ID.

        Args:
            message_id: Unique message identifier

        Returns:
            EmailMessage object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_id, contact_email, is_incoming, subject,
                       body, timestamp
                FROM messages
                WHERE message_id = ?
            """, (message_id,))

            row = cursor.fetchone()
            if row:
                return self._row_to_message(row)
            return None

    def delete_email(self, message_id: str) -> bool:
        """
        Delete an email message.

        Args:
            message_id: Unique message identifier

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages
                WHERE message_id = ?
            """, (message_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search_messages(
        self,
        contact_email: Optional[str] = None,
        is_incoming: Optional[bool] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[EmailMessage]:
        """
        Search messages by multiple criteria.

        Args:
            contact_email: Filter by contact email (sender or recipient)
            is_incoming: Filter by direction (True=received, False=sent, None=both)
            keyword: Search keyword in subject or body (case-insensitive)
            start_date: Filter messages on or after this date
            end_date: Filter messages on or before this date

        Returns:
            List of matching EmailMessage objects
        """
        conditions = []
        values = []

        if contact_email is not None:
            conditions.append("contact_email = ?")
            values.append(contact_email)

        if is_incoming is not None:
            conditions.append("is_incoming = ?")
            values.append(int(is_incoming))

        if keyword is not None:
            conditions.append("(subject LIKE ? OR body LIKE ?)")
            keyword_pattern = f"%{keyword}%"
            values.append(keyword_pattern)
            values.append(keyword_pattern)

        if start_date is not None:
            conditions.append("timestamp >= ?")
            values.append(start_date.isoformat())

        if end_date is not None:
            conditions.append("timestamp <= ?")
            values.append(end_date.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT message_id, contact_email, is_incoming, subject,
                       body, timestamp
                FROM messages
                WHERE {where_clause}
                ORDER BY timestamp DESC
            """, values)

            return [self._row_to_message(row) for row in cursor.fetchall()]

    def list_all_messages(self) -> List[EmailMessage]:
        """
        Get all messages ordered by timestamp (most recent first).

        Returns:
            List of all EmailMessage objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_id, contact_email, is_incoming, subject,
                       body, timestamp
                FROM messages
                ORDER BY timestamp DESC
            """)

            return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_inbox(self) -> List[EmailMessage]:
        """
        Get all incoming messages.

        Returns:
            List of incoming EmailMessage objects
        """
        return self.search_messages(is_incoming=True)

    def get_sent(self) -> List[EmailMessage]:
        """
        Get all sent messages.

        Returns:
            List of outgoing EmailMessage objects
        """
        return self.search_messages(is_incoming=False)

    def get_conversation(self, contact_email: str) -> List[EmailMessage]:
        """
        Get all messages to/from a specific contact.

        Args:
            contact_email: Email address of the contact

        Returns:
            List of EmailMessage objects ordered by timestamp
        """
        return self.search_messages(contact_email=contact_email)

    def get_contacts(self) -> List[str]:
        """
        Get list of all unique contact email addresses.

        Returns:
            List of unique email addresses
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT contact_email
                FROM messages
                ORDER BY contact_email
            """)

            return [row[0] for row in cursor.fetchall()]

    def get_recent_messages(self, limit: int = 10) -> List[EmailMessage]:
        """
        Get the most recent messages.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of recent EmailMessage objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT message_id, contact_email, is_incoming, subject,
                       body, timestamp
                FROM messages
                ORDER BY timestamp DESC
                LIMIT {limit}
            """)

            return [self._row_to_message(row) for row in cursor.fetchall()]
