
from setuptools import setup

requirements = [line.strip() for line in open("requirements.txt")]

setup(
    name="liveweb",
    version="2.0.dev",
    description="Liveweb proxy",
    license='GPL v2',
    author="Internet Archive",
    author_email="info@archive.org",
    url="http://github.com/internetarchive/liveweb",
    packages=["liveweb", "liveweb.tools"],
    platforms=["any"],
    entry_points={
        "console_scripts": [
            "liveweb-proxy=liveweb.cli:main"
        ]
    },
    install_requires=requirements
)

