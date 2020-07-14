#!/usr/bin/env bash

DATABASE_DIR=/media/veracrypt1/joplin-desktop
DATABASE_NAME=database.sqlite
JOPLIN_DB=${DATABASE_DIR}/$DATABASE_NAME
JOPLIN_DIR=~/Nextcloud/Joplin
REVISIONS_ARCHIVE_DIR=.orphan_revisions_archive
JOPLIN_BACKUP_FILE=JOPLIN_SYNC_DIR_BACKUP.tar
JOPLIN_DB_DATA=joplin-db-data.txt
DEBUG=1

if [ $DEBUG == 0 ]; then
  echo "Backing up Joplin's sync directory to the current user home directory."

  tar -cvf ~/$JOPLIN_BACKUP_FILE $JOPLIN_DIR
  if [ $? == 0 ]; then
    echo "Backup successful ... moving forward."
  else
    echo "Backup failed, aborting !"
    exit 1
  fi
fi

if [ ! -d $DATABASE_DIR ]; then
  echo "Joplin database not available, aborting !"
  exit 1
fi

sqlite3 $JOPLIN_DB "select id from notes" > ./$JOPLIN_DB_DATA
sqlite3 $JOPLIN_DB "select id from folders" >> ./$JOPLIN_DB_DATA
sqlite3 $JOPLIN_DB "select id from resources" >> ./$JOPLIN_DB_DATA
sqlite3 $JOPLIN_DB "select id from master_keys" >> ./$JOPLIN_DB_DATA

########################################################################
## TODO more queries may be necessary to cover all items like tags, ...
##      Also getting known revision ids could be a way to get rid only
##      of orphan revisions whatever the current sync status.
########################################################################

JOPLIN_ITEMS=($(sort $JOPLIN_DB_DATA)) # ordered list of IDs in Joplin's DB

echo "Number of items in Joplin's database: ${#JOPLIN_ITEMS[*]}"

#rm ./$JOPLIN_DB_DATA

FILES=($(ls ${JOPLIN_DIR}/*.md | sed -E -e "s/^\/.*\///" -e "s/([a-z0-9]*)\.md/\1/" | sort))
# ordered list of file IDs in Joplin's sync directory

echo "Number of files in Joplin's sync directory: ${#FILES[*]}"

declare -a ORPHAN_FILES

for FILE in ${FILES[*]}; do
  MATCH=0
  for ID in ${JOPLIN_ITEMS[*]}; do
    if [ $FILE == $ID ]; then # TODO inefficient double loop, could be optimized
      MATCH=1
      break
    fi
  done
  if [ $MATCH == 0 ];then
    ORPHAN_FILES+=( $FILE )
    if [ $DEBUG != 0 ]; then
      printf "DEBUG\t${FILE} => type: $(grep 'type_:' ${JOPLIN_DIR}/${FILE}.md | awk '{print $2}')\n"
    fi
  fi
done

echo "Number of orphan files: ${#ORPHAN_FILES[*]}"

if [ ${#ORPHAN_FILES[*]} -gt 0 ]; then # WEIRD ?!? using '>' actually redirects to a file '0' instead of testing
  if [ ! -d ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR ]; then
    mkdir ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR
  fi

  for ORPHAN_FILE in ${ORPHAN_FILES[*]}; do
    FILE_TYPE=$(grep type_ ${JOPLIN_DIR}/$ORPHAN_FILE.md | awk '{print $2}')
    if [ $FILE_TYPE == 13 ]; then
      if [ $DEBUG != 0 ]; then
        echo "DEBUG mv ${JOPLIN_DIR}/${ORPHAN_FILE}.md ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR"
      else
        mv ${JOPLIN_DIR}/${ORPHAN_FILE}.md ${JOPLIN_DIR}/$REVISIONS_ARCHIVE_DIR
      fi
    else
      printf "Skipping ${ORPHAN_FILE}.md\ttype: ${FILE_TYPE}\n"
    fi
  done
else
  echo "DB and Joplin's dir in sync: no orphan file found :)"
fi
