"""Utility functions"""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def clean_url_params(url: str) -> str:
	"""
	Removes duplicated query parameters from a URL.

	Keeps only the first occurrence of each parameter
	while preserving the original URL structure.

	Example:
	    Input:
	        http://example.com?page=5&page_size=100&page_size=100

	    Output:
	        http://example.com?page=5&page_size=100

	Args:
	    url (str):
	        URL to normalize.

	Returns:
	    str:
	        URL with cleaned query parameters.
	"""

	if not url:
		return url

	parsed = urlparse(url)

	query_dict = parse_qs(
		parsed.query,
		keep_blank_values=True,
	)

	cleaned_query = {key: values[0] for key, values in query_dict.items() if values}

	normalized_query = urlencode(cleaned_query)

	return urlunparse(
		(
			parsed.scheme,
			parsed.netloc,
			parsed.path,
			parsed.params,
			normalized_query,
			parsed.fragment,
		)
	)
