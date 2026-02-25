"""
Setup script for DB Clone Tool
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="db-clone-tool",
    version="0.2.0",
    description="All-in-one MySQL schema cloning tool with a built-in web UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Melih Çelenk",
    author_email="info@melihcelenk.com",
    url="https://github.com/melihcelenk/db-clone-tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "db_clone_tool": [
            "templates/**/*",
            "static/**/*",
        ],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "Flask==3.0.0",
        "pymysql==1.1.1",
        "cryptography>=41.0.0",
        "python-dotenv==1.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.12.0",
            "flake8>=7.0.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "db-clone-tool=src.db_clone_tool.main:run_app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="mysql database schema clone backup mysqldump",
)
