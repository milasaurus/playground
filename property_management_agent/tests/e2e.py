import os
import sys
from datetime import datetime, timedelta
import pytest

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.inbox_manager import InboxManager
from backend.listings_manager import ListingsManager
from backend.calendar_manager import CalendarManager
from api import process_email, process_query


# Database paths for testing
INBOX_DB = "test_inbox.db"
LISTINGS_DB = "test_listings.db"
CALENDAR_DB = "test_calendar.db"


def wipe_databases():
    """Remove all test database files."""
    for db_path in [INBOX_DB, LISTINGS_DB, CALENDAR_DB]:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def managers():
    """Initialize fresh manager instances with test databases."""
    # Setup: wipe databases before each test
    wipe_databases()

    inbox = InboxManager(INBOX_DB)
    listings = ListingsManager(LISTINGS_DB)
    calendar = CalendarManager(CALENDAR_DB)

    yield inbox, listings, calendar

    # Teardown: wipe databases after each test
    wipe_databases()


# ============================================================================
# process_email Tests
# ============================================================================

def test_email_apartment_inquiry(managers):
    """Test: Customer asks about available 2BR apartments under $3000."""
    print("\n" + "="*70)
    print("TEST: Email - Apartment Inquiry")
    print("="*70)

    inbox, listings, calendar = managers

    # Setup: Create some listings
    listings.create_listing(
        description="Spacious 2BR apartment with balcony in downtown",
        address="123 Oak Street",
        monthly_rent=2500,
        bedrooms=2,
        bathrooms=2
    )
    listings.create_listing(
        description="Cozy 2BR apartment near park",
        address="456 Maple Ave",
        monthly_rent=2800,
        bedrooms=2,
        bathrooms=1
    )
    listings.create_listing(
        description="Luxury 2BR with city views",
        address="789 Pine Road",
        monthly_rent=3500,
        bedrooms=2,
        bathrooms=2
    )
    listings.create_listing(
        description="Studio apartment downtown",
        address="321 Elm Street",
        monthly_rent=1800,
        bedrooms=1,
        bathrooms=1
    )

    # Execute
    sender = "customer@example.com"
    subject = "Looking for apartment"
    body = "What 2 bedroom apartments do you have available right now below $3000?"

    response = process_email(subject, body, sender)
    print(f"\nSender: {sender}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"\nResponse: {response}")

    # Verify
    inbox_messages = inbox.list_all_messages()
    assert len(inbox_messages) == 1, "Should have recorded 1 email in inbox"

    recorded_message = inbox_messages[0]
    assert recorded_message.contact_email == sender, "Email sender should match"
    assert recorded_message.subject == subject, "Email subject should match"
    assert recorded_message.is_incoming is True, "Email should be incoming"

    assert "123 Oak Street" in response, "Should include 123 Oak Street"
    assert "456 Maple Ave" in response, "Should include 456 Maple Ave"


def test_email_schedule_viewing(managers):
    """Test: Customer requests to schedule a viewing."""
    print("\n" + "="*70)
    print("TEST: Email - Schedule Viewing")
    print("="*70)

    inbox, listings, calendar = managers

    # Setup: Create a listing
    listings.create_listing(
        description="Beautiful 3BR house with garden",
        address="123 Oak Street",
        monthly_rent=3200,
        bedrooms=3,
        bathrooms=2
    )

    # Execute
    sender = "interested@example.com"
    subject = "Viewing request"
    body = "Please schedule a viewing at 123 Oak Street on Friday at 4 PM?"

    response = process_email(subject, body, sender)
    print(f"\nSender: {sender}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"\nResponse: {response}")

    # Verify
    inbox_messages = inbox.list_all_messages()
    assert len(inbox_messages) == 1, "Should have recorded 1 email in inbox"

    # Expected: Should create a calendar event for the viewing
    # Note: Actual implementation would parse "Friday at 4 PM" and create event
    events = calendar.list_all_events()
    assert len(events) == 1, "Should have created 1 calendar event for the viewing"

    event = events[0]
    assert "123 Oak Street" in event.name, "Event name should contain the address"
    assert sender in event.guests, f"Event should include {sender} as a guest"


def test_email_cancel_showing(managers):
    """Test: Customer cancels their showing for tomorrow."""
    print("\n" + "="*70)
    print("TEST: Email - Cancel Showing")
    print("="*70)

    inbox, listings, calendar = managers

    # Setup: Create a showing for tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_4pm = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)
    tomorrow_5pm = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)

    calendar.create_event(
        name="Showing at 456 Maple Ave for john@example.com",
        start_timestamp=tomorrow_4pm,
        end_timestamp=tomorrow_5pm,
        guests=["john@example.com"]
    )

    # Execute
    sender = "john@example.com"
    subject = "Need to cancel"
    body = "Just wanted to let you know that I found an apartment, so cancel my showing tomorrow"

    response = process_email(subject, body, sender)
    print(f"\nSender: {sender}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"\nResponse: {response}")

    # Verify
    inbox_messages = inbox.list_all_messages()
    assert len(inbox_messages) == 1, "Should have recorded 1 email in inbox"

    # Expected: Event should be deleted
    remaining_events = calendar.list_all_events()
    assert len(remaining_events) == 0, "Event should have been cancelled/deleted"


# ============================================================================
# process_query Tests
# ============================================================================

def test_query_delete_listing(managers):
    """Test: Internal query to delete a listing."""
    print("\n" + "="*70)
    print("TEST: Query - Delete Listing")
    print("="*70)

    inbox, listings, calendar = managers

    # Setup: Create a listing to delete
    listings.create_listing(
        description="Old listing to be removed",
        address="123 Oak Street",
        monthly_rent=2500,
        bedrooms=2,
        bathrooms=2
    )

    # Execute
    query = "Can you delete the listing at 123 Oak Street"
    response = process_query(query)
    print(f"\nQuery: {query}")
    print(f"\nResponse: {response}")

    # Verify
    all_listings = listings.list_all_listings()
    assert len(all_listings) == 0, "Listing should have been deleted"

    # Double check - search for specific address
    oak_street = [listing for listing in all_listings if "123 Oak Street" in listing.address]
    assert len(oak_street) == 0, "No listings at 123 Oak Street should remain"


def test_query_reschedule_appointment(managers):
    """Test: Internal query to move an appointment."""
    print("\n" + "="*70)
    print("TEST: Query - Reschedule Appointment")
    print("="*70)

    inbox, listings, calendar = managers

    # Setup: Create an appointment for tomorrow at 4 PM
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_4pm = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)
    tomorrow_5pm = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)

    calendar.create_event(
        name="Client meeting",
        start_timestamp=tomorrow_4pm,
        end_timestamp=tomorrow_5pm,
        guests=["client@example.com"]
    )

    # Execute
    query = "Can you move my appointment at 4 PM tomorrow to 5 PM"
    response = process_query(query)
    print(f"\nQuery: {query}")
    print(f"\nResponse: {response}")

    # Verify
    events = calendar.list_all_events()
    assert len(events) == 1, "Should still have exactly 1 event"

    # Expected: Event should still exist but with new time (5 PM)
    updated_event = events[0]
    start_time = datetime.fromisoformat(updated_event.start_timestamp)
    assert start_time.hour == 17, f"Event should now start at 5 PM (17:00), but starts at {start_time.hour}:00"


