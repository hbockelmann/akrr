info = """"""

walllimit=180
parser="xdmod.benchmark.io.ior.py"
#path to run script relative to AppKerDir on particular resource
executable="execs/ior"
input="inputs"

#if true will run single node benchmark on two nodes to trick node's caching, write on first node and read on second
requestTwoNodesForOneNodeAppKer=True

#which IO API/formats to check
testPOSIX=True
testMPIIO=True
testHDF5=True
testNetCDF=True

#will do write test first and after that read, that minimize the caching impact from storage nodes
#require large temporary storage easily 100s GiB 
doAllWritesFirst=True

runScriptPreRun="""
# MPI IO hints (optional)
# MPI IO hints are environment variables in the following format:
#
# 'IOR_HINT__<layer>__<hint>=<value>', where <layer> is either 'MPI'
# or 'GPFS', <hint> is the full name of the hint to be set, and <value>
# is the hint value.  E.g., 'export IOR_HINT__MPI__IBM_largeblock_io=true'
# 'export IOR_HINT__GPFS__hint=value' in mpi_io_hints
{mpi_io_hints}

#create working dir
export AKRR_TMP_WORKDIR=`mktemp -d {networkScratch}/ior.XXXXXXXXX`
echo "Temporary working directory: $AKRR_TMP_WORKDIR"
cd $AKRR_TMP_WORKDIR
"""

runScriptAK="""
perProcData="200m"
perProcXferSize="20m"

exe=$EXE
extraOpts="-b $perProcData -t $perProcXferSize -Z"
testOpts="-a POSIX
-a POSIX -F
-a MPIIO 
-a MPIIO -c
-a MPIIO -F
-a HDF5 
-a HDF5 -c
-a HDF5 -F
-a NCMPI 
-a NCMPI -c
"

# change bash's Internal Field Separator 
# to "\\n" only (by default it's "\\n\\t ")
oldIFS=$IFS
IFS=$'\\n'
# run the tests
echo "Using $AKRR_TMP_WORKDIR for test...." >> $AKRR_APP_STDOUT_FILE 2>&1
echo "\\\"appKerStartTime\\\":\\\""`date`"\\\"," >> $AKRR_TASK_WORKDIR/gen.info
for testOpt in $testOpts
do
    fileName=`echo $testOpt |tr  '[\- ]' '[__]'`
    if [[ "$testOpt" =~ "-c" ]]; then
      export IOR_HINT__MPI__panfs_concurrent_write=1
    else
      unset IOR_HINT__MPI__panfs_concurrent_write
    fi

    eval "$RUNMPI $exe $testOpt $extraOpts -o $AKRR_TMP_WORKDIR/$fileName" >> $AKRR_APP_STDOUT_FILE 2>&1
    sleep 3
done
echo "\\\"appKerEndTime\\\":\\\""`date`"\\\"," >> $AKRR_TASK_WORKDIR/gen.info
IFS=$oldIFS
"""
runScriptAK2="""
perProcData="200m"
perProcXferSize="20m"

exe=$EXE
extraOpts="-b $perProcData -t $perProcXferSize -C -v -v -v -Q $AKRR_CORES_PER_NODE"
testOpts="-a POSIX
-a POSIX -F
-a MPIIO 
-a MPIIO -c
-a MPIIO -F
-a HDF5 
-a HDF5 -c
-a HDF5 -F
-a NCMPI 
-a NCMPI -c
"

# change bash's Internal Field Separator 
# to "\\n" only (by default it's "\\n\\t ")
oldIFS=$IFS
IFS=$'\\n'
# run the tests
echo "Using $AKRR_TMP_WORKDIR for test...." >> $AKRR_APP_STDOUT_FILE 2>&1
echo "\\\"appKerStartTime\\\":\\\""`date`"\\\"," >> $AKRR_TASK_WORKDIR/gen.info
for testOpt in $testOpts
do
    eval "$RUNMPI $exe $testOpt $extraOpts -o $AKRR_TMP_WORKDIR/$fileName" >> $AKRR_APP_STDOUT_FILE 2>&1
    sleep 3
done
echo "\\\"appKerEndTime\\\":\\\""`date`"\\\"," >> $AKRR_TASK_WORKDIR/gen.info
IFS=$oldIFS

"""

