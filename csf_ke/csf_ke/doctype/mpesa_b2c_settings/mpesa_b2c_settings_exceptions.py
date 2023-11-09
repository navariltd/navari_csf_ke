"""Exceptions"""


class InvalidURLException(Exception):
    """Exception to raise when URLs fail validation"""


class IncompleteDataException(Exception):
    """Exception to raise when saving form with incomplete data"""
