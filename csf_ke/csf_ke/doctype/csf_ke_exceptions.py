"""Custom Exceptions and Errors raised by modules in the CSF_KE application"""


class InvalidReceiverMobileNumberError(Exception):
    """Raised when receiver's mobile number fails validation"""


class InsufficientPaymentAmountError(Exception):
    """Raised when the payment amount is less than the required KShs. 10"""


class IncorrectStatusError(Exception):
    """Raised when status is Errored but no errod description or error code has been supplied"""


class InvalidTokenExpiryTime(Exception):
    """
    Raised when the access token's expiry time is earlier
    or the same as the access token's fetch time.
    It should always be 1 hour after the fetch time.
    """


class InvalidURLError(Exception):
    """Raise when URLs fail validation"""


class InvalidAuthenticationCertificateFileError(Exception):
    """Raised when an invalid - i.e. not a .cer - certificate file is uploaded"""
