# Dos and Don'ts — TerraSpectra

Rules for the coding agent (Antigravity) and for you. Where a rule conflicts with a quick shortcut, the rule wins.

## A. Data & Geospatial

**DO**
- Use windowed reads (`rasterio.windows.Window`, chunked HDF5) everywhere.
- Preserve CRS and affine transform through every step; assert it in tests.
- Fit normalization and PCA on the **training split only**, then persist and reuse them.
- Split by scene or spatial block with a buffer gap.
- Write GeoTIFFs tiled and compressed; align HDF5 chunks with tile size.
- Keep `nodata` masks and honour them in loss and metrics.
- Reproject to EPSG:4326 only at the API boundary.
- Record seeds, generator parameters and data origin in `meta.json`.

**DON'T**
- Don't call `src.read()` on a whole cube or `np.load` a full multi-GB array.
- Don't split pixels randomly across train/test (spatial leakage).
- Don't hardcode lat/lon corners in the frontend or backend.
- Don't swap lat/lon order (GeoJSON is `[lon, lat]`; check every library's convention).
- Don't silently drop or fill NaNs; mask them.
- Don't commit raster data or checkpoints to git.

## B. Modeling

**DO**
- Build baselines first (spectral MLP, 2D-CNN, 3D-CNN) and report them next to the hybrid.
- Run at least 3 seeds and report mean ± std.
- Use mixed precision, small patches, and gradient accumulation to control memory.
- Evaluate with F1/AUPRC (class imbalance), lead time, and false-alarm rate.
- Calibrate probabilities before showing them as "risk %".
- Save config, git hash and artefact hashes inside every checkpoint.
- Validate attention-based explanations with a perturbation test.

**DON'T**
- Don't tune on the test split. Touch it once at the end.
- Don't report accuracy alone on imbalanced labels.
- Don't claim real-world three-week prediction from synthetic results.
- Don't make the network huge to chase synthetic scores; check for generator-artefact shortcuts.
- Don't use random geometric augmentations that break georeferencing semantics for inference.
- Don't present attention maps as proven causes.

## C. API / Backend

**DO**
- Keep routers thin and logic in `services/`.
- Load the model once at startup; run inference off the event loop.
- Persist job state; mark orphaned `running` jobs as `failed` at startup.
- Validate every input with Pydantic; return the standard error shape.
- Resolve `source_ref` inside `DATA_ROOT` and reject traversal.
- Serve rasters as tiles/COG, polygons simplified.
- Add tests for each error code.

**DON'T**
- Don't recompute inference in tile or analytics endpoints.
- Don't accept arbitrary filesystem paths from clients.
- Don't block the event loop with GPU or raster work.
- Don't return per-pixel JSON for large scenes.
- Don't enable wide-open CORS in anything but local dev.

## D. Frontend / GIS

**DO**
- Position overlays strictly from API-provided bounds or XYZ tiles.
- Provide a GCP debug overlay and use it for the GIS validation.
- Memoize Deck.gl layers; update through props.
- Debounce slider-driven refetches.
- Keep a visible data-origin badge (SYNTHETIC / PUBLIC / REAL).
- Offer a colour-blind-safe ramp; honour `prefers-reduced-motion`.
- Generate summary sentences from templates using real numbers.

**DON'T**
- Don't recreate layer objects every render.
- Don't use red/green as the only differentiator.
- Don't use an LLM to write the numeric summary text.
- Don't hide the "no inference yet" state; show a clear empty state.
- Don't require a paid Mapbox token for the default build (use MapLibre).

## E. Engineering Hygiene

**DO**
- Pin dependencies; keep environment reproducible (conda or Docker).
- Run `ruff`, `mypy`, `pytest`, `eslint`, `vitest` before declaring a task done.
- Make small commits, one task ID each (e.g., `T1.4: preprocessing`).
- Tick `tasks.md` and update specs when a design decision changes.
- Use config files; no magic numbers in code.
- Log with context (scene id, job id, tile index).

**DON'T**
- Don't leave `print` debugging or commented-out blocks.
- Don't catch broad exceptions and continue silently.
- Don't add dependencies without noting why in the PR/commit.
- Don't skip a review gate because the schedule is tight.
- Don't invent API fields or endpoints that are not in `api-spec.md`; update the spec first.

## F. Communication & Honesty

**DO**
- State limitations in the README: synthetic data, simplified spectral model, no field validation.
- Say plainly when a result did not meet a target and why.
- Cite public datasets and tools used.

**DON'T**
- Don't fabricate metrics, screenshots, or audit numbers; every number must come from a logged run.
- Don't describe the system as production-ready or agronomically validated.

## G. Agent Working Style (for Antigravity)

**DO**
- Read `AGENTS.md`, then the relevant spec file before coding a task.
- Work one task ID at a time; show a short plan; implement; test; report.
- Ask before changing the architecture, data schema, or API contract.
- Prefer the simplest implementation that satisfies the spec; note upgrade paths.
- Write tests alongside code.
- After finishing, summarise: what changed, tests run and results, open issues.

**DON'T**
- Don't refactor unrelated files.
- Don't batch many tasks into one giant change.
- Don't mark a task done while tests fail.
- Don't proceed past a review gate without the evidence file.
