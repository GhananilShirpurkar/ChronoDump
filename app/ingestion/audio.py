"""Audio ingestion and normalization handler."""

import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from aiogram import Bot
from app.config import settings

logger = logging.getLogger(__name__)


class AudioIngestion:
    """Manages downloading and normalizing incoming Telegram audio/voice messages."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.audio_dir = (data_dir or settings.DATA_DIR) / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def download_telegram_voice(self, bot: Bot, file_id: str) -> Path:
        """Download voice message from Telegram servers to local audio dir."""
        tg_file = await bot.get_file(file_id)
        if not tg_file.file_path:
            raise ValueError(f"Could not retrieve file path for Telegram file_id: {file_id}")

        extension = Path(tg_file.file_path).suffix or ".ogg"
        local_filename = f"{uuid.uuid4()}{extension}"
        local_path = self.audio_dir / local_filename

        await bot.download_file(tg_file.file_path, destination=local_path)
        logger.info(f"Downloaded Telegram voice file to {local_path}")
        return local_path

    def normalize_audio(self, input_path: Path) -> Path:
        """
        Normalize audio file to 16kHz mono WAV for optimal Whisper transcription.
        If ffmpeg is not available, returns the original path.
        """
        output_path = input_path.with_suffix(".wav")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            logger.info(f"Normalized audio to {output_path}")
            # Remove original input file to save disk space
            if input_path.exists() and input_path != output_path:
                input_path.unlink()
            return output_path
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"ffmpeg normalization skipped or failed: {e}. Using original audio file.")
            return input_path

    def cleanup_file(self, file_path: Path) -> None:
        """Securely remove audio file after processing to maintain user privacy."""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up temporary audio file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to remove audio file {file_path}: {e}")
