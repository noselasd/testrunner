.SUFFIXES:
SUFFIXES=
SUBDIRS = test_api

.PHONY: all clean check $(SUBDIRS) subdirs
     
all: subdirs

clean: subdirs
	@rm -f testsuite.log

check: subdirs

subdirs:
	@for subdir in $(SUBDIRS) ; do \
		$(MAKE) -C "$${subdir}" $(MAKECMDGOALS) ; \
	done

check:
	../../testrunner.py testsuite

