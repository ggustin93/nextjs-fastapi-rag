# Query Expansion Prompts

This directory contains customizable prompts for the Query Expansion feature.

## Purpose

Query expansion improves RAG retrieval by adding domain-specific synonyms and technical terms to user queries before searching. This helps with "vocabulary mismatch" - when users use different words than what's in the documents.

**Example:**

- User asks: "c'est quoi un chantier de type A?"
- Expanded: "c'est quoi un chantier de type A, définition A - Autorisation procédure complexe D - Dispense E - Exécution types de demandes délai 60 jours"

## Files

- `query_expansion.txt` - Main prompt template for query expansion

## Customizing for Your Organization

1. **Edit `query_expansion.txt`** with your domain terminology
2. **Keep the `{query}` placeholder** - it will be replaced with the user's question
3. **Structure your prompt** with:
   - Context about your knowledge base
   - Exact terminology from your documents
   - Instructions for the LLM

## Example: Customizing for a Different Domain

### Before (Osiris - Brussels Roadworks)

```text
TERMINOLOGIE DU DOMAINE:
- "D - Dispense" = occupation < 24h, gratuite
- "E - Exécution" = chantier < 60 jours
- "A - Autorisation" = chantiers complexes
```

### After (HR System Example)

```text
TERMINOLOGIE DU DOMAINE:
- "CDI" = Contrat à Durée Indéterminée
- "CDD" = Contrat à Durée Déterminée
- "RTT" = Réduction du Temps de Travail
- "CP" = Congés Payés
- "SIRH" = Système d'Information RH
```

## Configuration

Environment variables:

- `QUERY_EXPANSION_ENABLED` - Enable/disable feature (default: `true`)
- `QUERY_EXPANSION_MODEL` - LLM model to use (default: `gpt-4o-mini`)
- `QUERY_EXPANSION_PROMPT_FILE` - Custom path to prompt file

## Testing

```bash
# Test query expansion in isolation
python -c "
import asyncio
from packages.core.query_expansion import expand_query

async def test():
    result = await expand_query('votre question test')
    print(result)

asyncio.run(test())
"
```

## Cost

Query expansion uses `gpt-4o-mini` by default (~$0.00015 per query expansion).
For high-volume applications, consider:

- Caching common query expansions
- Using a smaller/local model
- Disabling via `QUERY_EXPANSION_ENABLED=false`
