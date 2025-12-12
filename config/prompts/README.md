# Prompt Configuration

Custom prompts for the RAG agent.

## Files

| File | Purpose | Status |
|------|---------|--------|
| `system_prompt.txt` | Agent behavior & response rules | gitignored |
| `query_expansion.txt` | Query reformulation with domain terms | gitignored |
| `*.txt.example` | Generic templates | tracked |

## Setup

```bash
# Copy examples and customize for your domain
cp system_prompt.txt.example system_prompt.txt
cp query_expansion.txt.example query_expansion.txt
```

## Loading Order

1. Environment variable (`RAG_SYSTEM_PROMPT` / `QUERY_EXPANSION_PROMPT_FILE`)
2. File in this directory (`config/prompts/*.txt`)
3. Built-in fallback in code
