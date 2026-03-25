from pathlib import Path
from typing import Optional

from src.models.app_schemas import (
    BatchFileError,
    InvoiceGraphState,
    InvoiceProcessingResult,
    PresetBatchResponse,
)
from src.models.policy_schemas import PolicySettings, PolicySettingsPatch
from src.service.graph import build_invoice_graph
from src.service.ingest import extract_content_type
from src.service.invoice_policy import DuplicateRegistry, PolicySettingsHolder, load_policy_settings
from src.service.temp_storage import clear_content_hash_dir, clear_invoice_temp_dir

_INVOICE_SUFFIXES = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"})

# Repo root: src/service/invoice_service.py -> parents[2] == project root (not process cwd).
_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_data_dir(data_dir: str) -> Path:
    """Resolve data_dir; relative paths are under the repo root (uvicorn cwd may differ)."""
    p = Path(data_dir)
    return p.resolve() if p.is_absolute() else (_REPO_ROOT / p).resolve()


class InvoiceService:
    """Owns the graph, policy holder, and duplicate registry."""

    def __init__(
        self,
        *,
        llm_type: str = "openai",
        policy_path: Optional[Path] = None,
        duplicates: Optional[DuplicateRegistry] = None,
    ) -> None:
        self._policy_path = policy_path
        self._llm_type = llm_type
        self._policy_holder = PolicySettingsHolder(load_policy_settings(policy_path))
        self._duplicates = duplicates or DuplicateRegistry()
        self._graph = build_invoice_graph(
            llm_type=llm_type,
            policy_holder=self._policy_holder,
            duplicates=self._duplicates,
        )

    async def process_file(
        self,
        data: bytes,
        *,
        filename: str = "",
        content_type: str | None = None,
    ) -> InvoiceProcessingResult:
        ct = content_type or _extract_content_type_from_name(filename)
        state = InvoiceGraphState(filename=filename, content_type=ct, raw_data=data)
        out = await self._graph.ainvoke(state)
        return out["final"]

    async def process_preset_dir(self, directory: Path) -> PresetBatchResponse:
        """Process each invoice in a folder (not subfolders)."""
        results: list[InvoiceProcessingResult] = []
        errors: list[BatchFileError] = []
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in _INVOICE_SUFFIXES:
                continue
            try:
                data = path.read_bytes()
                ct = extract_content_type(path)
                results.append(await self.process_file(data, filename=path.name, content_type=ct))
            except Exception as exc:  # noqa: BLE001
                errors.append(BatchFileError(filename=path.name, detail=str(exc)))
        return PresetBatchResponse(
            data_dir=str(directory.resolve()),
            results=results,
            errors=errors,
        )

    def reset_for_new_request(self) -> None:
        """Clear temp files and duplicate fingerprints before a new request."""
        clear_invoice_temp_dir()
        clear_content_hash_dir()
        self._duplicates.clear()

    def get_llm_type(self) -> str:
        return self._llm_type

    def set_llm_type(self, llm_type: str) -> str:
        if llm_type not in ("openai", "ollama"):
            raise ValueError(f"Unsupported llm_type: {llm_type!r}")
        self._llm_type = llm_type
        self._graph = build_invoice_graph(
            llm_type=llm_type,
            policy_holder=self._policy_holder,
            duplicates=self._duplicates,
        )
        return self._llm_type

    def get_policy_settings(self) -> PolicySettings:
        return self._policy_holder.get()

    def apply_policy_patch(self, patch: PolicySettingsPatch) -> PolicySettings:
        cur = self._policy_holder.get().model_dump()
        limits = {**cur["limits"], **(patch.limits or {})}
        merged = PolicySettings.model_validate({"limits": limits})
        self._policy_holder.set(merged)
        return merged

    def get_policy_defaults_from_file(self) -> PolicySettings:
        """Read policy.yaml without applying it."""
        return load_policy_settings(self._policy_path)

    def reset_policy_from_file(self) -> PolicySettings:
        """Reload live limits from policy.yaml."""
        s = load_policy_settings(self._policy_path)
        self._policy_holder.set(s)
        return s


def _extract_content_type_from_name(name: str) -> str:
    return extract_content_type(Path(name))
