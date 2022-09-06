# Source:
# https://github.com/p6ril/joplinRevisionsCleanUp
#
# Usage:
# python.exe revisions-cleanup.py

import sys
import os
import os.path
import glob
import shutil
import sqlite3
import io
from pathlib import Path
import subprocess
import re

#
# VARIABLES
#

DRY_RUN         = True

USER_HOME       = str(Path.home()) # Windows: %USERPROFILE%, Linux: ~
ONEDRIVE_DIR    = os.environ['ONEDRIVE'] # Windows has an environment variable: %ONEDRIVE%
#ONEDRIVE_DIR    = "/path/to/your/OneDrive/" # on Linux
DATABASE_DIR    = os.path.join(USER_HOME, ".config", "joplin-desktop") # Windows: %USERPROFILE%\.config\joplin-desktop, Linux: ~/.config/joplin-desktop
#DATABASE_DIR    = os.path.join(USER_HOME, "snap/joplin-desktop/current/.config/joplin-desktop") # Linux (Snap): ~/snap/joplin-desktop/current/.config/joplin-desktop/
JOPLIN_DIR      = os.path.join(ONEDRIVE_DIR, "Anwendungen", "Joplin") # local sync directory of Joplin's remote folder

# Backups:
BACKUP_FILE     = os.path.join(USER_HOME, "Joplin_Remote_Backup") #.zip
DO_BACKUP       = True

# Leave as is:
DATABASE_NAME   = "database.sqlite"
JOPLIN_DB       = os.path.join(DATABASE_DIR, DATABASE_NAME)


#
# FUNCTIONS
#


def is_joplin_running():
    if sys.platform.startswith('win'):
        return b"Joplin.exe" in subprocess.check_output('tasklist', shell=True)
    elif sys.platform.startswith('linux'):
        # https://stackoverflow.com/a/4139017
        try:
            ps     = subprocess.Popen("ps -eaf | grep joplin-desktop", shell=True, stdout=subprocess.PIPE)
            output = ps.stdout.read().decode("utf-8")
            ps.stdout.close()
            ps.wait()
            return re.search('/joplin-desktop/', output) is not None
        except:
            return False
    return False


def rotation():  # creates a kind of "lifo" rotation, latest rotation is up in the queue
    backups = glob.glob(BACKUP_FILE + ".*.zip")
    spukcab = sorted(backups, reverse=True)
    count = len(spukcab) + 1
    if count > 5:
        print("WARNING: Joplin's backups are piling up, consider cleaning up old backups.")
    for archive in spukcab:
        os.rename(archive, BACKUP_FILE + "." + str(count) + ".zip")
        count -= 1
    os.rename(BACKUP_FILE + ".zip", BACKUP_FILE + ".1.zip")


def backup():
    if os.path.isfile(BACKUP_FILE + ".zip"):  # a backup file already exists, rotating backups
        rotation()
    shutil.make_archive(BACKUP_FILE, 'zip', JOPLIN_DIR)


def get_revisions_from_db():
    if os.path.isdir(DATABASE_DIR):
        conn = sqlite3.connect(JOPLIN_DB)
        c = conn.cursor()
        c.execute("select id from revisions")
        query = c.fetchall()  # fetchall() returns a list of result tuples (not a list of id values as strings)
        revisions = map(lambda i: i[0], query)
        conn.close()
        return set(revisions)
    else:
        print("ERROR: Joplin's database not found, aborting !")
        sys.exit(1)


def file_filter(fileName):
    """only keeps Joplin's revision files (type 13)"""
    result=False
    f=open(fileName, "r")
    for l in f:
        if l.find("type_: 13") != -1:
            result=True
            break
    f.close()
    return result


def file_map(fileName):
    """extracts the revision ID out of the file name"""
    i=fileName.rfind(os.path.sep)
    return fileName[i+1:-3]


def get_revisions_from_files():
    # no grep on Windows!
    if os.path.isdir(JOPLIN_DIR):
        revisions=glob.glob(JOPLIN_DIR + os.path.sep + "*.md")
        filtered_list=filter(file_filter, revisions)
        revisions=map(file_map, filtered_list)
        return set(revisions)
    else:
        print("ERROR: local sync directory of Joplin's remote not found !")
        sys.exit(1)


def reconcile():
    # check https://www.freecodecamp.org/news/python-sets-detailed-visual-introduction/
    database = get_revisions_from_db()
    files = get_revisions_from_files()
    if len(database ^ files) == 0:  # ^ symmetric difference, i.e. elements not in common in both sets
        print("Joplin's database and remote files for revisions are perfectly in sync :)")
        return  # everything's good in the world we can stop here
    if not database.issubset(files):
        print("ERROR: some revisions in DB are missing their remote file counterpart !")
        for item in list(database - files):
            print("    - " + item)
    orphans = list(files - database)
    if len(orphans) > 0:
        print("Number of orphaned revisions found on the remote: " + str(len(orphans)))
        if DRY_RUN:
            for item in orphans:
                print("    - " + item + ".md")
        else:
            print("Deleting ...")
            for item in orphans:
                path = os.path.join(JOPLIN_DIR, item + ".md")
                print("    - " + item + ".md")
                os.remove(path)


if __name__ == "__main__":
    print("""Joplin Revisions Cleanup
------------------------
Original by p6ril
Modified by FelisDiligens
""")
    if is_joplin_running():
        print("ERROR: Please make sure to close Joplin! (File → Quit)")
        sys.exit(-1)

    if DRY_RUN:
        print("Dry run: Nothing will be deleted.")

    if DO_BACKUP and not DRY_RUN:
        print("Making backup...")
        backup()

    print("Cleanup...")
    reconcile()
    
    print("Done.")