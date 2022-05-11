from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in csf_ke/__init__.py
from csf_ke import __version__ as version

setup(
	name="csf_ke",
	version=version,
	description="Country Specific Functionality for Kenya",
	author="Navari Limited",
	author_email="info@navari.co.ke",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
