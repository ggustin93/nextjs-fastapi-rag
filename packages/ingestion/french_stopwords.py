"""
French linguistic rules for query reformulation.
Preserves semantic intent while removing query artifacts.
"""

# French stopwords to remove (generic filler words only)
# Keep prepositions like "de", "du", "des" as they carry meaning
FRENCH_STOPWORDS = frozenset(
    [
        # Articles that can be safely removed
        "le",
        "la",
        "les",
        "un",
        "une",
        # Common pronouns that don't add search value
        "je",
        "tu",
        "il",
        "elle",
        "nous",
        "vous",
        "ils",
        "elles",
        # Generic verbs that are question artifacts
        "est",
        "sont",
        "peut",
        "faut",
    ]
)

# Intent-preserving prepositions and markers (DO NOT REMOVE)
# These words carry semantic meaning and help with phrase matching
SEMANTIC_MARKERS = frozenset(
    [
        # Prepositions indicating relationships
        "de",
        "du",
        "des",
        "d",
        # Quantifiers and scope markers
        "tous",
        "toutes",
        "tout",
        "toute",
        # Comparatives
        "plus",
        "moins",
        "maximum",
        "minimum",
        # Negation
        "ne",
        "pas",
        "sans",
    ]
)

# Question patterns to remove (order matters - longest first)
QUESTION_PATTERNS = [
    # Full interrogative phrases
    "c'est quoi",
    "c est quoi",
    "qu'est-ce que c'est",
    "qu est ce que c est",
    "quelle est",
    "quel est",
    "quelles sont",
    "quels sont",
    "quelles",
    "quels",
    # Question words
    "comment est-ce que",
    "comment est ce que",
    "comment",
    "quand est-ce que",
    "quand est ce que",
    "quand",
    "où est-ce que",
    "où est ce que",
    "où",
    "combien de",
    "combien d",
    "combien",
    "pourquoi est-ce que",
    "pourquoi est ce que",
    "pourquoi",
    "est-ce que",
    "est ce que",
]
