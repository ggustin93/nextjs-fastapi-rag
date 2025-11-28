"""Domain-specific configuration for query expansion.

This module provides OPTIONAL domain-specific configuration for the RAG agent.
The RAG system works perfectly without any domain configuration - these are
purely optional enhancements for specific use cases.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryExpansionConfig:
    """Configuration for domain-specific query expansion.

    This is OPTIONAL - can be None to disable query expansion entirely.
    When enabled, provides domain-specific synonyms, criteria, and context
    for query enhancement.

    Example shows occupation type expansion (can be customized for any domain).
    To disable query expansion, simply pass None or omit this config.
    """

    type_d: dict = field(
        default_factory=lambda: {
            "synonyms": ["dispense", "D - Dispense"],
            "criteria": ["50 m²", "24 heures"],
            "context": ["déclaration", "occupation voie publique"],
        }
    )
    type_e: dict = field(
        default_factory=lambda: {
            "synonyms": ["exécution", "E - Exécution"],
            "criteria": ["300 m²", "60 jours"],
            "context": ["frais administratifs"],
        }
    )
    type_a: dict = field(
        default_factory=lambda: {
            "synonyms": ["autorisation", "A - Autorisation"],
            "criteria": ["longue durée"],
            "context": ["permis", "déviation"],
        }
    )


@dataclass
class DomainConfig:
    """Complete domain configuration.

    All fields are optional - the RAG system works without domain-specific
    customization. This class allows users to optionally add domain-specific
    behavior without modifying the core agent code.

    Example usage:
        # Generic RAG (no domain-specific features)
        config = DomainConfig()

        # With query expansion enabled
        config = DomainConfig(query_expansion=QueryExpansionConfig())

        # Disable query expansion explicitly
        config = DomainConfig(query_expansion=None)
    """

    query_expansion: Optional[QueryExpansionConfig] = None
