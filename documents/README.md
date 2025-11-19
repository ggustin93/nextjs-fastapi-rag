# Documents Directory

This directory contains documents for the RAG knowledge base.

## Structure

```
documents/
├── active/           # Documents to be ingested into the knowledge base
│   └── guichet/      # Active documents (French)
└── archive/          # Reference documents (not ingested)
    ├── audio_backup/ # Audio file backups
    └── other_docs/   # Other reference materials
```

## Usage

### Active Documents
Place documents you want to ingest into `active/`. The ingestion script will process these files and add them to the vector database.

Supported formats:
- PDF (.pdf)
- Markdown (.md)
- Word documents (.docx)
- Audio files (.mp3, .wav) - transcribed with Whisper

### Archive Documents
Documents in `archive/` are kept for reference but are not ingested into the knowledge base.

## Ingestion

To ingest documents, run from the project root:

```bash
python -m packages.ingestion.ingest --input-dir documents/active
```
