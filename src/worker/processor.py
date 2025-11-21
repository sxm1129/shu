from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
from sqlalchemy import update

from src.infra.database import get_session_factory
from src.infra.s3_client import AudioStorageClient
from src.models import ChapterTask

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    tts_url: str
    tts_api_key: Optional[str]
    speaker_audio_path: str
    max_retries: int
    heartbeat_interval: int
    gpu_limit: int
    mp3_poll_attempts: int = 5
    mp3_poll_interval: int = 2

    @classmethod
    def from_env(cls) -> "ProcessorConfig":
        return cls(
            tts_url=os.environ.get("TTS_API_URL", "http://127.0.0.1:8009/api/tts/synthesize"),
            tts_api_key=os.environ.get("TTS_API_KEY"),
            speaker_audio_path=os.environ.get("SPEAKER_AUDIO_PATH", "./speaker.wav"),
            max_retries=int(os.environ.get("MAX_RETRIES", "5")),
            heartbeat_interval=int(os.environ.get("HEARTBEAT_INTERVAL", "10")),
            gpu_limit=int(os.environ.get("WORKER_GPU_LIMIT", "4")),
            mp3_poll_attempts=int(os.environ.get("MP3_POLL_ATTEMPTS", "5")),
            mp3_poll_interval=int(os.environ.get("MP3_POLL_INTERVAL", "2")),
        )


class Heartbeat:
    def __init__(self, task_id: int, worker_id: str, interval: int):
        self.task_id = task_id
        self.worker_id = worker_id
        self.interval = max(5, interval)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._session_factory = get_session_factory()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval)

    def _run(self):
        while not self._stop_event.wait(self.interval):
            with self._session_factory() as session:
                session.execute(
                    update(ChapterTask)
                    .where(ChapterTask.task_id == self.task_id, ChapterTask.locked_by == self.worker_id)
                    .values(last_heartbeat=datetime.now(timezone.utc))
                )
                session.commit()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()


class TaskProcessor:
    def __init__(self, worker_id: str, storage: Optional[AudioStorageClient] = None, config: Optional[ProcessorConfig] = None):
        self.worker_id = worker_id
        self.config = config or ProcessorConfig.from_env()
        self.storage = storage or AudioStorageClient()
        self._session_factory = get_session_factory()
        self._semaphore = threading.BoundedSemaphore(max(1, self.config.gpu_limit))

    def process_task(self, task: ChapterTask) -> None:
        logger.info("Worker %s processing task %s", self.worker_id, task.task_id)
        with self._semaphore:
            heartbeat = Heartbeat(task.task_id, self.worker_id, self.config.heartbeat_interval)
            with heartbeat:
                try:
                    audio_bytes, duration = self._synthesize(task)
                    key = self.storage.generate_audio_key(task.book_id, task.chapter_index)
                    self.storage.upload_file(audio_bytes, key)
                    audio_url = self.storage.generate_presigned_url(key)
                    self._mark_completed(task.task_id, audio_url, duration)
                    logger.info("Task %s completed", task.task_id)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.exception("Task %s failed: %s", task.task_id, exc)
                    self._handle_failure(task, exc)

    def _synthesize(self, task: ChapterTask) -> tuple[bytes, Optional[int]]:
        data = {
            "text": task.content_text,
            "emotion_control_method": 0,
            "emotion_weight": 0.65,
            "emotion_random": "false",
            "max_text_tokens_per_segment": 120,
            "interval_silence": 200,
            "do_sample": "true",
            "top_p": 0.8,
            "top_k": 30,
            "temperature": 0.8,
            "length_penalty": 0.0,
            "num_beams": 3,
            "repetition_penalty": 10.0,
            "max_mel_tokens": 1500,
        }
        headers = {}
        if self.config.tts_api_key:
            headers["Authorization"] = f"Bearer {self.config.tts_api_key}"
        with open(self.config.speaker_audio_path, "rb") as audio_file:
            files = {"speaker_audio": ("speaker.wav", audio_file, "audio/wav")}
            response = requests.post(self.config.tts_url, data=data, files=files, headers=headers, timeout=120)
        response.raise_for_status()
        payload = response.json()
        mp3_url = payload.get("mp3_url")
        if not mp3_url:
            raise RuntimeError("TTS response missing mp3_url")
        mp3_bytes = self._poll_mp3(mp3_url)
        return mp3_bytes, payload.get("duration")

    def _poll_mp3(self, mp3_url: str) -> bytes:
        full_url = urljoin(self.config.tts_url, mp3_url)
        for attempt in range(self.config.mp3_poll_attempts):
            response = requests.get(full_url, timeout=60)
            if response.status_code == 200:
                return response.content
            if response.status_code == 202:
                time.sleep(self.config.mp3_poll_interval * (attempt + 1))
                continue
            response.raise_for_status()
        raise RuntimeError("MP3 not ready after polling")

    def _mark_completed(self, task_id: int, audio_url: str, duration: Optional[int]) -> None:
        with self._session_factory() as session:
            session.execute(
                update(ChapterTask)
                .where(ChapterTask.task_id == task_id)
                .values(
                    status="COMPLETED",
                    audio_url=audio_url,
                    audio_duration=duration,
                    last_heartbeat=datetime.now(timezone.utc),
                    locked_by=None,
                    locked_at=None,
                    error_log=None,
                )
            )
            session.commit()

    def _handle_failure(self, task: ChapterTask, exc: Exception) -> None:
        retries = (task.retry_count or 0) + 1
        if retries >= self.config.max_retries:
            status = "FAILED"
            next_retry_at = datetime.now(timezone.utc)
        else:
            status = "PENDING"
            wait_minutes = min(2 ** retries, 60)
            next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=wait_minutes)
        error_message = str(exc)
        with self._session_factory() as session:
            session.execute(
                update(ChapterTask)
                .where(ChapterTask.task_id == task.task_id)
                .values(
                    status=status,
                    retry_count=retries,
                    next_retry_at=next_retry_at,
                    locked_by=None,
                    locked_at=None,
                    last_heartbeat=None,
                    audio_url=None,
                    audio_duration=None,
                    error_log=error_message[:1000],
                )
            )
            session.commit()
