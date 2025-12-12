# Data Directory

This directory contains all data for the RAG knowledge base.

## Structure

```
data/
├── raw/                      # Unprocessed input files
│   ├── documents/            # Source documents (PDF, DOCX, etc.)
│   │   ├── BusinessAnalysis/ # Business & functional analysis
│   │   ├── Slides/           # Training presentations
│   │   └── UserGuides/       # User documentation
│   ├── notes/                # Custom markdown notes
│   └── web/                  # Web scraper configuration
│       └── sources.yaml      # Scraper sources config
├── processed/                # Generated/processed content
│   └── scraped/              # Web scraper output
└── examples/                 # Tutorial examples (tracked in git)

Note: Prompts and NLP config are in /config/ at project root.
```

## Data Flow

```
                    ┌─────────────────┐
                    │   Raw Input     │
                    │  (data/raw/)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │Documents │       │  Scraper │       │  Notes   │
   │(PDF,DOCX)│       │  (auto)  │       │   (md)   │
   └────┬─────┘       └────┬─────┘       └────┬─────┘
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────────────────────────────────────────┐
   │            Ingestion Pipeline               │
   │  (chunking → embedding → vector storage)    │
   └─────────────────────────────────────────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │   Supabase   │
                 │   pgvector   │
                 └──────────────┘
```

## Usage

### Adding Documents

Place documents in `data/raw/documents/` (organized by category):

```bash
cp my-document.pdf data/raw/documents/UserGuides/
cp analysis.docx data/raw/documents/BusinessAnalysis/
```

### Adding Notes

Place markdown notes in `data/raw/notes/`:

```bash
cp my-notes.md data/raw/notes/
```

### Running the Scraper

Web scraper outputs to `data/processed/scraped/`:

```bash
make scrape  # Uses config from data/raw/web/sources.yaml
```

### Ingestion

Ingest all data into the vector database:

```bash
make ingest  # Runs 3-step pipeline: documents → notes → scraped
```

## Supported Formats

**Documents:**
- PDF (.pdf)
- Word (.docx, .doc)
- PowerPoint (.pptx, .ppt)
- Excel (.xlsx, .xls)
- HTML (.html, .htm)
- Markdown (.md)
- Text (.txt)
- Audio (.mp3, .wav, .m4a) - transcribed with Whisper

**Scraped Output:**
- Markdown with YAML frontmatter

## Git Status

| Directory | Status | Notes |
|-----------|--------|-------|
| `data/raw/documents/` | gitignored | Local docs, README tracked |
| `data/raw/notes/` | gitignored | Local notes, README tracked |
| `data/raw/web/sources.yaml` | gitignored | Domain-specific scraper config |
| `data/processed/` | gitignored | Generated output |
| `data/examples/` | **tracked** | Tutorials |
| `config/prompts/` | gitignored | Prompts (examples tracked) |
| `config/stopwords.json` | gitignored | NLP config |
