# src/sealrepos/util/log.py: Structured JSON logger.
# This module provides a centralized logging setup that outputs structured
# JSON logs. It uses contextvars to automatically inject contextual information
# like repository name or operation ID into log records, making them easier to
# parse and analyze in a log management system.

import logging
import json
import contextvars

repo_context = contextvars.ContextVar('repo_context', default=None)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "repo": repo_context.get(),
        }
        return json.dumps(log_record)

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger
