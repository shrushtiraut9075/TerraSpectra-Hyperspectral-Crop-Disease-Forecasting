.PHONY: test lint synth train eval serve web demo audit dev clean

PYTHON = .venv/Scripts/python.exe
PYTEST = .venv/Scripts/pytest.exe
RUFF = .venv/Scripts/ruff.exe
MYPY = .venv/Scripts/mypy.exe

dev:
	start $(PYTHON) -m uvicorn api.main:app --reload --port 8000
	cd web && npm run dev

test:
	$(PYTEST) tests/
	cd web && npm test

lint:
	$(RUFF) check ml api tests
	$(MYPY) ml api

synth:
	$(PYTHON) -m ml.data.synth --config configs/data.yaml

train:
	$(PYTHON) -m ml.train --model-config configs/model.yaml --train-config configs/train.yaml

eval:
	$(PYTHON) -m ml.evaluate --checkpoint artifacts/checkpoints/best_model.pt

serve:
	$(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000

web:
	cd web && npm run dev

audit:
	$(PYTHON) -m ml.utils.bench --audit

demo:
	$(PYTHON) -m ml.data.synth --config configs/data.yaml --demo
	$(PYTHON) -m ml.infer --demo
	start $(PYTHON) -m uvicorn api.main:app --port 8000
	cd web && npm run dev

clean:
	rm -rf artifacts/checkpoints/* artifacts/reports/*

