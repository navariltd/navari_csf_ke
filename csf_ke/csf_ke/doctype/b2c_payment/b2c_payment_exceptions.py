"""B2C Payment Exceptions"""


class InvalidReceiverMobileNumberError(Exception):
    """Raised when receiver's mobile number fails validation"""


class InsufficientPaymentAmountError(Exception):
    """Raised when the payment amount is less than the required KShs. 10"""


class IncorrectStatusError(Exception):
    """Raised when status is Errored but no errod description or error code has been supplied"""
