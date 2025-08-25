"""
CirQit Hackathon Dashboard Database Package
Production-ready database system for accurate scoring and event management
"""

from .schema import DatabaseManager
from .migration import DataMigration

__all__ = ['DatabaseManager', 'DataMigration']