def test_query_view_schedule(managers):
    """Test: Internal query to view schedule for tomorrow."""
    print("\n" + "="*70)
    print("TEST: Query - View Schedule")
    print("="*70)

    inbox, listings, calendar = managers

    # Setup: Create multiple events for tomorrow
    tomorrow = datetime.now() + timedelta(days=1)

    event1_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    event1_end = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)
    calendar.create_event(
        name="Morning property viewing",
        start_timestamp=event1_start,
        end_timestamp=event1_end,
        guests=["client1@example.com"]
    )

    event2_start = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
    event2_end = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
    calendar.create_event(
        name="Afternoon inspection",
        start_timestamp=event2_start,
        end_timestamp=event2_end,
        guests=["inspector@example.com"]
    )

    event3_start = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)
    event3_end = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
    calendar.create_event(
        name="Client meeting",
        start_timestamp=event3_start,
        end_timestamp=event3_end,
        guests=["client2@example.com"]
    )

    # Execute
    query = "What's my schedule for tomorrow?"
    response = process_query(query)
    print(f"\nQuery: {query}")
    print(f"\nResponse: {response}")

    assert "Morning property viewing" in response, "Should have morning viewing"
    assert "Afternoon inspection" in response, "Should have afternoon inspection"
    assert "Client meeting" in response, "Should have client meeting"
