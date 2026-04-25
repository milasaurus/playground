"""
Listings management module.
Handles CRUD operations and search functionality for property listings.
"""

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Listing:
    """Represents a rental property listing."""
    listing_id: str
    description: str
    address: str
    monthly_rent: int
    bedrooms: int
    bathrooms: int
    created_at: str
    updated_at: str


class ListingsManager:
    """Manages property listings."""

    def __init__(self, db_path: str = "listings.db"):
        """
        Initialize the ListingsManager.

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
                CREATE TABLE IF NOT EXISTS listings (
                    listing_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    address TEXT NOT NULL,
                    monthly_rent INTEGER NOT NULL,
                    bedrooms INTEGER NOT NULL,
                    bathrooms INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def create_listing(
        self,
        description: str,
        address: str,
        monthly_rent: int,
        bedrooms: int,
        bathrooms: int
    ) -> Listing:
        """
        Create a new listing.

        Args:
            description: Property description
            address: Property address
            monthly_rent: Monthly rental rate
            bedrooms: Number of bedrooms
            bathrooms: Number of bathrooms

        Returns:
            Created Listing object
        """
        listing_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        listing = Listing(
            listing_id=listing_id,
            description=description,
            address=address,
            monthly_rent=monthly_rent,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            created_at=now,
            updated_at=now
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO listings VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                listing.listing_id,
                listing.description,
                listing.address,
                listing.monthly_rent,
                listing.bedrooms,
                listing.bathrooms,
                listing.created_at,
                listing.updated_at
            ))
            conn.commit()

        return listing

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        """
        Retrieve a listing by ID.

        Args:
            listing_id: Unique listing identifier

        Returns:
            Listing object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT listing_id, description, address,
                       monthly_rent, bedrooms, bathrooms,
                       created_at, updated_at
                FROM listings
                WHERE listing_id = ?
            """, (listing_id,))

            row = cursor.fetchone()
            if row:
                return Listing(*row)
            return None

    def update_listing(
        self,
        listing_id: str,
        **kwargs
    ) -> Optional[Listing]:
        """
        Update a listing with new values.

        Args:
            listing_id: Unique listing identifier
            **kwargs: Fields to update (description, address, monthly_rent, etc.)

        Returns:
            Updated Listing object if found, None otherwise
        """
        allowed_fields = {
            'description', 'address', 'monthly_rent',
            'bedrooms', 'bathrooms'
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return self.get_listing(listing_id)

        updates['updated_at'] = datetime.utcnow().isoformat()

        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [listing_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE listings
                SET {set_clause}
                WHERE listing_id = ?
            """, values)
            conn.commit()

            if cursor.rowcount == 0:
                return None

        return self.get_listing(listing_id)

    def delete_listing(self, listing_id: str) -> bool:
        """
        Delete a listing.

        Args:
            listing_id: Unique listing identifier

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM listings
                WHERE listing_id = ?
            """, (listing_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search_by_description(self, search_term: str) -> List[Listing]:
        """
        Search listings by description text.

        Args:
            search_term: Text to search for in descriptions

        Returns:
            List of matching Listing objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT listing_id, description, address,
                       monthly_rent, bedrooms, bathrooms,
                       created_at, updated_at
                FROM listings
                WHERE description LIKE ?
            """, (f"%{search_term}%",))

            return [Listing(*row) for row in cursor.fetchall()]

    def search_listings(self, filters: Dict[str, Any]) -> List[Listing]:
        """
        Search listings by multiple criteria.

        Args:
            filters: Dictionary of field names and values to filter by
                    (e.g., {"bedrooms": 2, "monthly_rent": 2000})

        Returns:
            List of matching Listing objects
        """
        allowed_fields = {
            'monthly_rent', 'bedrooms', 'bathrooms'
        }

        conditions = []
        values = []

        for field, value in filters.items():
            if field in allowed_fields:
                conditions.append(f"{field} = ?")
                values.append(value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT listing_id, description, address,
                       monthly_rent, bedrooms, bathrooms,
                       created_at, updated_at
                FROM listings
                WHERE {where_clause}
            """, values)

            return [Listing(*row) for row in cursor.fetchall()]

    def list_all_listings(self) -> List[Listing]:
        """
        Get all listings for the owner.

        Returns:
            List of all Listing objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT listing_id, description, address,
                       monthly_rent, bedrooms, bathrooms,
                       created_at, updated_at
                FROM listings
            """)

            return [Listing(*row) for row in cursor.fetchall()]

    def search_by_rent_range(
        self,
        min_rent: Optional[int] = None,
        max_rent: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Listing]:
        """
        Search listings within a rent range with additional filters.

        Args:
            min_rent: Minimum monthly rent (inclusive)
            max_rent: Maximum monthly rent (inclusive)
            filters: Additional filters (e.g., {"bedrooms": 2, "bathrooms": 1})
                    Note: monthly_rent is excluded from filters as it's handled by min_rent/max_rent

        Returns:
            List of Listing objects matching the criteria
        """
        conditions = []
        values = []

        # Handle rent range
        if min_rent is not None:
            conditions.append("monthly_rent >= ?")
            values.append(min_rent)

        if max_rent is not None:
            conditions.append("monthly_rent <= ?")
            values.append(max_rent)

        # Handle additional filters (excluding monthly_rent)
        if filters:
            allowed_fields = {'bedrooms', 'bathrooms'}

            for field, value in filters.items():
                if field in allowed_fields:
                    conditions.append(f"{field} = ?")
                    values.append(value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT listing_id, description, address,
                       monthly_rent, bedrooms, bathrooms,
                       created_at, updated_at
                FROM listings
                WHERE {where_clause}
            """, values)

            return [Listing(*row) for row in cursor.fetchall()]
