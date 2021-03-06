appKernelRunEnvironmentTemplate="""
#Load application enviroment
module load intel/13.0
module load intel-mpi/4.1.0
module list

MKLROOT=/panfs/panfs.ccr.buffalo.edu/projects/ccrstaff/general/appker/edge12core/execs/lib/mkl
source $MKLROOT/bin/mklvars.sh intel64
export I_MPI_PMI_LIBRARY=/usr/lib64/libpmi.so

ulimit -s unlimited

#set how to run app kernel
RUN_APPKERNEL="srun {appKerDir}/{executable}"
"""
