all: $(foreach run,$(RUNS),work/$(run).stamp)

BASE_DIR=../../../../
OUT_DIR=../../../output/

work/design_%.v: $(GENERATOR)
	mkdir -p work/
	python $(GENERATOR) > $@

work/design_%.bit: work/design_%.v
	$(BASE_DIR)/radiant.sh $(DEVICE) $< || $(ALLOW_FAIL)

work/%.stamp: work/design_%.bit
	mkdir -p $(OUT_DIR)

	python $(BASE_DIR)/timing/util/extract_route.py work/design_$*.tmp/par.udb $(OUT_DIR)/$(NAME)_$*_route.pickle

	# we need the '|| true' because of
	# malloc_consolidate(): unaligned fastbin chunk detected

	$(BASE_DIR)/radiant_cmd.sh backanno -sp 4 -w -o $(OUT_DIR)/$(NAME)_$*_4.vo work/design_$*.tmp/par.udb || true
	$(BASE_DIR)/radiant_cmd.sh backanno -sp 5 -w -o $(OUT_DIR)/$(NAME)_$*_5.vo work/design_$*.tmp/par.udb || true
	$(BASE_DIR)/radiant_cmd.sh backanno -sp 6 -w -o $(OUT_DIR)/$(NAME)_$*_6.vo work/design_$*.tmp/par.udb || true

	$(BASE_DIR)/radiant_cmd.sh backanno -sp 10 -w -o $(OUT_DIR)/$(NAME)_$*_10.vo work/design_$*.tmp/par.udb || true
	$(BASE_DIR)/radiant_cmd.sh backanno -sp 11 -w -o $(OUT_DIR)/$(NAME)_$*_11.vo work/design_$*.tmp/par.udb || true
	$(BASE_DIR)/radiant_cmd.sh backanno -sp 12 -w -o $(OUT_DIR)/$(NAME)_$*_12.vo work/design_$*.tmp/par.udb || true

	$(BASE_DIR)/radiant_cmd.sh backanno -min -w -o $(OUT_DIR)/$(NAME)_$*_M.vo work/design_$*.tmp/par.udb || true

	touch $@

.PRECIOUS: %.v
