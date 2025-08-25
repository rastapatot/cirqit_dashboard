"""
CirQit Hackathon Dashboard Services Package
Production-ready services for scoring and event management
"""

from .scoring import ScoringService
from .event_management import EventManagementService

__all__ = ['ScoringService', 'EventManagementService']