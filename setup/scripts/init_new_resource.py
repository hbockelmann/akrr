"""
Python script for retrieving the 'resource' information from XDMoD and pre-generating
the default resource templates.
"""

###############################################################################
# IMPORTS
###############################################################################
import inspect
import sys
import os
import getpass
import cStringIO
import traceback
import re
#modify python_path so that we can get /src on the path
curdir=os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if (curdir+"/../../src") not in sys.path:
    sys.path.append(curdir+"/../../src")

import akrr
import util.logging as logging
import resource_validation_and_deployment

try:
    import argparse
except:
    #add argparse directory to path and try again
    curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    argparsedir=os.path.abspath(os.path.join(curdir,"..","..","3rd_party","argparse-1.3.0"))
    if argparsedir not in sys.path:sys.path.append(argparsedir)
    import argparse

# Attempt to import MySQL, if it's not there then we'll exit out and notify the
# user blow
try:
    import MySQLdb

    mysql_available = True
except ImportError:
    mysql_available = False

###############################################################################
# VARIABLES
###############################################################################

# global variable to hold the script arguments
args = None

config_dir = os.path.join(curdir, '../../cfg/')

resources_dir = os.path.join(config_dir, 'resources/')

resourceName=None

rsh=None
#variables for template with defalt values
info = None
ppn = None
remoteAccessNode = None
remoteAccessMethod = 'ssh'
remoteCopyMethod='scp'
sshUserName = None
sshPassword = None
sshPassword4thisSession = None
sshPrivateKeyFile = None#'/home/mikola/.ssh/id_rsa_test'
sshPrivateKeyPassword=None

networkScratch=None
localScratch="/tmp"
akrrData=None
appKerDir=None
batchScheduler = None
batchJobHeaderTemplate=None

resource_cfg_filename=None

def open_file(file_path, privs):
    """
    Open and return the file handle to the file identified by the provided 'file_path' with the provided 'privs'.
    If an error occurs during the opening of the file then it will be logged and 'None' will be returned.

    :type file_path str
    :type privs str

    :param file_path: the path to be opened.
    :param privs: the privs with which to open the provided file path.
    :return: a file handle ( object ) if the open operation is successful else None.
    """
    if file_path and isinstance(file_path, basestring) and privs and isinstance(privs, basestring):

        # ADD: Some verbosity
        if args.verbose:
            logging.info("Opening with privs [{0}]: {1}", privs, file_path)

        try:

            # ATTEMPT: to open the file identified by the provided file_path
            file_handle = open(file_path, privs)

            # LET: the verbose users know we succeeded
            if args.verbose:
                logging.info('Successfully preformed open [{0}] on {1}', privs, file_path)

            # RETURN: the file_handle
            return file_handle
        except IOError, e:
            logging.error('Unable to open file: {0} due to {1}: {2}', file_path, e.args[0], e.args[1])
            return None

    # IF: we've reached this point than one of the parameters was incorrect.
    logging.warning('Error 62: Internal error. Please contact support.')
    return None


def read_from_file(file_handle):
    """
    Read the contents from the provided file_handle and return them. If there is an error then a message detailing the
    problem will be written to stdout and None will be returned.

    :type file_handle file

    :param file_handle: the file object to read from.
    :return: the contents of the file or, if an error is encountered, None.
    """
    if file_handle and isinstance(file_handle, file):

        # ADDING: verbose logging before the operation.
        if args.verbose:
            logging.info('Attempting to read in contents of {0}', file_handle.name)

        try:

            # ATTEMPT: to read the contents of the file.
            contents = file_handle.read()

            # PROVIDE: the user some verbose success logging.
            if args.verbose:
                logging.info('Successfully read the contents of {0}', file_handle.name)

            # RETURN: the contents of the file.
            return contents
        except IOError, e:
            logging.error('There was a problem reading from {0}. {1}: {2}', file_handle.name, e.args[0], e.args[1])
            return None

    #IF: we've reached this point than the file_handle that was passed in isn't valid.
    logging.warning('Error 93: Internal error. Please contact support.')
    return None


def write_to_file(file_handle, lines):
    """
    Write the provided lines to the provided file_handle. If an error occurs an error message will be logged to stdout.

    :type lines: list
    :type file_handle: file

    :param file_handle: the file that the provided lines should be written
    :param lines: the lines that should be written to the provided file.
    :return: void
    """
    if not file_handle or not isinstance(file_handle, file):
        logging.error('Received an invalid file reference.')
        return
    if lines:
        try:
            if args.verbose:
                logging.info("Writing {0} lines to {1}", len(lines), file_handle.name)

            file_handle.writelines(lines)

            if args.verbose:
                logging.info("Successfully wrote {0} lines to {1}", len(lines), file_handle.name)

        except IOError, e:
            logging.error('There was an error while writing to {0}. {1}: {2}', file_handle.name, e.args[0], e.args[1])


def close_file(file_handle):
    """
    Close the provided file_handle. If an error is encountered than a message will be logged to stdout.

    :type file_handle file

    :param file_handle: the file to be closed.
    :return: void
    """
    if file_handle and isinstance(file_handle, file):
        try:
            if args.verbose:
                logging.info('Attempting to close the file {0}', file_handle.name)

            file_handle.close()

            if args.verbose:
                logging.info('Successfully closed the file {0}', file_handle.name)
        except IOError, e:
            logging.error('There was an error encountered while closing {0}. {1}: {2}', file_handle.name, e.args[0], e.args[1])


###############################################################################
# SCRIPT FUNCTIONS
###############################################################################

def retrieve_resources():
    """
    Retrieve the applicable contents of the `modw`.`resourcefact` table.
    :return: a tuple of strings containing the name of the resources.
    """
    try:
        connection, cursor = akrr.getXDDB()

        # PROVIDES: automatic resource cleanup
        with connection:
            cursor = connection.cursor()
            cursor.execute("SELECT `name`,`id` FROM `modw`.`resourcefact`")
            rows = cursor.fetchall()
    except MySQLdb.Error, e:
        logging.error("MySQL Error: {0}: {1}", e.args[0]. e.args[1])
        sys.exit(1)

    # PROVIDE: a little bit of verbosity to the masses.
    if args.verbose:
        logging.info("Retrieved {0} Resource records...", len(rows) if rows else 0)

    return rows


def retrieve_queue_template(file_path, queue):
    """
    Retrieve the resource per queue type template and return it's contents.

    :type file_path str
    :type queue str

    :param file_path: the path to the template whose contents will be returned.
    :param queue: the queue type that will be used to look up the template.
    :return: the contents of the template or, if there is an exception, None.
    """
    if file_path and isinstance(file_path, basestring) and queue and isinstance(queue, basestring):
        privs = 'r'
        template_path = file_path.format(queue)
        return read_from_file(open_file(template_path, privs))


def create_resource_template(file_path, queue, contents):
    """

    :type file_path str
    :type queue str

    :param file_path:
    :param queue:
    :param contents:
    :return:
    """

    privs = 'w'
    output_path = file_path.format(queue)
    
    def update_template(s,variable,inQuotes=True):
        rexp='^'+variable+'\s*=\s*.*$'
        replace=variable+' = '
        value=globals()[variable]
        if value==None:
            replace+='None'
        else:
            if inQuotes:replace+='"'
            replace+=str(value)
            if inQuotes:replace+='"'
        out=[]
        lines=s.splitlines()
        for line in lines:
            out.append(re.sub(rexp,replace,line))
        #s=re.sub(rexp,replace,s,flags=re.M)
        
        return "\n".join(out)
    
    contents=update_template(contents,'ppn',inQuotes=False)
    for v in ['remoteAccessNode','remoteAccessMethod','remoteCopyMethod',
              'sshUserName','sshPassword','sshPrivateKeyFile','sshPrivateKeyPassword',
              'networkScratch','localScratch','akrrData','appKerDir','batchScheduler']:
              contents=update_template(contents,v)
    contents+="\n\n"
    
    #contents=re.sub(r'^ppn\s*=\s*.*$','ppn = %d'%ppn,contents,flags=re.M)
    #contents=re.sub(r'^remoteAccessNode\s*=\s*.*$','remoteAccessNode = "%s"'%remoteAccessNode,contents,flags=re.M)
    #contents=re.sub(r'^remoteAccessMethod\s*=\s*.*$','remoteAccessMethod = "%s"'%remoteAccessNode,contents,flags=re.M)
