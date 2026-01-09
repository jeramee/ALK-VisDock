SITE?=site
PDB?=2XP2

.PHONY: build serve clean

build:
	python -m alk_visdock build --out $(SITE) --ligands examples/ligands.csv --pdb-id $(PDB)

serve:
	python -m alk_visdock serve --site $(SITE) --port 8000

clean:
	rm -rf $(SITE)
