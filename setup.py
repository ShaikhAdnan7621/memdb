"""
Setup configuration for MemDB - Hybrid In-Memory + PostgreSQL Database

This package provides a high-performance database solution combining the speed
of in-memory operations with the durability of PostgreSQL persistence.

Installation:
    pip install python-memdb

Quick Start:
    from dyn_memdb import MemDB

    db = MemDB("postgresql://user:pass@localhost:5432/dbname")
    await db.start()
    await db.insert("table", "key", {"data": "value"})
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(
    os.path.join(this_directory, "dyn_memdb", "README.md"), encoding="utf-8"
) as f:
    long_description = f.read()

setup(
    name="python-memdb",
    version="1.0.0",
    author="Shaikh Adnan",
    author_email="shaikh.adnan.dev@gmail.com",
    description="High-performance hybrid in-memory + PostgreSQL database for real-time applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shaikhadnan7621/memdb",
    project_urls={
        "Bug Tracker": "https://github.com/shaikhadnan7621/memdb/issues",
        "Documentation": "https://github.com/shaikhadnan7621/memdb#readme",
        "Source Code": "https://github.com/shaikhadnan7621/memdb",
    },
    packages=find_packages(exclude=["tests", "examples", "docs", "benchmarks"]),
    python_requires=">=3.8",
    install_requires=[
        "asyncpg>=0.28.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Databases",
        "Framework :: AsyncIO",
        "Natural Language :: English",
    ],
    keywords=[
        "database",
        "cache",
        "caching",
        "postgresql",
        "postgres",
        "sql",
        "async",
        "asyncio",
        "real-time",
        "in-memory",
        "memory-cache",
        "high-performance",
        "fast-database",
        "telephony",
        "voip",
        "session",
        "session-management",
        "iot",
        "streaming",
        "hybrid-database",
        "python3",
        "microservices",
        "rest-api",
        "web-development",
    ],
    zip_safe=False,
)
