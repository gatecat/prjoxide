ARCH?=LIFCL

fuzzers=$(wildcard fuzzers/$(ARCH)/*)
stamps=$(patsubst %,%/work/stamp,$(fuzzers)) 

all: $(stamps)

%/work/stamp:
	cd $* && $(MAKE)

