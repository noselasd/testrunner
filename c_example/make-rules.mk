# Variables that can be set:
# PROGRAM          - will create an executable of all .c sources in 
#					 the current direectory
# STATICLIB		   - will create a static library of all .c sources
#					 in the current directory
# SUBDIRS		   - Will call make recursivly on these directories
# EXTRA_CLEAN	   - will rm -f these files on "make clean"
# CC			   - C compiler executable
# LD			   - Linker executable
# CFLAGS		   - C compiler flags
# CPPFLAGS		   - C preprocessor flags
# LDFLAGS		   - Linker flags
# LDLIBS           - Linker libraries
# AR			   - static library archive executable
# RM			   - executable to remove files
# RMDIR            - executable to remove directory
# PROGRAM_DEPS	   - extra dependencies for PROGRAM
# STATICLIB_DEPS   - extra dependencies for STATICLIB
# STACK_PROTECT    - set to yes to build with stack protection
#
# make targets
# 	all 		   - will build the PROGRAM and/or STATICLIB
# 	check		   - Run test suites (depends on the default(all) target)
# 	clean		   - clean up
# 	real_check	   - Can be createn in a subdir to actuall run tests
# 	                 on 'make check'

MAKEFLAGS += --no-builtin-rules
.SUFFIXES: 
SUFFIXES=

ifndef DEBUG
VARIANT_CFLAGS		?= -O2
VARIANT_CPPFLAGS	?= -DNDEBUG
else
VARIANT_CPPFLAGS	?= -DDEBUG
endif

COMMON_CFLAGS	?= -Wall -Wextra -Wno-unused-parameter -ggdb -pipe
COMMON_CPPFLAGS	?= -D_FILE_OFFSET_BITS=64

ifeq ($(STACK_PROTECT), yes)
COMMON_CFLAGS   += -fstack-protector --param=ssp-buffer-size=4
COMMON_CPPFLAGS += -D_FORTIFY_SOURCE=2
endif
COMMON_LDFLAGS	=

CC				=  cc
LD				=  $(CC)
ALL_CFLAGS		?= $(COMMON_CFLAGS) $(VARIANT_CFLAGS) $(CFLAGS)
ALL_CPPFLAGS  	?= $(COMMON_CPPFLAGS) $(VARIANT_CPPFLAGS) $(CPPFLAGS)
ALL_LDLIBS		?= $(LDLIBS)
ALL_LDFLAGS		?= $(COMMON_LDFLAGS) $(LDFLAGS)
AR			 	= ar
ARFLAGS			= cru
ALL_ARFLAGS		?= $(ARFLAGS)
RM				= rm -f
RMDIR			= rmdir

OBJDIR=build
OBJECTS = $(addprefix $(OBJDIR)/,$(notdir $(SOURCES:.c=.o)))
DEPS   = $(addprefix $(OBJDIR)/,$(notdir $(SOURCES:.c=.d)))


.PHONY: $(SUBDIRS) subdirs
all: subdirs $(PROGRAM) $(STATICLIB)
	@echo -en "\007"

$(OBJDIR)/%.d: %.c
	$(CC) -MM -MG $(ALL_CPPFLAGS) $(ALL_CFLAGS) -MF  $@ $<

$(OBJDIR)/%.o: %.c
	$(CC) $(ALL_CPPFLAGS) $(ALL_CFLAGS) -c -o $@ $<

$(STATICLIB): $(OBJECTS) 
	$(AR) $(ALL_ARFLAGS)  $@ $^ 

$(PROGRAM): $(OBJECTS) $($(PROGRAM)_DEPENDS)
	$(LD) $(ALL_LDFLAGS) -o $@ $^ $(ALL_LDLIBS)


$(OBJDIR):
	@test -d $(OBJDIR) || mkdir -p ./$(OBJDIR)

$(OBJECTS): | $(OBJDIR)
$(DEPS): | $(OBJDIR)

.PHONY: clean 
clean:: subdirs 
	-$(RM) $(PROGRAM) $(OBJECTS) $(DEPS) $(STATICLIB)
	-test -d $(OBJDIR) && $(RMDIR) ./$(OBJDIR) || true
ifneq (,$(EXTRA_CLEAN))
	-$(RM) -f $(EXTRA_CLEAN)
endif

subdirs:
	@for subdir in $(SUBDIRS) ; do \
		$(MAKE) -C "$${subdir}" $(MAKECMDGOALS) ; \
	done

.PHONY: check real_check
check: all real_check

ifeq (,$(findstring clean, $(MAKECMDGOALS)))
-include $(DEPS)
endif

