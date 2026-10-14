# CoinFT transient auto-recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** A transient fault pauses the qualitative animation without destroying its completed demo baseline; fresh healthy data automatically resumes it.

**Architecture:** Split transient pause from hard baseline invalidation in the existing app. Retain frame continuity across temporary display clearing. Real tare/frame-epoch changes remain disarming.

**Tech Stack:** Existing JavaScript Canvas frontend and Python unittest/Chromium browser tests.

## Global constraints

Binding task requirements and exact acceptance cases are in `.superpowers/sdd/auto-recovery-task-1-brief.md`. No automatic tare/zero, no strict-mode relaxation, no backend/firmware/geometry/template edits. No Git repository initialization. User explicitly approved this recovery behavior; prior diagnosis established the clear-baseline mechanism.

## Task 1: Frontend lifecycle and regression tests

- [x] RED reproduction, then surgical implementation, focused and full GREEN tests per task brief.
- [x] Task spec/quality review; strict-only reset finding resolved with RED/GREEN and re-review.
- [x] Broad final review and root fresh full72/72 PASS61.522s exit0; no unresolved Critical/Important.
- [x] Deploy visible page without automatic zero; served/disk hash match, live200Hz/noJSerrors/未归零. PROJECT_LOG.md updated with known offset-detection and physical acceptance limits.
