.PHONY: new-draft

new-draft:
ifndef SPEC
	$(error SPEC is required. Usage: make new-draft SPEC=transport FROM=draft14 TO=draft15)
endif
ifndef FROM
	$(error FROM is required. Usage: make new-draft SPEC=transport FROM=draft14 TO=draft15)
endif
ifndef TO
	$(error TO is required. Usage: make new-draft SPEC=transport FROM=draft14 TO=draft15)
endif
	cp -r $(SPEC)/$(FROM) $(SPEC)/$(TO)
	@echo "Copied $(SPEC)/$(FROM) → $(SPEC)/$(TO). Update meta.json and modify changed vectors."