#     if 
    
    



    if not args.test:
        output_file = open_file(output_path, privs)
        write_to_file(output_file, contents)
        close_file(output_file)
    else:
        logging.info('Test Mode: Would have written to: {0}', output_path)
        logging.info('It content would be:')
        print contents


def generate_default_templates(resources):
    """
    Create the default templates per resource that was retrieved from the `modw`.`resourcefact` table.

    :param resources: a tuple of (string,int) [name, id] retrieved from the `modw`.`resourcefact` table.
    :return: void
    """

    if not resources:
        logging.warning("No resources found. No files to create.")
    else:

        slurm_template_contents = retrieve_queue_template(os.path.join(akrr.curdir, 'templates','template.{0}.inp.py'), 'slurm')
        pbs_template_contents = retrieve_queue_template(os.path.join(akrr.curdir, 'templates', 'template.{0}.inp.py'), 'pbs')

        queues = {'slurm': slurm_template_contents, 'pbs': pbs_template_contents}

        for resource in resources:
            if args.verbose:
                logging.info("Creating Resource Template: {0} ", resource[0] + "")

            if not args.test:
                for queue, contents in queues.iteritems():

                    file_path = os.path.join(resources_dir, resource[0] + 'resource.inp.py')

                    create_resource_template(file_path, queue, contents)

        logging.info("Resource Template Generation Complete!")

def generate_resource_config(resource_id, resource_name, queuing_system):
    logging.info("Initiating %s at AKRR"%(resource_name,))
    
    slurm_template_contents = retrieve_queue_template(os.path.join(akrr.curdir, 'templates', 'template.{0}.inp.py'), 'slurm')
    pbs_template_contents = retrieve_queue_template(os.path.join(akrr.curdir, 'templates', 'template.{0}.inp.py'), 'pbs')

    queues = {'slurm': slurm_template_contents, 'pbs': pbs_template_contents}
    

    if not args.test:
        os.mkdir(os.path.join(resources_dir, resource_name),0700)
    
    file_path = os.path.abspath(os.path.join(resources_dir, resource_name, 'resource.inp.py'))
    global resource_cfg_filename
    resource_cfg_filename=file_path
    
    create_resource_template(file_path, queues[queuing_system], queues[queuing_system])
        
    if not args.test:    
        #add entry to mod_appkernel.resource
        dbAK,curAK=akrr.getAKDB(True)
            
        curAK.execute('''SELECT * FROM resource WHERE nickname=%s''', (resource_name,))
        resource_in_AKDB = curAK.fetchall()
        if len(resource_in_AKDB)==0:
            curAK.execute('''INSERT INTO resource (resource,nickname,description,enabled,visible,xdmod_resource_id)
                        VALUES(%s,%s,%s,0,0,%s);''',
                        (resource_name,resource_name,resource_name,resource_id))
            dbAK.commit()
        curAK.execute('''SELECT * FROM resource WHERE nickname=%s''', (resource_name,))
        resource_in_AKDB = curAK.fetchall()
        resource_id_in_AKDB=resource_in_AKDB[0]['resource_id']
        #add entry to mod_akrr.resource
        db,cur=akrr.getDB(True)
            
        cur.execute('''SELECT * FROM resources WHERE name=%s''', (resource_name,))
        resource_in_DB = cur.fetchall()
        if len(resource_in_DB)==0:
            cur.execute('''INSERT INTO resources (id,xdmod_resource_id,name,enabled)
                        VALUES(%s,%s,%s,%s);''',
                        (resource_id_in_AKDB,resource_id,resource_name,0))
            db.commit()

            logging.info("Resource configuration is in "+file_path)

