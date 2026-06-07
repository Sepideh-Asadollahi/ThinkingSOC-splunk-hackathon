"""128k context prompt budgets."""

from __future__ import annotations

from services.llm.llm_context_budget import (
    alert_context_max_chars,
    context_input_char_budget,
    schema_prompt_max_chars,
)


def test_128k_input_budget(test_settings) -> None:
    s = test_settings.model_copy(update={"tsoc_llm_context_tokens": 131072})
    budget = context_input_char_budget(s)
    assert budget > 400_000
    assert schema_prompt_max_chars(s) <= budget
    assert alert_context_max_chars(s) <= budget
