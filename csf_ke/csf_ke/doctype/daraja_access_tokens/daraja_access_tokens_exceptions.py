"""Daraja Access Tokens exceptions"""


class InvalidTokenExpiryTime(Exception):
    """
    Raised when the access token's expiry time is earlier
    or the same as the access token's fetch time.
    It should always be 1 hour after the fetch time.
    """
