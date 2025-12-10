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
│   └── notes/                # Custom markdown notes
├── processed/                # Generated/processed content
│   └── scraped/              # Web scraper output
├── config/                   # Configuration files
│   └── sources.yaml          # Scraper sources config
└── examples/                 # Tutorial examples (tracked in git)
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
make scrape  # Uses config from data/config/sources.yaml
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
| `data/processed/` | gitignored | Generated output |
| `data/config/sources.yaml` | gitignored | Domain-specific config |
| `data/examples/` | **tracked** | Tutorials |