def validate_resource_id(resource_id,resources):
    try:
        resource_id=long(resource_id)
    except:
        return False
    for resource_name,resource_id2 in resources:
        if int(resource_id2)==int(resource_id):
            return True
    if resource_id==0:
        return True
    return False

def validate_resource_name(resource_name):
    if resource_name.strip()=="":
        logging.error("Bad name for resource, try a different name")
        return False
    #check config file presence
    file_path = os.path.abspath(os.path.join(resources_dir, resource_name))
    if os.path.exists(file_path):
        logging.error("Resource configuration directory (%s) for resource with name %s already present on file system, try a different name"%(file_path,resource_name,))
        return False
    
    
    #check the entry in mod_appkernel
    dbAK,curAK=akrr.getAKDB(True)
        
    curAK.execute('''SELECT * FROM resource WHERE nickname=%s''', (resource_name,))
    resource_in_AKDB = curAK.fetchall()
    if len(resource_in_AKDB)!=0:
        logging.error("Resource with name %s already present in mod_appkernel DB, try a different name"%(resource_name,))
        return False
    
    #check the entry in mod_akrr
    db,cur=akrr.getDB(True)
        
    cur.execute('''SELECT * FROM resources WHERE name=%s''', (resource_name,))
    resource_in_DB = cur.fetchall()
    if len(resource_in_DB)!=0:
        logging.error("Resource with name %s already present in mod_akrr DB, try a different name"%(resource_name,))
        return False
    
    return True

def get_resourcename_by_id(resource_id,resources):
    try:
        resource_id=long(resource_id)
    except:
        return False
    for resource_name,resource_id2 in resources:
        if int(resource_id2)==int(resource_id):
            return resource_name
    return None
def validate_queuing_system(queuing_system):
    if queuing_system in ['slurm', 'pbs']:
        return True
    else:
        return False
