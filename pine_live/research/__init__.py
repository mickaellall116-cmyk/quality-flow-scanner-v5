"""Pine V3.6 research namespace — OBSERVATION ONLY.

Research instrumentation for the paper phase. Modules here may READ
``pine_live/paper_state/`` and the dual ledger; they must NEVER write
there, affect paper positions/fills/runner decisions/gate thresholds,
send alerts, or place orders. There is no order path in this namespace
and there never will be. See SHADOW_ADVISOR_SPEC.md and
DELAY_STUDY_SPEC.md (both frozen at pre-registration).
"""
