
from setuptools import setup

setup(
    name="liveweb",
    version="2.0-dev",
    description="Liveweb proxy",
    license='GPL v2',
    author="Internet Archive",
    author_email="info@archive.org",
    url="http://github.com/internetarchive/liveweb",
    packages=["liveweb"],
    platforms=["any"],
    entry_points={
        "console_scripts": [
            "liveweb-proxy=liveweb.cli:main"
        ]
    }
)

