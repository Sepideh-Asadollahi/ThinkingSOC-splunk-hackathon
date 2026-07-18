# ThinkingSOC Lite — Polished Tutorial Voiceover Without Timestamps

Hello, and welcome to ThinkingSOC Lite. It uses AI Agents to help security teams investigate threats faster and reuse what they learn. In this walkthrough, I will show how a completed Splunk investigation becomes a checked and analyst-approved Runbook for the next matching alert.

First, what is a SOC? A Security Operations Center watches for threats, investigates alerts, and helps the organization respond to incidents. The main challenge is scale: analysts review large amounts of evidence and often repeat work that someone else has already done.

ThinkingSOC Lite turns repeated work into knowledge the team can reuse. Analysts spend less time rebuilding searches and can handle more alerts. The documented mid-sized example demonstrates thousands of dollars in annual savings by reducing staffing costs. In larger, high-volume SOCs, savings can reach hundreds of thousands or even millions of dollars, depending on team size, staffing costs, alert volume, and Runbook reuse.

Now, let us follow the workflow. The investigation page keeps the original Splunk alert, verdict, evidence, and analyst timeline in one place. After the analyst acknowledges the investigation, ThinkingSOC Lite turns the accepted findings into a Runbook for that exact Alert Name.

Behind the scenes, Runbook Autopilot coordinates a bounded team of Agents. The Supervisor manages the workflow; Evidence Scout collects context; Runbook Engineer creates fresh read-only SPL; Policy Guard enforces safety rules; and Response Advisor suggests the next step. Tool access uses MCP, with the Splunk REST API available as fallback. Every Agent handoff and tool result is stored in an auditable trace.

The execution graph shows the whole process. Each box explains the step, its SPL parser validation, its source evidence, and its current gate. Reuse stays blocked until every check passes, the Runbook receives human-in-the-loop approval, and the target Alert Name matches exactly.

The Runbook Library groups Runbooks by exact Alert Name. Analysts can search, sort, open details, create an immutable revision without overwriting older versions, and import or export JSON. Each revision keeps its SPL, source evidence, model provenance, performance data, and approval history.

ThinkingSOC Lite tests its results before claiming success. Shadow Evaluation runs the same detection against another alert and measures SPL validation, evidence coverage, speed, errors, and estimated time saved. Missing evidence and incomplete results stay visible, so the system shows what really happened.

Runbook knowledge and Autopilot activity are available in SOC Chat. Analysts can ask why an Agent made a decision, see which tools it used, or ask ThinkingSOC Lite to run an approved Runbook for an alert in plain English. The same safety checks still apply.

ThinkingSOC Lite turns every accepted investigation into a safer, faster, and more useful response to the next alert.
