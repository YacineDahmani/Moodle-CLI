"""Moodle CLI package."""
import warnings

# Suppress harmless requests dependency version warning on newer Python environments
warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")

__version__ = "1.0.0"
