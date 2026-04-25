"""Listings tools — create, update, delete, search, and list property listings."""

import json
from dataclasses import asdict

from tools.base import Tool
from backend.listings_manager import ListingsManager


# All fields are required since a listing without an address or rent
# doesn't make sense. Uses **params to pass directly to the manager
# since the schema keys match the create_listing() signature exactly.
class CreateListingTool(Tool):
    def __init__(self, listings: ListingsManager):
        self.listings = listings
        super().__init__(
            name="create_listing",
            description="Create a new property listing.",
            input_schema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Property description"},
                    "address": {"type": "string", "description": "Property address"},
                    "monthly_rent": {"type": "integer", "description": "Monthly rental rate in dollars"},
                    "bedrooms": {"type": "integer", "description": "Number of bedrooms"},
                    "bathrooms": {"type": "integer", "description": "Number of bathrooms"},
                },
                "required": ["description", "address", "monthly_rent", "bedrooms", "bathrooms"],
            },
        )

    def run(self, params: dict) -> str:
        listing = self.listings.create_listing(**params)
        return json.dumps(asdict(listing))


# Partial update — only provided fields change. Uses **params because
# ListingsManager.update_listing() accepts **kwargs and filters to
# allowed fields internally, so extra keys are safely ignored.
class UpdateListingTool(Tool):
    def __init__(self, listings: ListingsManager):
        self.listings = listings
        super().__init__(
            name="update_listing",
            description="Update an existing property listing. Only provided fields are changed.",
            input_schema={
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "Unique listing identifier"},
                    "description": {"type": "string", "description": "New property description"},
                    "address": {"type": "string", "description": "New property address"},
                    "monthly_rent": {"type": "integer", "description": "New monthly rent in dollars"},
                    "bedrooms": {"type": "integer", "description": "New number of bedrooms"},
                    "bathrooms": {"type": "integer", "description": "New number of bathrooms"},
                },
                "required": ["listing_id"],
            },
        )

    def run(self, params: dict) -> str:
        listing = self.listings.update_listing(**params)
        return json.dumps(asdict(listing))


# Permanent deletion. The model needs the listing_id first — typically
# found via search_listings_by_description (searching by address text)
# or list_all_listings. The e2e tests verify the listing is fully gone
# from listings.list_all_listings() after deletion.
class DeleteListingTool(Tool):
    def __init__(self, listings: ListingsManager):
        self.listings = listings
        super().__init__(
            name="delete_listing",
            description="Delete a property listing by its ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "description": "Unique listing identifier"},
                },
                "required": ["listing_id"],
            },
        )

    def run(self, params: dict) -> str:
        return json.dumps({"deleted": self.listings.delete_listing(params["listing_id"])})


# Searches description text (not address). Uses LIKE under the hood, so
# it's case-insensitive substring matching. The model can use this to find
# listings by address since the description often includes location info,
# but for address-specific lookups list_all_listings may be more reliable.
class SearchListingsByDescriptionTool(Tool):
    def __init__(self, listings: ListingsManager):
        self.listings = listings
        super().__init__(
            name="search_listings_by_description",
            description="Search property listings by description text.",
            input_schema={
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "Text to search for in descriptions"},
                },
                "required": ["search_term"],
            },
        )

    def run(self, params: dict) -> str:
        return json.dumps([asdict(listing) for listing in self.listings.search_by_description(params["search_term"])])


# The main tool for customer inquiries like "2BR under $3000". All params
# are optional so the model can filter by rent alone, bedrooms alone, or
# any combination. Bedroom/bathroom filters are extracted into a separate
# dict because ListingsManager.search_by_rent_range() expects them as a
# filters kwarg rather than top-level args.
class SearchListingsByRentRangeTool(Tool):
    def __init__(self, listings: ListingsManager):
        self.listings = listings
        super().__init__(
            name="search_listings_by_rent_range",
            description="Search property listings within a rent range, with optional bedroom/bathroom filters.",
            input_schema={
                "type": "object",
                "properties": {
                    "min_rent": {"type": "integer", "description": "Minimum monthly rent (inclusive)"},
                    "max_rent": {"type": "integer", "description": "Maximum monthly rent (inclusive)"},
                    "bedrooms": {"type": "integer", "description": "Filter by number of bedrooms"},
                    "bathrooms": {"type": "integer", "description": "Filter by number of bathrooms"},
                },
                "required": [],
            },
        )

    def run(self, params: dict) -> str:
        filters = {k: params[k] for k in ("bedrooms", "bathrooms") if k in params} or None
        results = self.listings.search_by_rent_range(
            min_rent=params.get("min_rent"),
            max_rent=params.get("max_rent"),
            filters=filters,
        )
        return json.dumps([asdict(listing) for listing in results])


# Returns every listing. Used when the model needs a full overview or
# can't narrow down by description/rent. For this project's scope the
# dataset is small, so returning everything is fine.
class ListAllListingsTool(Tool):
    def __init__(self, listings: ListingsManager):
        self.listings = listings
        super().__init__(
            name="list_all_listings",
            description="List all property listings.",
            input_schema={"type": "object", "properties": {}, "required": []},
        )

    def run(self, params: dict) -> str:
        return json.dumps([asdict(listing) for listing in self.listings.list_all_listings()])
