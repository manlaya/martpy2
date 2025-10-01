FC = gfortran
FCFLAGS = -I/mnt/d/Z/Marthe/build/linux-gnu-x64-debug/src/libmarthe    # include dir des mod
LDFLAGS = -L/mnt/d/Z/Marthe/build/linux-gnu-x64-debug/lib -llibmarthe  # link lib sans le préfixe lib et extension .a
LDFLAGS += -L/mnt/d/Z/Marthe/build/linux-gnu-x64-debug/lib -llibutimar_ux_plain

SRC = export_mart_variables.f90
OBJ = $(SRC:.f90=.o)

all: martconf

# memo
# $@ : target, la cible qui doit être générée
# $< : premier prérequis
# $^ : tous les prérequis, sans doublons

martconf: $(OBJ)
	$(FC) -o $@ $^ $(LDFLAGS)

# implicit rule to make object files
%.o: %.f90
	$(FC) $(FCFLAGS) -c $<

clean:
	rm -f *.o martconf
