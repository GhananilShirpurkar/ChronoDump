"""Local speech-to-text transcription powered by faster-whisper with Silero VAD."""

import logging
from pathlib import Path
from typing import Optional, Tuple
from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Manages local Whisper model for CPU-optimized speech-to-text."""

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ) -> None:
        self.model_size = model_size or settings.WHISPER_MODEL
        self.device = device or settings.WHISPER_DEVICE
        self.compute_type = compute_type or settings.WHISPER_COMPUTE_TYPE
        self._model: Optional[WhisperModel] = None

    @property
    def model(self) -> WhisperModel:
        """Lazy loader for Whisper model to conserve startup memory."""
        if self._model is None:
            logger.info(
                f"Loading faster-whisper model '{self.model_size}' on {self.device} with {self.compute_type}..."
            )
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load whisper model '{self.model_size}': {e}. Falling back to 'tiny.en'..."
                )
                self.model_size = "tiny.en"
                self._model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully.")
        return self._model

    def transcribe(self, audio_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        Transcribe audio file using faster-whisper and Silero VAD.
        Returns (transcript_text, error_message).
        If transcription is successful, error_message is None.
        If transcription fails or quality is unacceptable, returns (None, user_error_message).
        """
        if not audio_path.exists():
            return None, "Audio file not found."

        try:
            segments, info = self.model.transcribe(
                str(audio_path),
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            # Language check (PRD Section 10.5: English only)
            if info.language and info.language != "en" and info.language_probability > 0.8:
                logger.info(f"Non-English audio detected ({info.language} with prob {info.language_probability})")
                return None, "I only speak English for now 🤙 — send me an English note."

            transcript_parts = []
            avg_logprob_sum = 0.0
            count = 0

            for segment in segments:
                text = segment.text.strip()
                if text:
                    transcript_parts.append(text)
                    avg_logprob_sum += segment.avg_logprob
                    count += 1

            full_transcript = " ".join(transcript_parts).strip()

            # Poor audio / empty transcript check (PRD Section 20 Failure 3)
            if not full_transcript or len(full_transcript) < 3:
                logger.info("Empty or near-empty transcription.")
                return None, "I couldn't make that out — mind re-recording? 🎙️"

            # Check average logprob for catastrophic garble
            if count > 0 and (avg_logprob_sum / count) < -2.5:
                logger.warning("Very low transcription confidence detected.")
                return None, "I couldn't make that out — mind re-recording? 🎙️"

            logger.info(f"Transcription successful ({count} segments): {full_transcript[:60]}...")
            return full_transcript, None

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}", exc_info=True)
            return None, "I couldn't make that out — mind re-recording? 🎙️"
