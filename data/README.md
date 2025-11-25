# Data Directory

This directory contains all data for the RAG knowledge base.

## Structure

```
data/
├── raw/                   # Unprocessed input files
│   └── pdfs/              # Manual PDF documents
│       └── guichet/       # OSIRIS user guides (French)
├── processed/             # Generated/processed content
│   └── scraped/           # Web scraper output
│       ├── myosiris/      # From my.osiris.brussels
│       ├── belgian_legal/ # From eJustice portal
│       └── osiris/        # Additional OSIRIS content
└── examples/              # Tutorial examples (tracked in git)
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
   │   PDFs   │       │  Scraper │       │  Audio   │
   │ (manual) │       │  (auto)  │       │(whisper) │
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

### Adding PDFs

Place PDF documents in `data/raw/pdfs/`:

```bash
cp my-document.pdf data/raw/pdfs/
```

### Running the Scraper

Web scraper outputs to `data/processed/scraped/`:

```bash
uv run python scripts/scrape.py --source myosiris
```

### Ingestion

Ingest all data (raw + processed) into the vector database:

```bash
# Ingest PDFs
uv run python -m packages.ingestion.ingest --documents data/raw/pdfs

# Ingest scraped content
uv run python -m packages.ingestion.ingest --documents data/processed/scraped
```

## Supported Formats

**Raw Input:**
- PDF (.pdf)
- Word (.docx)
- Markdown (.md)
- Audio (.mp3, .wav) - transcribed with Whisper

**Processed Output:**
- Markdown with YAML frontmatter (from scraper)

## Git Status

- `data/raw/` - **gitignored** (local data)
- `data/processed/` - **gitignored** (generated output)
- `data/examples/` - **tracked** (tutorials)
