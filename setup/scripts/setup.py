import sys
import datetime
import time
import inspect
import os
import re
import traceback
import types
import shutil
import getpass
import subprocess
import os
import random
import string

try:
    import argparse
except:
    #add argparse directory to path and try again
    curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    argparsedir=os.path.abspath(os.path.join(curdir,"..","..","3rd_party","argparse-1.3.0"))
    if argparsedir not in sys.path:sys.path.append(argparsedir)
    import argparse

# modify python_path so that we can get /src on the path
curdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if (curdir + "/../../src") not in sys.path:
    sys.path.append(curdir + "/../../src")

akrr_home=os.path.abspath(curdir + "/../../")


#add check_output fuction to subprocess module if python is old
if "check_output" not in dir( subprocess ): # duck punch it in!
    def f(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output
    subprocess.check_output = f


from util import logging as log

try:
    import MySQLdb
    import MySQLdb.cursors
except Exception,e:
    log.error("""python module MySQLdb is not available. Install it!
    For example by running on Ubuntu:
         sudo apt-get install python2.7-mysqldb""")
    exit(1)



class InstallAKRR:
    default_akrr_user='akrruser'
    def __init__(self):
        self.akrr_user_name=None
        self.akrr_user_password=None
        self.xd_user_name=None
        self.xd_user_password=None
        self.sql_root_name=None
        self.sql_root_password=None
        self.cronemail=None
    def check_previous_installation(self):
        if(os.path.exists(os.path.join(akrr_home,"cfg","akrr.inp.py"))):
            msg="This is a fresh installation script. "+akrr_home+\
                     " contains previous AKRR installation. Either uninstall it or see documentation on updates.\n\n";
            msg+="To uninstall AKRR manually:\n\t1)remove $AKRR_HOME/cfg/akrr.inp.py\n\t\trm $AKRR_HOME/cfg/akrr.inp.py\n"
            msg+="\t2) (optionally for totally fresh start) drop mod_akrr and mod_appkernel database\n"
            msg+="\t\tDROP DATABASE mod_appkernel;\n"
            msg+="\t\tDROP DATABASE mod_akrr;\n\n"
            
            log.error(msg)
            exit(1)
        
    def read_akrr_creds(self):
        log.info("Before Installation continues we need to setup the database.")

        log.input("Please specify a database user for AKRR (This user will be created if it does not already exist):")
        self.akrr_user_name=raw_input('[{0}] '.format(self.default_akrr_user)) 
        if self.akrr_user_name=='':self.akrr_user_name=self.default_akrr_user
        
        while True:
            log.input("Please specify a password for the AKRR database user:")
            password=getpass.getpass()
            log.input("Please reenter password:")
            password2=getpass.getpass()
            if password==password2:
                self.akrr_user_password=password
                break
            log.error("Entered passwords do not match. Please try again.")
        
    def read_modw_creds(self):
        log.input("Please specify the user that will be connecting to the XDMoD database (modw):")
        self.xd_user_name=raw_input('[{0}] '.format(self.default_akrr_user))
        if self.xd_user_name=='':self.xd_user_name=self.default_akrr_user
        if self.xd_user_name==self.akrr_user_name:
            log.info("Same user as for AKRR database user, will set same password")
            self.xd_user_password=self.akrr_user_password
        else:
            while True:
                log.input("Please specify the password:")
                password=getpass.getpass()
                log.input("Please reenter password:")
                password2=getpass.getpass()
                if password==password2:
                    self.xd_user_password=password
                    break
                log.error("Entered passwords do not match. Please try again.")
    def get_db(dictCursor=True,user=None,password=None,host='localhost',port=3306,db_name='mysql'):
        if dictCursor:
            db = MySQLdb.connect(host=host, port=port, user=cfg.akrr_db_user if user==None else user,
                                 passwd=cfg.akrr_db_passwd if password==None else password, db=db_name,
                                 cursorclass=MySQLdb.cursors.DictCursor)
        else:
            db = MySQLdb.connect(host=host, port=port, user=cfg.akrr_db_user if user==None else user,
                                 passwd=cfg.akrr_db_passwd if password==None else password, db=db_name)
        cur = db.cursor()
        return db, cur
    def get_random_password(self):
        length = 16
        chars = string.ascii_letters + string.digits
        # + '@#$%^&*'
        password=""
        while len(password)<length:
            i=os.urandom(1)
            if ord(i)>(255/len(chars))*len(chars):
                continue
            password+=chars[ord(i)%len(chars)]
        return password
    def read_sql_root_creds(self):
        while True:
            log.input("""Please provide an administrative database user under which the installation sql script should
run (This user must have privileges to create users and databases):""")
            self.sql_root_name=raw_input()
            log.input("Please provide the password for the the user which you previously entered:")
            self.sql_root_password=getpass.getpass()
            
            try:
                self.get_db(user=self.sql_root_name,password=self.sql_root_password)
                break
            except Exception,e:
                log.error("Entered credential is not valid. Please try again.")
    def init_mysql_dbs(self):
        try:
            log.info("Creating AKRR databases and granting permissions for AKRR user.")
            
            db_root,cur_root=self.get_db(user=self.sql_root_name,password=self.sql_root_password)
            cur_root.execute("SHOW DATABASES")
            dbsNames=[v['Database'] for v in cur_root.fetchall()]
            
            cur_root.execute("SELECT @@hostname")
            results=cur_root.fetchall()
            hostname=results[0]['@@hostname']
            
            #create user if needed
            #cur_root.execute("SELECT * FROM mysql.user WHERE User=%s",(self.akrr_user_name,))
            #results=cur_root.fetchall()
            
            # ENSURE: That the `mod_akrr` database is created.
            if 'mod_akrr' not in dbsNames:
                cur_root.execute("CREATE DATABASE IF NOT EXISTS mod_akrr")
                while cur_root.nextset() is not None: pass
            # ENSURE: That the `mod_appkernel` database is created.
            if 'mod_appkernel' not in dbsNames:
                cur_root.execute("CREATE DATABASE IF NOT EXISTS mod_appkernel")
                while cur_root.nextset() is not None: pass
            # ENSURE: That the user that will be used by AKRR is created with the correct privileges.
            cur_root.execute("GRANT ALL ON mod_akrr.* TO %s@%s IDENTIFIED BY %s",(self.akrr_user_name, '%', self.akrr_user_password))
            cur_root.execute("GRANT ALL ON mod_akrr.* TO %s@%s IDENTIFIED BY %s",(self.akrr_user_name, 'localhost', self.akrr_user_password))
            cur_root.execute("GRANT ALL ON mod_akrr.* TO %s@%s IDENTIFIED BY %s",(self.akrr_user_name, hostname, self.akrr_user_password))
            
            while cur_root.nextset() is not None: pass
            # ENSURE: That the AKRR user has the correct privileges to the `mod_appkernel` database.
            cur_root.execute("GRANT ALL ON mod_appkernel.* TO %s@%s IDENTIFIED BY %s",(self.akrr_user_name, '%', self.akrr_user_password))
            cur_root.execute("GRANT ALL ON mod_appkernel.* TO %s@%s IDENTIFIED BY %s",(self.akrr_user_name, 'localhost', self.akrr_user_password))
            cur_root.execute("GRANT ALL ON mod_appkernel.* TO %s@%s IDENTIFIED BY %s",(self.akrr_user_name, hostname, self.akrr_user_password))
            
            while cur_root.nextset() is not None: pass
            # ENSURE: That the AKRR modw user is created w/ the correct privileges
            cur_root.execute("GRANT SELECT ON modw.resourcefact TO %s@%s IDENTIFIED BY %s",(self.xd_user_name, '%', self.xd_user_password))
            cur_root.execute("GRANT SELECT ON modw.resourcefact TO %s@%s IDENTIFIED BY %s",(self.xd_user_name, 'localhost', self.xd_user_password))
            cur_root.execute("GRANT SELECT ON modw.resourcefact TO %s@%s IDENTIFIED BY %s",(self.xd_user_name, hostname, self.xd_user_password))
            
            while cur_root.nextset() is not None: pass
            # ENSURE: That the newly granted privileges are flushed into active service.
            cur_root.execute("FLUSH PRIVILEGES")
            while cur_root.nextset() is not None: pass
            db_root.commit()
        except Exception,e:
            log.error("Can not execute the sql install script: "+str(e))
            exit(1)
    def generate_self_signed_certificate(self):
        log.info("Generating self-signed certificate for REST-API")
        try:
            output=subprocess.check_output("which openssl", shell=True)
        except Exception,e:
            log.error("""openssl program is not available. Install it!
    For example by running on Ubuntu:
         sudo apt-get install openssl""")
            exit(1)
        #openssl genrsa -des3 -passout pass:x -out ${__AKRR_CFG_DIR}/server.pass.key 2048
        #openssl rsa -passin pass:x -in ${__AKRR_CFG_DIR}/server.pass.key -out ${__AKRR_CFG_DIR}/server.key
        #rm ${__AKRR_CFG_DIR}/server.pass.key
        #openssl req -new -key ${__AKRR_CFG_DIR}/server.key -out ${__AKRR_CFG_DIR}/server.csr
        #openssl x509 -req -days 36500 -in ${__AKRR_CFG_DIR}/server.csr -signkey ${__AKRR_CFG_DIR}/server.key -out ${__AKRR_CFG_DIR}/server.crt
        output=subprocess.check_output("""
            openssl req \
                -new \
                -newkey rsa:4096 \
                -days 365 \
                -nodes \
                -x509 \
                -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=localhost" \
                -keyout {akrr_cfg_dir}/server.key \
                -out {akrr_cfg_dir}/server.cert
            cp {akrr_cfg_dir}/server.key {akrr_cfg_dir}/server.pem
            cat {akrr_cfg_dir}/server.cert >> {akrr_cfg_dir}/server.pem
            """.format(akrr_cfg_dir=os.path.join(akrr_home,'cfg')), shell=True)
        print output
        log.info("New self-signed certificate have been generated")

    def generate_settings_file(self):
        log.info("Generating Settings File...")
        with open(os.path.join(akrr_home,'setup','scripts','akrr.src.inp.py'),'r') as f:
            akrr_inp_template=f.read()
        restapi_rw_password=self.get_random_password()
        restapi_ro_password=self.get_random_password()
        var={
            'akrr_user_name':self.akrr_user_name,
            'akrr_user_password':self.akrr_user_password,
            'xd_user_name':self.xd_user_name,
            'xd_user_password':self.xd_user_password,
            'restapi_rw_password':restapi_rw_password,
            'restapi_ro_password':restapi_ro_password
        }
        akrr_inp=akrr_inp_template.format(**var)
        with open(os.path.join(akrr_home,'cfg','akrr.inp.py'),'w') as f:
            akrr_inp_template=f.write(akrr_inp)
        log.info("Settings written to: {0}".format(os.path.join(akrr_home,'cfg','akrr.inp.py')))
    def set_permission_on_files(self):
        log.info("Removing access for group members and everybody for all files as it might contain sensitive information.")
        output=subprocess.check_output("""
            chmod -R g-rwx {akrr_home}
            chmod -R o-rwx {akrr_home}
            """.format(akrr_home=akrr_home), shell=True)
    def db_check(self):
        import akrrdb_check
        akrrdb_check.akrrdb_check()
    def generate_tables(self):
        import akrrgenerate_tables
        akrrgenerate_tables.args = type("Args", (object,), {})()
        akrrgenerate_tables.args.verbose=True
        akrrgenerate_tables.args.test=False
        akrrgenerate_tables.args.host=None
        akrrgenerate_tables.args.user=None
        akrrgenerate_tables.args.password=None
        akrrgenerate_tables.args.db=None
        # SETUP: the mod_akrr database tables
        akrrgenerate_tables.setup_mod_akrr()
    
        # SETUP: the mod_app_kernel tables
        akrrgenerate_tables.setup_mod_appkernel()
    def start_daemon(self):
        """Start the daemon"""
        daemon_script=os.path.join(akrr_home,'src','akrrscheduler.py')
        status=subprocess.call(sys.executable+" "+daemon_script+" start", shell=True)
        if status!=0:exit(status)
    def check_daemon(self):
        """Check that the daemon is running"""
        check_daemon=os.path.join(akrr_home,'setup','scripts','akrrcheck_daemon.py')
        status=subprocess.call(sys.executable+" "+check_daemon, shell=True)
        if status!=0:exit(status)
    
    def ask_cron_email(self):
        """ask_cron_email."""
        try:
            crontanContent=subprocess.check_output("crontab -l", shell=True)
            crontanContent=crontanContent.splitlines(True)
        except:
            #probably no crontab was setup yet
            crontanContent=[]
        for l in crontanContent:
            if len(l.strip())>1 and l.strip()[0]!="#":
                m=re.match(r'^MAILTO\s*=\s*(.*)',l.strip())
                if m:
                    self.cronemail=m.group(1)
                    self.cronemail=self.cronemail.replace('"','')
        if self.cronemail==None:
            log.input("Please enter the e-mail where cron will send messages (leave empty to opt out):")
            self.cronemail=raw_input()
        else:
            log.input("Please enter the e-mail where cron will send messages:")
            cronemail=raw_input('[{0}] '.format(self.cronemail)) 
            if cronemail!="":self.cronemail=cronemail
        if self.cronemail=="":self.cronemail=None
    def install_cron_scripts(self):
        """Install cron scripts."""
        if self.cronemail:mail="MAILTO = "+self.cronemail
        else: mail=None
        restart="50 23 * * * "+akrr_home+"/bin/restart.sh"
        checknrestart="33 * * * * "+akrr_home+"/bin/checknrestart.sh"
        
        try:
            crontanContent=subprocess.check_output("crontab -l", shell=True)
            crontanContent=crontanContent.splitlines(True)
        except:
            log.info("Crontab does not have user's crontab yet")
            crontanContent=[]
        
        mailUpdated=False
        mailThere=False
        restartThere=False
        checknrestartThere=False
        
        for i in range(len(crontanContent)):
            l=crontanContent[i]
            if len(l.strip())>1 and l.strip()[0]!="#":
                m=re.match(r'^MAILTO\s*=\s*(.*)',l.strip())
                if m:
                    cronemail=m.group(1)
                    cronemail=self.cronemail.replace('"','')
                    mailThere=True
                    if self.cronemail!=cronemail:
                        if mail:
                            crontanContent[i]=mail
                        else:
                            crontanContent[i]="#"+crontanContent[i]
                        mailUpdated=True
                if l.count("restart.sh")>0:
                    restartThere=True
                if l.count("checknrestart.sh")>0:
                    checknrestartThere=True
        if mailUpdated:
            log.info("Cron's MAILTO was updated")
        if ((self.cronemail!=None and mailThere) or (self.cronemail==None and mailThere==False)) and restartThere and checknrestartThere and mailUpdated==False:
            log.warning("All entries found. No modifications necessary.")
            return
        if self.cronemail!=None and mailThere==False:
            crontanContent.insert(0, mail+"\n")
        if restartThere==False:
            crontanContent.append(restart+"\n")
        if checknrestartThere==False:
            crontanContent.append(checknrestart+"\n")
        
        with open(os.path.expanduser('.crontmp'),'w') as f:
            for l in crontanContent:
                f.write(l)
        subprocess.call("crontab .crontmp", shell=True)
        os.remove(".crontmp")
        log.info("Cron Scripts Processed!")
    def update_bashrc(self):
        """Add AKRR enviroment variables to .bashrc"""
        log.info("Updating .bashrc")
        bashcontentNew=[]
        akrrHeader='#AKRR Server Environment Variables'
        if os.path.exists(os.path.expanduser("~/.bashrc")):
            log.info("Updating AKRR record in $HOME/.bashrc, backing to $HOME/.bashrc_akrrbak")
            subprocess.call("cp ~/.bashrc ~/.bashrcakrr", shell=True)
            with open(os.path.expanduser('~/.bashrc'),'r') as f:
                bashcontent=f.readlines()
                inAKRR=False
                for l in bashcontent:
                    if l.count(akrrHeader+' [Start]')>0:inAKRR=True
                    if not inAKRR:bashcontentNew.append(l)
                    if l.count(akrrHeader+' [End]')>0:inAKRR=False
        bashcontentNew.append("\n"+akrrHeader+" [Start]\n")
        bashcontentNew.append("export AKRR_HOME=\"{0}\"\n".format(akrr_home))
        bashcontentNew.append("export PATH=\"{0}/bin:$PATH\"\n".format(akrr_home))
        bashcontentNew.append(akrrHeader+" [End]\n\n")
        with open(os.path.expanduser('~/.bashrc'),'w') as f:
            for l in bashcontentNew:
                f.write(l)
        log.info("Appended AKRR records to $HOME/.bashrc")
if __name__ == '__main__':
    install=InstallAKRR()
    #check 
    install.check_previous_installation()
    #was in prep
    install.read_akrr_creds()
    install.read_modw_creds()
    install.read_sql_root_creds()
    install.ask_cron_email()
    
    install.init_mysql_dbs()
    install.generate_self_signed_certificate()
    install.generate_settings_file()
    install.set_permission_on_files()
    #was in setup
    install.db_check()
    install.generate_tables()
    install.start_daemon()
    install.check_daemon()
    install.install_cron_scripts()
    install.update_bashrc()
    
    
