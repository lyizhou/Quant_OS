"""Rate Limiting Middleware - Prevent API abuse."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
# Note: config_filename=None prevents slowapi from reading .env file
# which can cause encoding issues on Windows with Chinese characters
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    config_filename=None,  # Disable .env file reading to avoid encoding issues
)
