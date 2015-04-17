.SUFFIXES:
SUFFIXES=
#the subdirs must be in the order of dependencies,
#as the makefiles arn't made to track these dependencies
SUBDIRS = lib src tests

.PHONY: all clean check $(SUBDIRS) subdirs
     
all: subdirs

clean: subdirs

check: subdirs

subdirs:
	@for subdir in $(SUBDIRS) ; do \
		$(MAKE) -C "$${subdir}" $(MAKECMDGOALS) ; \
	done

