"""Exceptions"""


class InvalidURLError(Exception):
    """Exception to raise when URLs fail validation"""


class IncompleteDataError(Exception):
    """Exception to raise when saving form with incomplete data"""
