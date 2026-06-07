"""Operational response planner for observability pipeline."""

from __future__ import annotations

from models.observability import DiagnoserSection, ImpactContext, ResponderSection


def build_responder(impact: ImpactContext, diagnoser: DiagnoserSection) -> ResponderSection:
    actions = [
        "Validate the metric trend for the same alert time window.",
        "Correlate service logs with metric spikes before applying remediation.",
        "Check recent deployments or configuration changes for affected service.",
    ]
    if impact.impact_level in ("high", "critical"):
        actions.append("Prepare escalation to service owner while validating root cause evidence.")
        actions.append("Apply remediation (scale/restart/rollback) only after confirmation.")
    else:
        actions.append("Continue monitoring and collect additional evidence before disruptive action.")

    safety_notes = [
        "Do not perform disruptive actions before validating impact on critical transactions.",
        "Prefer reversible actions first and document each step with timestamp.",
    ]
    if not diagnoser.root_cause_hypotheses:
        safety_notes.append("Root cause is uncertain; gather more evidence before remediation.")

    return ResponderSection(recommended_actions=actions, safety_notes=safety_notes)