def checkConnectionToResource():
    successfullyConnected=False
    global remoteAccessNode
    global remoteAccessMethod
    global remoteCopyMethod
    global sshUserName
    global sshPassword
    global sshPassword4thisSession
    global sshPrivateKeyFile
    global sshPrivateKeyPassword
    passphraseEntranceCount=0
    authorizeKeyCount=0
    while True:
        str_io=cStringIO.StringIO()
        try:
            sys.stdout = sys.stderr = str_io
            akrr.sshAccess(remoteAccessNode, ssh=remoteAccessMethod, username=sshUserName, password=sshPassword,
                    PrivateKeyFile=sshPrivateKeyFile, PrivateKeyPassword=sshPrivateKeyPassword, logfile=str_io,
                    command='ls')
            
            sys.stdout=sys.__stdout__
            sys.stderr=sys.__stderr__
            
            successfullyConnected=True
            break
        except Exception,e:
            sys.stdout=sys.__stdout__
            sys.stderr=sys.__stderr__
            if args.verbose:
                logging.info("Had attempted to access resource without password and failed, below is resource response")
                print "="*80
                print str_io.getvalue()
                print traceback.format_exc()
                print "="*80
            #check if it asking for passphrase
            m=re.search(r"Enter passphrase for key '(.*)':",str_io.getvalue())
            if m:
                if passphraseEntranceCount>=3:
                    sshPrivateKeyPassword=None
                    sshPrivateKeyFile=None
                    break
                if passphraseEntranceCount>0:
                    logging.error("Incorrect passphrase try again")
                sshPrivateKeyFile=m.group(1)
                logging.input("Enter passphrase for key '%s':"%sshPrivateKeyFile)
                sshPrivateKeyPassword=getpass.getpass("")
                passphraseEntranceCount+=1
                continue
            m2=re.search(r"[pP]assword:",str_io.getvalue())
            if m==None and sshPrivateKeyFile!=None and m2:
                logging.warning("Can not login to head node. Probably the public key of private key was not authorized on head node")
                print "Will try to add public key to list of authorized keys on head node"
                while True:
                    try:
                        authorizeKeyCount+=1
                        logging.input("Enter password for %s@%s (will be used only during this session):"%(sshUserName,remoteAccessNode))
                        sshPassword4thisSession=getpass.getpass("")
                        print
                        str_io=cStringIO.StringIO()
                        sys.stdout = sys.stderr = str_io
                        akrr.sshAccess(remoteAccessNode, ssh='ssh-copy-id', username=sshUserName, password=sshPassword4thisSession,
                            PrivateKeyFile=sshPrivateKeyFile, PrivateKeyPassword=None, logfile=str_io,
                            command='')
                    
                        sys.stdout=sys.__stdout__
                        sys.stderr=sys.__stderr__
                        print str_io.getvalue()
                        #successfullyConnected=True
                        logging.info("Have added public key to list of authorized keys on head node, will attempt to connect again.")
                        print
                        break
                    except Exception,e:
                        sys.stdout=sys.__stdout__
                        sys.stderr=sys.__stderr__
                        if args.verbose:
                            logging.info("Had attempted to add public key to list of authorized keys on head node and failed, below is resource response")
                            print "="*80
                            print str_io.getvalue()
                            print traceback.format_exc()
                            print "="*80
                        logging.info("Incorrect password try again.")
                        if authorizeKeyCount>=3:
                            break
                if authorizeKeyCount<3:
                     continue       
            break
    return successfullyConnected
