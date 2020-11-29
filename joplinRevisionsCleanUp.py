#!/usr/bin/env python3

import sys
import os
import os.path
import glob # unix style pathname pattern expansion (in particular '~')
import tarfile
import sqlite3
import io

USER_HOME             = os.path.expanduser("~")
DATABASE_DIR          = "/media/veracrypt1/joplin-desktop" # my Joplin directory is in an ecrypted container
DATABASE_NAME         = "database.sqlite"
JOPLIN_DB             = DATABASE_DIR + "/" + DATABASE_NAME
JOPLIN_DIR            = USER_HOME + "/Nextcloud/Joplin" # local sync directory of Joplin's remote folder
REVISIONS_ARCHIVE_DIR = ".orphaned_revisions_archive"
JOPLIN_BACKUP_FILE    = USER_HOME + "/JOPLIN_REMOTE_BACKUP.tgz"
BACKUP                = True
DEBUG                 = False

def rotation(): # creates a lifo rotation, latest rotation is up in the queue
    backups=glob.glob(JOPLIN_BACKUP_FILE[0:-4] + ".*.tgz")
    spukcab=sorted(backups, reverse=True)
    count=len(spukcab) + 1
    if count > 5:
        print("WARNING: Joplin's backups are piling up, consider cleaning up old backups.")
    for archive in spukcab:
        os.rename(archive, JOPLIN_BACKUP_FILE[0:-4] + "." + str(count) + ".tgz")
        count -= 1
    os.rename(JOPLIN_BACKUP_FILE, JOPLIN_BACKUP_FILE[0:-4] + ".1.tgz")

def backupFilter(tarinfo):
    if tarinfo.name.find(REVISIONS_ARCHIVE_DIR) < 0: # exclude any existing orphaned revision archives
        return tarinfo
    else:
        return None

def backup():
    if BACKUP:
        if os.path.isfile(JOPLIN_BACKUP_FILE): # a backup file already exists, rotating backups
            rotation()
        archive=tarfile.open(JOPLIN_BACKUP_FILE, "w:gz")
        archive.add(JOPLIN_DIR, filter=backupFilter)
        archive.close()

def getRevisionsFromDB():
    if os.path.isdir(DATABASE_DIR):
        conn=sqlite3.connect(JOPLIN_DB)
        c=conn.cursor()
        c.execute("select id from revisions")
        query=c.fetchall() # fetchall() returns a list of result tuples (not a list of id values as strings)
        revisions=map(lambda i : i[0], query)
        conn.close()
        return set(revisions)
    else:
        print("ERROR: Joplin's Veracrypt container not mounted, aborting !")
        sys.exit(1)

def fileFilter(fileName): # only keeps Joplin's revision files (type 13)
    result=False
    f=open(fileName, "r")
    for l in f:
        if l.find("type_: 13") != -1:
            result=True
            break
    f.close()
    return result

def fileMap(fileName): # extracts the revision ID out of the file name
    i=fileName.rfind("/")
    return fileName[i+1:-3]

def getRevisionsFromFiles():
    if os.path.isdir(JOPLIN_DIR):
        revisions=glob.glob(JOPLIN_DIR + "/*.md")
        filteredList=filter(fileFilter, revisions)
        revisions=map(fileMap, filteredList)
        return set(revisions)
    else:
        print("ERROR: local sync directory of Joplin's remote not found !")
        sys.exit(1)

def reconcile():
    # check https://www.freecodecamp.org/news/python-sets-detailed-visual-introduction/
    database=getRevisionsFromDB()
    files=getRevisionsFromFiles()
    if len(database^files) == 0: # ^ symmetric difference, i.e. elements not in common in both sets 
        print("Joplin's database and remote files for revisions are perfectly in sync :)")
    elif not database.issubset(files):
        print ("ERROR: some revisions in DB are missing their remote file counterpart !")
        for item in list(database-files):
            print("    - " + item)
    else:
        orphans=list(files-database)
        print("Number of orphaned revisions found on the remote: " + str(len(orphans)))
        target=JOPLIN_DIR + "/" + REVISIONS_ARCHIVE_DIR
        if not os.path.isdir(target):
            os.mkdir(target)
        print("Archiving ...")
        for item in orphans:
            src=JOPLIN_DIR + "/" + item + ".md"
            dst=target + "/" + item + ".md"
            if DEBUG:
                print(src + " => " + dst)
            else:
                print("    - " + item + ".md")
                os.rename(src, dst)

backup()
reconcile()