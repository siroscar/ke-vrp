IMG=kenya-vrp:dev
RUN=docker run --rm --cpus=2 -v $(PWD):/workspace -w /workspace $(IMG)

build:
	docker build -t $(IMG) .
test:
	$(RUN) pytest -q
smoke:
	$(RUN) python -m kvrp.run --sizes 40 --seeds 1 --runtime 5 --out results/smoke
experiment:
	$(RUN) python -m kvrp.run --sizes 50 100 200 --seeds 5 --runtime 30 --out results/main
shell:
	docker run --rm -it --cpus=2 -v $(PWD):/workspace -w /workspace $(IMG) bash
