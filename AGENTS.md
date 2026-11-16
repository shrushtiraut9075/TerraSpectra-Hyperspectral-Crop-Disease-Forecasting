# AGENTS.md — TerraSpectra

You are building **TerraSpectra**, a hyperspectral crop-disease forecasting system: Rasterio/GDAL data pipeline, PyTorch 3D-CNN + ViT model, FastAPI inference service, and a React + Deck.gl dashboard.

## Read first
1. `DOcumentaion/PRD.md` — what and why
2. `DOcumentaion/architecture.md` — structure and decisions
3. The spec for your current task in `DOcumentaion/`: `data-pipeline.md`, `model-spec.md`, `api-spec.md`, or `frontend-spec.md`
4. `DOcumentaion/tasks.md` — your task IDs; `DOcumentaion/dos-and-donts.md` — rules

## Non-negotiables
- **Memory:** windowed reads only. Never load a full cube.
- **Geo:** keep CRS/transform end to end; reproject to EPSG:4326 only at the API edge; never hardcode coordinates.
- **Leakage:** split by scene/spatial block; fit normalization and PCA on train only.
- **Honesty:** data is synthetic unless stated; label it in UI and reports; never invent metrics.
- **Contract:** do not change `api-spec.md` shapes without updating the spec first and asking.
- **Gates:** do not start Week 3 before `memory_audit.md` and `gis_validation.md` exist.

## Stack
Python 3.11, PyTorch 2.x, rasterio/GDAL, h5py, zarr, scikit-learn, FastAPI, Pydantic v2; React 18, TypeScript, Vite, Deck.gl 9, MapLibre, TanStack Query, Zustand, Tailwind.

## Commands
`make test` · `make lint` · `make synth` · `make train` · `make eval` · `make serve` · `make web` · `make demo` · `make audit`

## Workflow per task
1. State the task ID and a 3–5 line plan.
2. Implement in small steps with tests.
3. Run lint + tests; fix failures.
4. Tick the task in `DOcumentaion/tasks.md`.
5. Report: files changed, tests run (with results), anything unresolved.

## Style
- Type hints everywhere in Python; `ruff` and `mypy` clean.
- Strict TypeScript; no `any` without a comment.
- Config in YAML under `configs/`; no magic numbers.
- Small functions, clear names, docstrings on public functions.
- Commit message format: `T<id>: <what>`.

## Ask the human when
- A choice changes architecture, data schema, or the API contract.
- A dependency is heavy or has licensing concerns.
- Results miss targets and the next step is unclear.
