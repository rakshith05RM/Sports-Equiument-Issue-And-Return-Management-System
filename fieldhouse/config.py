"""
Application configuration.
Reads settings from environment variables (see .env.example).
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file into the environment
load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")

    # MySQL database
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "rakshith")
    DB_NAME = os.environ.get("DB_NAME", "fieldhouse")

    # Pagination
    ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", 10))
