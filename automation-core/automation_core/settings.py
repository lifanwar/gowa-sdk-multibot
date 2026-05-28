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

    device_id: str
    stream_name: str | None = None
    stream_prefix: str = "wa:incoming"

    consumer_group: str | None = None
    consumer_name: str | None = None

    redis_url: str = "redis://localhost:6379/0"

    stream_block_ms: int = 5000
    stream_count: int = 10

    gowa_base_url: str = "http://localhost:3000"
    gowa_device_id: str | None = None

    gowa_send_message_path: str = "/send/message"
    gowa_basic_auth_username: str | None = None
    gowa_basic_auth_password: str | None = None

    ack_on_handler_success: bool = True

    @property
    def resolved_stream_name(self) -> str:
        if self.stream_name:
            return self.stream_name

        return f"{self.stream_prefix}:{self.device_id}"

    @property
    def resolved_consumer_group(self) -> str:
        if self.consumer_group:
            return self.consumer_group

        return f"{self.bot_name}-group"

    @property
    def resolved_consumer_name(self) -> str:
        if self.consumer_name:
            return self.consumer_name

        hostname = socket.gethostname()
        pid = os.getpid()

        return f"{self.bot_name}-{hostname}-{pid}"

    @property
    def resolved_gowa_device_id(self) -> str:
        return self.gowa_device_id or self.device_id


@lru_cache
def get_settings() -> Settings:
    return Settings()