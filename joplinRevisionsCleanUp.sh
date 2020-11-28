#!/usr/bin/env bash

DATABASE_DIR=/media/veracrypt1/joplin-desktop
DATABASE_NAME=database.sqlite
JOPLIN_DB=${DATABASE_DIR}/$DATABASE_NAME
JOPLIN_DIR=~/Nextcloud/Joplin
REVISIONS_ARCHIVE_DIR=.orphaned_revisions_archive
JOPLIN_BACKUP_FILE=~/JOPLIN_REMOTE_BACKUP.tgz
JOPLIN_DB_DATA=~/joplin-db-data.txt
LOG=~/joplin-remote-cleanup.log
BACKUP=1
DEBUG=0

echo "--------------- $(date) Joplin's revisions cleanup job starts ---------------" | tee -a $LOG

if [[ $BACKUP == 1 ]]; then
  echo "Backing up Joplin's remote local sync directory." | tee -a $LOG
  if [[ -f $JOPLIN_BACKUP_FILE ]]; then
    # a backup file already exists, rotating
    # ${string%substring} deletes the shortest match of substring from the end of string. 
    # https://tldp.org/LDP/abs/html/string-manipulation.html
    NB_BACKUPS=$(ls ${JOPLIN_BACKUP_FILE%.tgz}.*.tgz 2> /dev/null | wc -l)
    NB_BACKUPS=$(($NB_BACKUPS+1))
    mv $JOPLIN_BACKUP_FILE ${JOPLIN_BACKUP_FILE%.tgz}.${NB_BACKUPS}.tgz
    if [[ $? == 0 ]]; then
      echo "  * Backup rotation successful." | tee -a $LOG
    else
      echo "ERROR: backup rotation failure, aborting!" | tee -a $LOG
      exit 1
    fi
  fi
  tar -cvzf $JOPLIN_BACKUP_FILE --exclude=$REVISIONS_ARCHIVE_DIR $JOPLIN_DIR 2> /dev/null >> $LOG
  if [ $? == 0 ]; then
    echo "  * Backup successful ... moving forward." | tee -a $LOG
  else
    echo "ERROR: backup failed, aborting!" | tee -a $LOG
    exit 1
  fi
fi

if [[ ! -d $DATABASE_DIR ]]; then
  echo "ERROR: Joplin database not available, aborting!" | tee -a $LOG
  exit 1
fi

sqlite3 $JOPLIN_DB "select id from notes" > $JOPLIN_DB_DATA
sqlite3 $JOPLIN_DB "select id from folders" >> $JOPLIN_DB_DATA
sqlite3 $JOPLIN_DB "select id from resources" >> $JOPLIN_DB_DATA
sqlite3 $JOPLIN_DB "select id from master_keys" >> $JOPLIN_DB_DATA

########################################################################
## TODO more queries may be necessary to cover all items like tags, ...
##      Also getting known revision ids could be a way to get rid only
##      of orphaned revisions whatever the current sync status.
########################################################################

JOPLIN_ITEMS=($(sort $JOPLIN_DB_DATA)) # ordered list of IDs in Joplin's DB

echo "Number of items in Joplin's database: ${#JOPLIN_ITEMS[*]}" | tee -a $LOG

if [[ $DEBUG == 0 ]]; then
  rm $JOPLIN_DB_DATA
fi

FILES=($(ls ${JOPLIN_DIR}/*.md | sed -E -e "s/^\/.*\///" -e "s/([a-z0-9]*)\.md/\1/" | sort))
# ordered list of file IDs in Joplin's sync directory

echo "Number of files in Joplin's sync directory: ${#FILES[*]}" | tee -a $LOG

declare -a ORPHAN_FILES

for FILE in ${FILES[*]}; do
  MATCH=0
  for ID in ${JOPLIN_ITEMS[*]}; do
    if [[ $FILE == $ID ]]; then # TODO inefficient double loop, could be optimized
      MATCH=1
      break
    fi
  done
  if [[ $MATCH == 0 ]];then
    ORPHAN_FILES+=( $FILE )
    if [[ $DEBUG != 0 ]]; then
      printf "DEBUG:\t${FILE} => type: $(grep 'type_:' ${JOPLIN_DIR}/${FILE}.md | awk '{print $2}')\n" | tee -a $LOG
    fi
  fi
done

echo "Number of orphan files: ${#ORPHAN_FILES[*]}" | tee -a $LOG

if [[ ${#ORPHAN_FILES[*]} -gt 0 ]]; then # WEIRD ?!? using '>' actually redirects to a file '0' instead of testing
  if [[ ! -d ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR ]]; then
    mkdir ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR
    if [[ $? != 0 ]]; then
      echo "ERROR: couldn't create ${REVISIONS_ARCHIVE_DIR} directory, aborting!." | tee -a $LOG
      exit 1
    fi
  fi

  for ORPHAN_FILE in ${ORPHAN_FILES[*]}; do
    FILE_TYPE=$(grep type_ ${JOPLIN_DIR}/$ORPHAN_FILE.md | awk '{print $2}')
    if [[ $FILE_TYPE == 13 ]]; then
      # only archive revision files, not other kinds of Joplin's data
      if [[ $DEBUG != 0 ]]; then
        echo "DEBUG: mv ${JOPLIN_DIR}/${ORPHAN_FILE}.md ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR"
        # similar to a dry run option, display the command don't actually do anything
      else
        mv ${JOPLIN_DIR}/${ORPHAN_FILE}.md ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR
        if [[ $? != 0 ]]; then
          echo "ERROR while archiving orphaned revision ${ORPHAN_FILE}.md" | tee -a $LOG
        fi
      fi
    else
      printf "Skipping ${ORPHAN_FILE}.md\ttype: ${FILE_TYPE}\n" | tee -a $LOG
    fi
  done
else
  echo "DB and Joplin's dir in sync: no orphan file found :)" | tee -a $LOG
fi

echo "--------------- $(date) Joplin's revisions cleanup job done ---------------" | tee -a $LOG