def getRemoteAccessMethod():
    global remoteAccessNode
    global remoteAccessMethod
    global remoteCopyMethod
    global sshUserName
    global sshPassword
    global sshPassword4thisSession
    global sshPrivateKeyFile
    global sshPrivateKeyPassword
    global rsh
    #set remoteAccessNode
    while True:
        logging.input("Enter Resource head node (access node) full name (e.g. headnode.somewhere.org):")
        remoteAccessNode=raw_input("[%s] "%resourceName)
        if remoteAccessNode.strip()=="":
            remoteAccessNode=resourceName
        
        response = os.system("ping -c 1 -w2 " + remoteAccessNode + " > /dev/null 2>&1")
        
        if response==0:
            break
        else:
            logging.error("Incorrect head node name (can not ping %s), try again"%remoteAccessNode)
    #set sshUserName
    curentuser=getpass.getuser()
    askForUserName=True
    successfullyConnected=False
    while True:
        if askForUserName:
            logging.input("Enter username for resource access:")
            sshUserName=raw_input("[%s] "%curentuser)
            if sshUserName.strip()=="":
                sshUserName=curentuser
            curentuser=sshUserName
        
        #check passwordless access
        if sshPassword==None:
            logging.info("Checking for password-less access")
        else:
            logging.info("Checking for resource access")
        successfullyConnected=checkConnectionToResource()
        if successfullyConnected:
            if sshPassword==None:
                logging.info("Can access resource without password")
            else:
                logging.info("Can access resource")
        
        if successfullyConnected==False:
            logging.info("Can not access resource without password")
            actionList=[]
            actionList.append(["TryAgain","The private and public keys was generated manually, right now. Try again."])
            #check private keys
            userHomeDir = os.path.expanduser("~")
            privateKeys = [ os.path.join(userHomeDir,'.ssh',f[:-4]) for f in os.listdir(os.path.join(userHomeDir,'.ssh')) if os.path.isfile(os.path.join(userHomeDir,'.ssh',f)) \
                       and f[-4:]=='.pub' and os.path.isfile(os.path.join(userHomeDir,'.ssh',f[:-4]))]
            if len(privateKeys)>0:
                actionList.append(["UseExistingPrivateKey","Use existing private and public key."])
            
            actionList.append(["GenNewKey","Generate new private and public key."])
            actionList.append(["UsePassword","Use password directly."])
            
            print
            print "Select authentication method:"
            for i in range(len(actionList)):
                print "%3d  %s"%(i,actionList[i][1])
            while True:
                logging.input("Select option from list above:")
                try:
                    action=raw_input("[2] ")
                    if action.strip()=="":action=2
                    else: action=int(action)
                    
                    if action<0 or action>=len(actionList):
                        raise
                    break
                except Exception,e:
                    logging.error("Incorrect entry, try again.")
            
            #do the action
            print
            if actionList[action][0]=="TryAgain":
                continue
            if actionList[action][0]=="UsePassword":
                logging.input("Enter password for %s@%s:"%(sshUserName,remoteAccessNode))
                sshPassword=getpass.getpass("")
                askForUserName=not askForUserName
                continue
            if actionList[action][0]=="UseExistingPrivateKey":
                print "Available private keys:"
                for i in range(len(privateKeys)):
                    print "%3d  %s"%(i,privateKeys[i])
                while True:
                    logging.input("Select key number from list above:")
                    try:
                        iKey=raw_input("")
                        iKey=int(iKey)
                        
                        if iKey<0 or iKey>=len(privateKeys):
                            raise
                        break
                    except Exception,e:
                        logging.error("Incorrect entry, try again.")
                sshPrivateKeyFile=privateKeys[iKey]
                askForUserName=not askForUserName
                continue
            if actionList[action][0]=="GenNewKey":
                count=0
                while True:
                    logging.input("Enter password for %s@%s (will be used only during this session):"%(sshUserName,remoteAccessNode))
                    sshPassword4thisSession=getpass.getpass("")
                    sshPassword=sshPassword4thisSession
                    
                    if checkConnectionToResource():
                        break
                    count+=1
                    if count>=3:
                        break
                sshPassword=None
                #generate keys
                logging.input("Enter private key name:")
                sshPrivateKeyFile=raw_input("[id_rsa_%s]"%resourceName)
                if sshPrivateKeyFile.strip()=="":
                    sshPrivateKeyFile="id_rsa_%s"%resourceName
                sshPrivateKeyFile=os.path.join(userHomeDir,'.ssh',sshPrivateKeyFile)
                logging.input("Enter passphrase for new key (leave empty for passwordless access):")
                sshPrivateKeyPassword=getpass.getpass("")
                os.system("ssh-keygen -t rsa -N \"%s\" -f %s"%(sshPrivateKeyPassword,sshPrivateKeyFile))
                if sshPrivateKeyPassword.strip()=="":
                    sshPrivateKeyPassword=None
                #copy keys
                akrr.sshAccess(remoteAccessNode, ssh='ssh-copy-id', username=sshUserName, password=sshPassword4thisSession,
                            PrivateKeyFile=sshPrivateKeyFile, PrivateKeyPassword=None, logfile=sys.stdout,
                            command='')
                askForUserName=not askForUserName
                continue
        
        if successfullyConnected:
            break
        else:
            logging.error("Incorrect resource access credential")
    if successfullyConnected:
        print
        logging.info("Connecting to "+resourceName)
        
        str_io=cStringIO.StringIO()
        sys.stdout = sys.stderr = str_io
        rsh=akrr.sshAccess(remoteAccessNode, ssh=remoteAccessMethod, username=sshUserName, password=sshPassword,
                    PrivateKeyFile=sshPrivateKeyFile, PrivateKeyPassword=sshPrivateKeyPassword, logfile=sys.stdout,
                    command=None)
        sys.stdout=sys.__stdout__
        sys.stderr=sys.__stderr__
        
        logging.info("              Done")
    print
    return successfullyConnected
