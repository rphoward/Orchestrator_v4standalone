"""
Composition root: wires infrastructure adapters into core use cases.

May import all layers. Domain code in ``core/`` must not import this module.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

from orchestrator_v4.infrastructure.runtime_executable_layout import (
    bundle_extract_directory,
    executable_directory,
    is_frozen_bundle,
)
from orchestrator_v4.runtime_paths import resolve_orchestrator_db_path
from orchestrator_v4.core.use_cases.conduct_interview_turn import ConductInterviewTurn
from orchestrator_v4.core.use_cases.conduct_manual_interview_turn import (
    ConductManualInterviewTurn,
)
from orchestrator_v4.core.use_cases.finalize_interview_session import FinalizeInterviewSession
from orchestrator_v4.core.use_cases.initialize_interview_session import (
    InitializeInterviewSession,
)
from orchestrator_v4.core.use_cases.create_interview_session import CreateInterviewSession
from orchestrator_v4.core.use_cases.delete_interview_session import DeleteInterviewSession
from orchestrator_v4.core.use_cases.list_interview_sessions import ListInterviewSessions
from orchestrator_v4.core.use_cases.load_interview_prompt_body import LoadInterviewPromptBody
from orchestrator_v4.core.use_cases.prompt_template_catalog import (
    CreatePromptTemplate,
    DeletePromptTemplate,
    ListPromptTemplates,
    UpdatePromptTemplate,
)
from orchestrator_v4.core.use_cases.load_interview_session_conversations import (
    LoadInterviewSessionConversations,
)
from orchestrator_v4.core.use_cases.load_interview_session_for_export import LoadInterviewSessionForExport
from orchestrator_v4.core.use_cases.load_interview_session_routing_logs import (
    LoadInterviewSessionRoutingLogs,
)
from orchestrator_v4.core.use_cases.read_agent_overrides import ReadAgentOverrides
from orchestrator_v4.core.use_cases.update_interview_session import UpdateInterviewSession
from orchestrator_v4.infrastructure.ai.gemini_interview_llm_gateway import (
    GeminiInterviewLlmGateway,
)
from orchestrator_v4.infrastructure.ai.gemini_stage_completion_judge import (
    GeminiStageCompletionJudge,
)
from orchestrator_v4.infrastructure.persistence.cached_prompt_file_reader import (
    CachedPromptFileReader,
)
from orchestrator_v4.infrastructure.persistence.sqlite_interview_session_turn_store import (
    SqliteInterviewSessionTurnStore,
)
from orchestrator_v4.infrastructure.stubs.fake_interview_llm_gateway import FakeInterviewLlmGateway
from orchestrator_v4.infrastructure.stubs.fake_stage_completion_judge import (
    FakeStageCompletionJudge,
)
from orchestrator_v4.infrastructure.persistence.sqlite_agent_configuration_store import (
    SqliteAgentConfigurationStore,
)
from orchestrator_v4.infrastructure.persistence.sqlite_agent_override_reader import (
    SqliteAgentOverrideReader,
)
from orchestrator_v4.infrastructure.persistence.sqlite_prompt_template_store import (
    SqlitePromptTemplateStore,
)
from orchestrator_v4.infrastructure.persistence.sqlite_template_aware_prompt_body_source import (
    SqliteTemplateAwarePromptBodySource,
)
from orchestrator_v4.infrastructure.persistence.sqlite_interview_session_catalog import (
    SqliteInterviewSessionCatalog,
)
from orchestrator_v4.infrastructure.persistence.sqlite_interview_session_reader import (
    SqliteInterviewSessionReader,
)
from orchestrator_v4.infrastructure.persistence.sqlite_model_registry_store import (
    SqliteModelRegistryStore,
)
from orchestrator_v4.infrastructure.persistence.sqlite_interview_session_importer import (
    SqliteInterviewSessionImporter,
)
from orchestrator_v4.infrastructure.persistence.orchestrator_sqlite_bootstrap import (
    ensure_orchestrator_database,
)
from orchestrator_v4.infrastructure.ai.generative_language_models import run_model_verify

_LOG = logging.getLogger(__name__)


def _src_dir() -> str:
    """Directory containing this composition root (`orchestrator_v4/`)."""
    return os.path.dirname(os.path.abspath(__file__))


# `.env` before GEMINI_API_KEY: next to .exe when frozen, else this package folder (dev).
if is_frozen_bundle():
    load_dotenv(os.path.join(executable_directory(), ".env"))
else:
    load_dotenv(os.path.join(_src_dir(), ".env"))


def _default_prompts_root() -> str:
    """Bundled spine Markdown: ``_MEIPASS/runtime/prompts`` when frozen, else ``orchestrator_v4/runtime/prompts``."""
    if is_frozen_bundle():
        return os.path.join(bundle_extract_directory(), "runtime", "prompts")
    return os.path.join(_src_dir(), "runtime", "prompts")


def resolve_prompts_root() -> str:
    """Optional override via ORCHESTRATOR_PROMPTS_ROOT for tests or custom installs."""
    return os.environ.get("ORCHESTRATOR_PROMPTS_ROOT", _default_prompts_root())


# Same idea as v3 app startup: create DB file + tables; seed default agents if empty.
ensure_orchestrator_database(resolve_orchestrator_db_path())

_override_reader = SqliteAgentOverrideReader(resolve_orchestrator_db_path())
read_agent_overrides = ReadAgentOverrides(_override_reader)

agent_config_store = SqliteAgentConfigurationStore(
    resolve_orchestrator_db_path(),
    resolve_prompts_root(),
)

_prompt_cache = CachedPromptFileReader(resolve_prompts_root())
_prompt_body_source = SqliteTemplateAwarePromptBodySource(
    resolve_orchestrator_db_path(),
    resolve_prompts_root(),
    prompt_cache=_prompt_cache,
)
load_interview_prompt_body = LoadInterviewPromptBody(_prompt_body_source)

_prompt_template_store = SqlitePromptTemplateStore(resolve_orchestrator_db_path())
list_prompt_templates = ListPromptTemplates(_prompt_template_store)
create_prompt_template = CreatePromptTemplate(_prompt_template_store)
update_prompt_template = UpdatePromptTemplate(_prompt_template_store)
delete_prompt_template = DeletePromptTemplate(_prompt_template_store)

_session_catalog = SqliteInterviewSessionCatalog(resolve_orchestrator_db_path())
list_interview_sessions = ListInterviewSessions(_session_catalog)
create_interview_session = CreateInterviewSession(_session_catalog)
update_interview_session = UpdateInterviewSession(_session_catalog)
delete_interview_session = DeleteInterviewSession(_session_catalog)

_session_reader = SqliteInterviewSessionReader(resolve_orchestrator_db_path())
load_interview_session_for_export = LoadInterviewSessionForExport(_session_reader)
load_interview_session_conversations = LoadInterviewSessionConversations(_session_reader)
load_interview_session_routing_logs = LoadInterviewSessionRoutingLogs(_session_reader)

_turn_store = SqliteInterviewSessionTurnStore(
    resolve_orchestrator_db_path(),
    resolve_prompts_root(),
    prompt_cache=_prompt_cache,
    prompt_body_source=_prompt_body_source,
)

model_registry_store = SqliteModelRegistryStore(resolve_orchestrator_db_path())

_gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
gemini_api_key = _gemini_api_key
gemini_api_key_configured = bool(_gemini_api_key)


def _resolved_router_model_id() -> str:
    """Router model id: non-empty ``ORCHESTRATOR_ROUTER_MODEL`` wins; else SQLite/registry."""
    env = (os.environ.get("ORCHESTRATOR_ROUTER_MODEL") or "").strip()
    if env:
        return env
    return model_registry_store.get_router_model()


def _resolved_agent_fallback_model_id() -> str:
    """Default agent model when per-turn model is blank: env ``ORCHESTRATOR_AGENT_MODEL`` or registry."""
    env = (os.environ.get("ORCHESTRATOR_AGENT_MODEL") or "").strip()
    if env:
        return env
    return model_registry_store.get_default_active_model_id()


def rebind_llm_gateway() -> None:
    """Rebuild the LLM gateway + stage-completion judge from the current API key
    and model registry (and env overrides)."""
    global _llm_gateway, _stage_completion_judge, stage_completion_judge
    global conduct_interview_turn, initialize_session, conduct_manual_turn, finalize_session

    if gemini_api_key_configured and _gemini_api_key:
        rid = _resolved_router_model_id()
        afid = _resolved_agent_fallback_model_id()
        r_env = bool((os.environ.get("ORCHESTRATOR_ROUTER_MODEL") or "").strip())
        _LOG.info(
            "effective_router_model=%s agent_fallback_model=%s router_from_env=%s",
            rid,
            afid,
            r_env,
        )
        _llm_gateway = GeminiInterviewLlmGateway(
            api_key=_gemini_api_key,
            router_model=rid,
            agent_model=afid,
        )
        _stage_completion_judge = GeminiStageCompletionJudge(
            api_key=_gemini_api_key,
            prompt_cache=_prompt_cache,
            judge_model=afid,
        )
        _LOG.info(
            "LLM gateway: live Gemini API (router=%s); stage_completion_judge=%s",
            rid,
            afid,
        )
    else:
        _llm_gateway = FakeInterviewLlmGateway()
        # ``judge_error:`` prefix triggers the use-case heuristic fallback so
        # offline dev, pytest, and --smoke still advance stage flags by the
        # 2-user-chat rule. See .cursor/plans/stage-completion-judge_*.plan.md
        # slice 8 for the rationale.
        _stage_completion_judge = FakeStageCompletionJudge(
            default_reason="judge_error: offline stub"
        )
        _LOG.warning(
            "LLM gateway: offline stub — no GEMINI_API_KEY at startup. "
            "Routing logs show reason %r; replies prefix your message with %r (no API calls). "
            "Stage-completion judge falls back to the 2-user-chat heuristic. "
            "Put GEMINI_API_KEY in .env next to bootstrap.py or save a key under Settings.",
            "stub-route",
            "echo:",
        )

    stage_completion_judge = _stage_completion_judge
    conduct_interview_turn = ConductInterviewTurn(
        _turn_store, _llm_gateway, _stage_completion_judge
    )
    initialize_session = InitializeInterviewSession(_turn_store, _llm_gateway)
    conduct_manual_turn = ConductManualInterviewTurn(
        _turn_store, _llm_gateway, _stage_completion_judge
    )
    finalize_session = FinalizeInterviewSession(_turn_store, _llm_gateway)


rebind_llm_gateway()

_session_importer = SqliteInterviewSessionImporter(resolve_orchestrator_db_path())
import_session = _session_importer


def execute_model_id_verify() -> dict[str, Any]:
    """Preflight: ``models.list`` + public deprecations doc vs in-use ids (composition-root entry)."""
    return run_model_verify((gemini_api_key or "").strip(), resolve_orchestrator_db_path())


def apply_gemini_api_key(key: str) -> None:
    """
    Persist runtime Gemini key state and rebuild the LLM gateway so Settings can rewire
    without restart.

    ``GEMINI_API_KEY`` is authentication only. ``ORCHESTRATOR_ROUTER_MODEL`` and
    ``ORCHESTRATOR_AGENT_MODEL`` (when non-empty) are **model id** overrides for the
    live gateway, not secrets; unset them to use SQLite / Settings registry resolution.
    """
    global _gemini_api_key, gemini_api_key, gemini_api_key_configured

    stripped = (key or "").strip()
    _gemini_api_key = stripped
    gemini_api_key = stripped
    gemini_api_key_configured = bool(stripped)
    if stripped:
        os.environ["GEMINI_API_KEY"] = stripped
    else:
        os.environ.pop("GEMINI_API_KEY", None)

    rebind_llm_gateway()


def invalidate_prompt_runtime_cache(agent_id: int | None = None) -> None:
    """
    Explicit cache invalidation hook for runtime prompt/template coherence.
    Invalidates both the prompt-body and turn-store read paths.
    """
    _prompt_body_source.invalidate_prompt_cache(agent_id)
    _turn_store.invalidate_prompt_cache(agent_id)
