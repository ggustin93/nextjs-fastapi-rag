"""
Multi-format document reader module.

Supports PDF, DOCX, audio files via Docling and Whisper ASR.
Extracts content and converts to markdown format for consistent processing.
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DocumentReader:
    """
    Multi-format document reader with Docling and Whisper ASR support.

    Handles:
    - Office formats (PDF, DOCX, PPTX, XLSX) via Docling
    - Audio formats (MP3, WAV, M4A, FLAC) via Whisper ASR transcription
    - Text formats (TXT, MD, HTML) via direct reading
    """

    def read(self, file_path: str) -> tuple[str, Optional[Any]]:
        """
        Read document content from file - supports multiple formats via Docling.

        Args:
            file_path: Path to the document file

        Returns:
            Tuple of (markdown_content, docling_document)
            docling_document is None for text files and audio files

        Raises:
            RuntimeError: If file cannot be read or processed
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        # Audio formats - transcribe with Whisper ASR
        audio_formats = [".mp3", ".wav", ".m4a", ".flac"]
        if file_ext in audio_formats:
            content = self._transcribe_audio(file_path)
            return (content, None)  # No DoclingDocument for audio

        # Docling-supported formats (convert to markdown)
        docling_formats = [
            ".pdf",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".xlsx",
            ".xls",
            ".html",
            ".htm",
        ]

        if file_ext in docling_formats:
            try:
                from docling.document_converter import DocumentConverter

                logger.info(
                    f"Converting {file_ext} file using Docling: {os.path.basename(file_path)}"
                )

                converter = DocumentConverter()
                result = converter.convert(file_path)

                # Export to markdown for consistent processing
                markdown_content = result.document.export_to_markdown()
                logger.info(f"Successfully converted {os.path.basename(file_path)} to markdown")

                # Return both markdown and DoclingDocument for HybridChunker
                return (markdown_content, result.document)

            except Exception as e:
                logger.error(f"Failed to convert {file_path} with Docling: {e}")
                # Fall back to raw text if Docling fails
                logger.warning(f"Falling back to raw text extraction for {file_path}")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return (f.read(), None)
                except (IOError, OSError, UnicodeDecodeError) as e:
                    logger.error(f"Failed to read file {file_path}: {e}")
                    raise RuntimeError(f"Could not read file {os.path.basename(file_path)}: {e}")

        # Text-based formats (read directly)
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return (f.read(), None)
            except UnicodeDecodeError:
                # Try with different encoding
                with open(file_path, "r", encoding="latin-1") as f:
                    return (f.read(), None)

    def _transcribe_audio(self, file_path: str) -> str:
        """
        Transcribe audio file using Whisper ASR via Docling.

        Args:
            file_path: Path to the audio file

        Returns:
            Transcribed text in markdown format with timestamps

        Note:
            Returns error message string if transcription fails
        """
        try:
            from pathlib import Path

            from docling.datamodel import asr_model_specs
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import AsrPipelineOptions
            from docling.document_converter import AudioFormatOption, DocumentConverter
            from docling.pipeline.asr_pipeline import AsrPipeline

            # Use Path object - Docling expects this
            audio_path = Path(file_path).resolve()
            logger.info(f"Transcribing audio file using Whisper Turbo: {audio_path.name}")
            logger.info(f"Audio file absolute path: {audio_path}")

            # Verify file exists
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Configure ASR pipeline with Whisper Turbo model
            pipeline_options = AsrPipelineOptions()
            pipeline_options.asr_options = asr_model_specs.WHISPER_TURBO

            converter = DocumentConverter(
                format_options={
                    InputFormat.AUDIO: AudioFormatOption(
                        pipeline_cls=AsrPipeline,
                        pipeline_options=pipeline_options,
                    )
                }
            )

            # Transcribe the audio file - pass Path object
            result = converter.convert(audio_path)

            # Export to markdown with timestamps
            markdown_content = result.document.export_to_markdown()
            logger.info(f"Successfully transcribed {os.path.basename(file_path)}")
            return markdown_content

        except Exception as e:
            logger.error(f"Failed to transcribe {file_path} with Whisper ASR: {e}")
            return f"[Error: Could not transcribe audio file {os.path.basename(file_path)}]"
