TARGET      := triforce-hello
BUILD       := build
SOURCES     := source
DATA        :=
INCLUDES    :=

CFLAGS      := -O2 -Wall -Wextra
CXXFLAGS    := $(CFLAGS)
LDFLAGS     :=
LIBS        := -logc -lm

include $(DEVKITPPC)/gamecube_rules
