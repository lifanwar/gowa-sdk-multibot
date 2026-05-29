import os
import socket
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_name: str = "automation-bot"

    # Device yang akan ditangani worker ini.
    # Worker hanya subscribe ke channel milik device ini.
    device_id: str

    redis_url: str = "redis://localhost:6379/0"

    # Pub/Sub baru. Format default channel:
    # wa:incoming:{device_id}
    pubsub_channel_name: str | None = None
    pubsub_channel_prefix: str = "wa:incoming"

    # Backward-compatible migration fields.
    # Kalau .env lama masih memakai STREAM_NAME/STREAM_PREFIX,
    # worker tetap bisa jalan, tetapi sebaiknya pindah ke PUBSUB_*.
    stream_name: str | None = None
    stream_prefix: str | None = None

    pubsub_poll_timeout_seconds: float = 1.0
    redis_reconnect_sleep_seconds: float = 2.0

    gowa_base_url: str = "http://localhost:3000"
    gowa_device_id: str | None = None

    gowa_send_message_path: str = "/send/message"
    gowa_basic_auth_username: str | None = None
    gowa_basic_auth_password: str | None = None

    @property
    def resolved_pubsub_channel(self) -> str:
        if self.pubsub_channel_name:
            return self.pubsub_channel_name

        if self.stream_name:
            return self.stream_name

        prefix = self.pubsub_channel_prefix

        if self.stream_prefix:
            prefix = self.stream_prefix

        return f"{prefix}:{self.device_id}"

    @property
    def resolved_consumer_name(self) -> str:
        hostname = socket.gethostname()
        pid = os.getpid()
        return f"{self.bot_name}-{hostname}-{pid}"

    @property
    def resolved_gowa_device_id(self) -> str:
        return self.gowa_device_id


@lru_cache
def get_settings() -> Settings:
    return Settings()