iorCommonTestParam="-b 200m -t 20m"
iorTestsList="""("-a POSIX"
"-a POSIX -F"
"-a MPIIO "
"-a MPIIO -c"
"-a MPIIO -F"
"-a HDF5 "
"-a HDF5 -c"
"-a HDF5 -F"
"-a NCMPI "
"-a NCMPI -c")"""

akrrRunAppKernelTemplate="""
#blockSize and transferSize
COMMON_TEST_PARAM="{iorCommonTestParam}"
#2 level of verbosity, don't clear memory
COMMON_OPTIONS="-vv"
CACHING_BYPASS="-Z"

#list of test to perform
TESTS_LIST={iorTestsList}

#combine common parameters
COMMON_PARAM="$COMMON_OPTIONS $RESOURCE_SPECIFIC_OPTION $CACHING_BYPASS $COMMON_TEST_PARAM"


echo "Using $AKRR_TMP_WORKDIR for test...." >> $AKRR_APP_STDOUT_FILE 2>&1

#determine filesystem for file
canonicalFilename=`readlink -f $AKRR_TMP_WORKDIR`
filesystem=`awk -v canonical_path="$canonicalFilename" '{{if ($2!="/" && 1==index(canonical_path, $2)) print $3 " " $1 " " $2;}}' /proc/self/mounts`
echo "File System To Test: $filesystem" >> $AKRR_APP_STDOUT_FILE 2>&1
writeToGenInfo "fileSystem" "$filesystem"

#start the tests
writeToGenInfo "appKerStartTime" "`date`"
{runIORTests}
writeToGenInfo "appKerEndTime" "`date`"

"""

runIORTestsWriteReadCyclic="""
for TEST_PARAM in "${{TESTS_LIST[@]}}"
do
    echo "# Starting Test: $TEST_PARAM" >> $AKRR_APP_STDOUT_FILE 2>&1
    fileName=`echo ior_test_file_$TEST_PARAM |tr  '-' '_'|tr  ' ' '_'|tr  '=' '_'`
    
    #run the test
    command_to_run="$RUNMPI $EXE $COMMON_PARAM $TEST_PARAM -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
done
"""

runIORTestsAllWritesFirst="""
#do write first
for TEST_PARAM in "${{TESTS_LIST[@]}}"
do
    echo "# Starting Test: $TEST_PARAM" >> $AKRR_APP_STDOUT_FILE 2>&1
    fileName=`echo ior_test_file_$TEST_PARAM |tr  '-' '_'|tr  ' ' '_'|tr  '=' '_'`
    
    #run the test
    command_to_run="$RUNMPI $EXE $COMMON_PARAM $TEST_PARAM -w -k -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
done
#do read last
for TEST_PARAM in "${{TESTS_LIST[@]}}"
do
    echo "# Starting Test: $TEST_PARAM" >> $AKRR_APP_STDOUT_FILE 2>&1
    fileName=`echo ior_test_file_$TEST_PARAM |tr  '-' '_'|tr  ' ' '_'|tr  '=' '_'`
    
    #run the test
    command_to_run="$RUNMPI_OFFSET $EXE $COMMON_PARAM $TEST_PARAM -r -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
done
"""
runIORTestsWriteReadCyclicOneNode="""
for TEST_PARAM in "${{TESTS_LIST[@]}}"
do
    echo "# Starting Test: $TEST_PARAM" >> $AKRR_APP_STDOUT_FILE 2>&1
    fileName=`echo ior_test_file_$TEST_PARAM |tr  '-' '_'|tr  ' ' '_'|tr  '=' '_'`
    
    #run the test
    command_to_run="$RUNMPI $EXE $COMMON_PARAM $TEST_PARAM -w -k -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
    
    command_to_run="$RUNMPI_OFFSET $EXE $COMMON_PARAM $TEST_PARAM -r -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
done
"""

