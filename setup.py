from setuptools import setup

setup(
    name="flights-api",
    version="0.1.0",
    package_dir={"": "src"},
    packages=["api"],
    python_requires=">=3.12",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "pydantic>=2.5.2",
        "python-multipart>=0.0.6",
        "aiohttp>=3.9.1",
        "brotli>=1.1.0",
        "selectolax>=0.3.17",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "httpx>=0.25.2",
        ],
    },
)

# testing
