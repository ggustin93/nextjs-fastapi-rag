"""Domain-specific configuration module.

This package contains OPTIONAL configuration classes for domain-specific
RAG customization. The core RAG system works without any configuration.
"""
from .domain_config import DomainConfig, QueryExpansionConfig

__all__ = ["DomainConfig", "QueryExpansionConfig"]
