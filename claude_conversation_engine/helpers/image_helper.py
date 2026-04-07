import base64
import mimetypes
import os
import urllib.request

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


class ImageHelper:
    """Handles image validation and conversion to base64 content blocks."""

    @staticmethod
    def load_from_file(path):
        """Read a local image file and return (base64_data, media_type)."""
        with open(path, "rb") as f:
            image_bytes = f.read()
        media_type = mimetypes.guess_type(path)[0] or "image/png"
        return base64.standard_b64encode(image_bytes).decode("utf-8"), media_type

    @staticmethod
    def fetch_from_url(url):
        """Download an image URL and return (base64_data, media_type)."""
        with urllib.request.urlopen(url) as response:
            image_bytes = response.read()
            content_type = response.headers.get("Content-Type")
        if not content_type:
            content_type = mimetypes.guess_type(url)[0] or "image/png"
        return base64.standard_b64encode(image_bytes).decode("utf-8"), content_type

    @staticmethod
    def build_content_block(image):
        """Build a base64 image content block from a file path, URL, or raw data dict."""
        if isinstance(image, str):
            if os.path.isfile(image):
                data, media_type = ImageHelper.load_from_file(image)
            else:
                data, media_type = ImageHelper.fetch_from_url(image)
        else:
            data, media_type = image["data"], image["media_type"]

        decoded_size = len(data) * 3 // 4
        if decoded_size > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"Image exceeds maximum size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB"
            )
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }
