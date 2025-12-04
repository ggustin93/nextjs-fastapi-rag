# Example Prompts

This directory contains **example templates** for RAG system prompts.

## Quick Start

1. **Copy** the example files to `data/prompts/` (gitignored):
   ```bash
   cp data/examples/prompts/example_query_expansion.txt data/prompts/query_expansion.txt
   cp data/examples/prompts/example_system_prompt.txt data/prompts/system_prompt.txt
   ```

2. **Customize** with your domain-specific terminology

3. **Test** your configuration

## Files

| Example File | Purpose | Copy To |
|-------------|---------|---------|
| `example_query_expansion.txt` | Query enrichment with domain terms | `data/prompts/query_expansion.txt` |
| `example_system_prompt.txt` | RAG assistant behavior rules | `data/prompts/system_prompt.txt` |

## Query Expansion

Query expansion improves retrieval by adding domain-specific synonyms and technical terms before searching.

**Example transformation:**
- User asks: "How do I authenticate?"
- Expanded: "How do I authenticate, authentication OAuth JWT tokens API keys authorization login credentials"

### Customizing Query Expansion

1. Update the **CONTEXT** section with your knowledge base description
2. Replace **DOMAIN TERMINOLOGY** with your organization's specific terms
3. Adjust **INSTRUCTIONS** for your language and formatting preferences

### Domain Examples

**Technical Documentation:**
```text
DOMAIN TERMINOLOGY:
- "API" = Application Programming Interface, endpoints, REST
- "SDK" = Software Development Kit, client libraries
- "Authentication" = OAuth, JWT tokens, API keys
```

**HR System:**
```text
DOMAIN TERMINOLOGY:
- "PTO" = Paid Time Off, vacation, leave
- "HRIS" = Human Resources Information System
- "Onboarding" = new hire process, orientation
```

**Legal Documents:**
```text
DOMAIN TERMINOLOGY:
- "NDA" = Non-Disclosure Agreement, confidentiality
- "SLA" = Service Level Agreement, uptime guarantees
- "ToS" = Terms of Service, user agreement
```

## System Prompt

The system prompt defines how the RAG assistant behaves, including:
- Scope boundaries (what questions to answer)
- Tool usage rules
- Response formatting
- Source citation requirements

### Key Sections to Customize

1. **SCOPE RULES**: Define what topics your knowledge base covers
2. **OUT-OF-SCOPE RESPONSE**: How to handle irrelevant questions
3. **RELEVANCE THRESHOLDS**: Adjust based on your retrieval quality
4. **RESPONSE STYLE**: Language, formatting, citation format

## Configuration

Environment variables (optional):
- `QUERY_EXPANSION_ENABLED` - Enable/disable (default: `true`)
- `QUERY_EXPANSION_MODEL` - LLM model (default: `gpt-4o-mini`)
- `SYSTEM_PROMPT_FILE` - Custom path to system prompt

## Directory Structure

```
data/
├── prompts/                  # Your actual prompts (gitignored)
│   ├── query_expansion.txt
│   └── system_prompt.txt
└── examples/
    └── prompts/              # Example templates (tracked in git)
        ├── README.md
        ├── example_query_expansion.txt
        └── example_system_prompt.txt
```

## Tips

- **Start simple**: Begin with the example and iterate based on retrieval quality
- **Test expansions**: Verify expanded queries improve retrieval
- **Monitor costs**: Query expansion adds ~$0.00015/query with gpt-4o-mini
- **Use exact terms**: Copy terminology exactly as it appears in your documents
