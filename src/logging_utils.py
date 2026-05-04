import io
import logging
import sys
from pathlib import Path


class TeeStream(io.TextIOBase):
    """터미널 출력과 로그 파일 기록을 동시에 처리하는 간단한 스트림입니다."""

    def __init__(self, logger: logging.Logger, level: int, original_stream) -> None:
        self.logger = logger
        self.level = level
        self.original_stream = original_stream
        self._buffer = ""

    def write(self, text: str) -> int:
        self.original_stream.write(text)
        self._buffer += text

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                self.logger.log(self.level, line)
        return len(text)

    def flush(self) -> None:
        self.original_stream.flush()
        if self._buffer.strip():
            self.logger.log(self.level, self._buffer.strip())
        self._buffer = ""


def setup_file_logging(log_path: Path) -> logging.Logger:
    """logs/app.log 파일에 기록하는 logger를 준비합니다."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("inu_assignment_sync")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def attach_stdout_stderr_to_logger(logger: logging.Logger) -> None:
    """print 출력도 로그 파일에 함께 남도록 stdout/stderr를 감쌉니다."""
    sys.stdout = TeeStream(logger, logging.INFO, sys.__stdout__)
    sys.stderr = TeeStream(logger, logging.ERROR, sys.__stderr__)
