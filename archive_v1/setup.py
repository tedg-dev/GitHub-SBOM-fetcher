from setuptools import setup, find_packages

setup(
    name="github_sbom_fetcher",
    version="0.1.0",
    packages=find_packages(include=['github_sbom_fetcher*']),
    install_requires=[
        "requests>=2.25.1",
    ],
    python_requires=">=3.7",
    extras_require={
        'test': [
            'pytest>=6.2.5',
            'pytest-cov>=3.0.0',
        ],
    },
)
