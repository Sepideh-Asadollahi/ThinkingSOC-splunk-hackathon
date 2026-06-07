"""Optional newline-delimited JSON log of analysis results (local file)."""

from __future__ import annotations

import logging

from config import Settings
from models.analysis import SocAnalysisResult

logger = logging.getLogger(__name__)


def append_analysis_log(settings: Settings, result: SocAnalysisResult) -> None:
    path = settings.tsoc_analysis_log_path
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")
    except OSError as e:
        logger.warning("Could not append to tsoc_analysis_log_path: %s", e)