def getSytemCharacteristics():
    global ppn
    while True:   
        try:                 
            logging.input("Enter processors (cores) per node count:")
            ppn=int(raw_input(""))
            break
        except Exception,e:
            logging.error("Incorrect entry, try again.")
    
def getFileSytemAccessPoints():
    global networkScratch
    global localScratch
    global akrrData
    global appKerDir
    
    homeDir=akrr.sshCommand(rsh,"echo $HOME").strip()
    scratchNetworkDir=akrr.sshCommand(rsh,"echo $SCRATCH").strip()
    
    #localScratch
    localScratchDefault="/tmp"
    while True:                    
        logging.input("Enter location of local scratch (visible only to single node):")
        localScratch=raw_input("[%s]"%localScratchDefault)
        if localScratch.strip()=="":
            localScratch=localScratchDefault
        status,msg=resource_validation_and_deployment.CheckDirSimple(rsh, localScratch)
        if status:
            logging.info(msg)
            print
            break
        else:
            logging.warning(msg)
            logging.warning('local scratch might be have a different location on head node, so if it is by design it is ok')
            print
            break
    localScratch=akrr.sshCommand(rsh,"echo %s"%(localScratch,)).strip()
    #networkScratch
    networkScratchDefault=""
    if scratchNetworkDir!="":
        networkScratchDefault=scratchNetworkDir
    networkScratchVisible=False
    while True:                    
        logging.input("Enter location of network scratch (visible only to all nodes), used for temporary storage of app kernel input/output:")
        if networkScratchDefault!="":
            networkScratch=raw_input("[%s]"%networkScratchDefault)
            if networkScratch.strip()=="":
                networkScratch=networkScratchDefault
        else:
            networkScratch=raw_input("")
            
        if networkScratch=="":
            logging.error("Incorrect value for networkScratch, try again")
            continue
        
        
        status,msg=resource_validation_and_deployment.CheckDir(rsh, networkScratch,exitOnFail=False,tryToCreate=True)
        if status:
            logging.info(msg)
            networkScratchVisible=True
            print
            break
        else:
            logging.warning(msg)
            #logging.warning('network scratch might be have a different location on head node, so if it is by design it is ok')
            #print
            break
    networkScratch=akrr.sshCommand(rsh,"echo %s"%(networkScratch,)).strip()
    #appKerDir
    appKerDirDefault=os.path.join(homeDir,"appker",resourceName)   
    while True:                    
        logging.input("Enter future location of app kernels input and executable files:")
        appKerDir=raw_input("[%s]"%appKerDirDefault)
        if appKerDir.strip()=="":
            appKerDir=appKerDirDefault
        status,msg=resource_validation_and_deployment.CheckDir(rsh, appKerDir,exitOnFail=False,tryToCreate=True)
        if status:
            logging.info(msg)
            print
            break
        else:
            logging.error(msg)
    appKerDir=akrr.sshCommand(rsh,"echo %s"%(appKerDir,)).strip()
    #akrrData
    akrrDataDefault=os.path.join(homeDir,"akrrdata",resourceName)
    if networkScratchVisible:
        akrrDataDefault=os.path.join(networkScratch,"akrrdata",resourceName)
    while True:                    
        logging.input("Enter future locations for app kernels working directories (can or even should be on scratch space):")
        akrrData=raw_input("[%s]"%akrrDataDefault)
        if akrrData.strip()=="":
            akrrData=akrrDataDefault
        status,msg=resource_validation_and_deployment.CheckDir(rsh, akrrData,exitOnFail=False,tryToCreate=True)
        if status:
            logging.info(msg)
            print
            break
        else:
            logging.error(msg) 
    akrrData=akrr.sshCommand(rsh,"echo %s"%(akrrData,)).strip()
    #remoteAccessMethod = 'ssh'
    #remoteCopyMethod='scp'
    #sshPassword = None
    #sshPrivateKeyFile = None
    #sshPrivateKeyPassword=None