runIORTestsAllWritesFirstOneNode="""
#do write first
for TEST_PARAM in "${{TESTS_LIST[@]}}"
do
    echo "# Starting Test: $TEST_PARAM" >> $AKRR_APP_STDOUT_FILE 2>&1
    fileName=`echo ior_test_file_$TEST_PARAM |tr  '-' '_'|tr  ' ' '_'|tr  '=' '_'`
    
    #run the tests
    command_to_run="$RUNMPI $EXE $COMMON_PARAM $TEST_PARAM -w -k -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
done
#do read last
for TEST_PARAM in "${{TESTS_LIST[@]}}"
do
    echo "# Starting Test: $TEST_PARAM" >> $AKRR_APP_STDOUT_FILE 2>&1
    fileName=`echo ior_test_file_$TEST_PARAM |tr  '-' '_'|tr  ' ' '_'|tr  '=' '_'`
    
    #run the tests
    command_to_run="$RUNMPI_OFFSET $EXE $COMMON_PARAM $TEST_PARAM -r -o $AKRR_TMP_WORKDIR/$fileName"
    echo "executing: $command_to_run" >> $AKRR_APP_STDOUT_FILE 2>&1
    $command_to_run >> $AKRR_APP_STDOUT_FILE 2>&1
done
"""

runScriptPostRun="""
#clean-up
cd $AKRR_TASK_WORKDIR
if [ "${{AKRR_DEBUG=no}}" = "no" ]
then
        echo "Deleting temporary files"
        rm -rf $AKRR_TMP_WORKDIR
else
        echo "Copying temporary files"
        cp -r $AKRR_TMP_WORKDIR workdir
        rm -rf $AKRR_TMP_WORKDIR
fi
"""

def process_params(params):
    tests=[]
    if params['testPOSIX']: tests.extend(['"-a POSIX $RESOURCE_SPECIFIC_OPTION_N_to_1"',
                                          '"-a POSIX -F $RESOURCE_SPECIFIC_OPTION_N_to_N"'])
    if params['testMPIIO']: tests.extend(['"-a MPIIO $RESOURCE_SPECIFIC_OPTION_N_to_1"',
                                          '"-a MPIIO -c $RESOURCE_SPECIFIC_OPTION_N_to_1"',
                                          '"-a MPIIO -F $RESOURCE_SPECIFIC_OPTION_N_to_N"'])
    if params['testHDF5']:  tests.extend(['"-a HDF5 $RESOURCE_SPECIFIC_OPTION_N_to_1"',
                                          '"-a HDF5 -c $RESOURCE_SPECIFIC_OPTION_N_to_1"',
                                          '"-a HDF5 -F $RESOURCE_SPECIFIC_OPTION_N_to_N"'])
    if params['testNetCDF']:tests.extend(['"-a NCMPI $RESOURCE_SPECIFIC_OPTION_N_to_1"',
                                          '"-a NCMPI -c $RESOURCE_SPECIFIC_OPTION_N_to_1"'])
    params['iorTestsList']='('+"\n".join(tests)+')'
    
    if params['akrrNNodes']==1 and params['requestTwoNodesForOneNodeAppKer']==1:
        #doAllWritesFirst
        if params['doAllWritesFirst']==True:
            params['runIORTests']=params['runIORTestsAllWritesFirstOneNode']
        else:
            params['runIORTests']=params['runIORTestsWriteReadCyclicOneNode']
    else:
        #akrrNNodes>1
        #doAllWritesFirst
        if params['doAllWritesFirst']==True:
            params['runIORTests']=params['runIORTestsAllWritesFirst']
        else:
            params['runIORTests']=params['runIORTestsWriteReadCyclic']
    

    