###############################################################################
# SCRIPT ENTRY POINT
###############################################################################
if __name__ == '__main__':
    #global batchScheduler
    logging.info("Beginning Initiation of New Resource...")
    # CHECK: To see if we were able to import MySQLdb
    if not mysql_available:
        logging.error("Unable to find MySQLdb. Please install this python library before re-running .")
        exit(1)

    # TIME: to get to parsing
    parser = argparse.ArgumentParser()

    # SETUP: the arguments that we're going to support
    parser.add_argument('-v', '--verbose', action='store_true', help="turn on verbose logging")
    parser.add_argument('-t', '--test', action='store_true', help="No files will actually be created, only their names will be outputed to the console.")
    parser.add_argument('-m', '--minimalistic', action='store_true', help="Minimize questions number, configuration files will be edited manually")

    # PARSE: them arguments
    args = parser.parse_args()

    logging.info("Retrieving Resources from XDMoD Database...")
    # RETRIEVE: the resources from XDMoD
    resources = retrieve_resources()
    print
    print "Found following resources from XDMoD Database:"
    print
    print "resource_id  name"
    for resource_name,resource_id in resources:
        print "%11d  %-40s"%(resource_id,resource_name)
    print
    
    while True:
        logging.input('Enter resource_id for import (enter 0 for no match):')
        resource_id=raw_input()
        if validate_resource_id(resource_id,resources):
            break
        print "Incorrect resource_id try again"
    print
    resource_id=int(resource_id)
    if resource_id<=0:#i.e. no match from XDMoD DB
        resource_id=None
    
    resource_name=""
    while True:
        if resource_id==None:
            logging.input('Enter AKRR resource name:')
            resource_name=raw_input()
        else:
            resource_name2=get_resourcename_by_id(resource_id,resources)
            logging.input('Enter AKRR resource name, hit enter to use same name as in XDMoD Database [%s]:'%(resource_name2,))
            resource_name=raw_input()
            if resource_name.strip()=="":
                resource_name=resource_name2
        
        if validate_resource_name(resource_name)==True:
            break
    resourceName=resource_name
    print       
    
    logging.input('Enter queuing system on resource (slurm or pbs): ')
    queuing_system=raw_input()
    while not validate_queuing_system(queuing_system):
        logging.error("Incorrect queuing_system try again")
        logging.input('Enter queuing system on resource (slurm or pbs): ')
        queuing_system=raw_input()
    batchScheduler=queuing_system
    print
    
    if args.minimalistic==False:
        getRemoteAccessMethod()
        getSytemCharacteristics()
        getFileSytemAccessPoints()
    
    if args.verbose:
        logging.info("summary of parameters")
        print "remoteAccessNode",remoteAccessNode
        print "remoteAccessMethod",remoteAccessMethod
        print "remoteCopyMethod",remoteCopyMethod
        print "sshUserName",sshUserName
        print "sshPassword",sshPassword
        print "sshPrivateKeyFile",sshPrivateKeyFile
        print "sshPrivateKeyPassword",sshPrivateKeyPassword
        print "networkScratch",networkScratch
        print "localScratch",localScratch
        print "akrrData",akrrData
        print "appKerDir",appKerDir
        print "batchScheduler",batchScheduler
        print "batchJobHeaderTemplate",batchJobHeaderTemplate
        print
        
    generate_resource_config(resource_id, resource_name, queuing_system)
    logging.info('Initiation of new resource is completed.')
    logging.info('    Edit batchJobHeaderTemplate variable in '+resource_cfg_filename)
    logging.info('    and move to resource validation and deployment step.')
    print
    print "Execute following command to setup environment variable for future setup convenience:"
    print "export RESOURCE=%s"%(resource_name,)
    print
    # GENERATE: the
    #generate_default_templates(resources)



