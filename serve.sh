#! /usr/bin/bash

RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

[ -n "$DEBUG" ] && function printcmd {
	echo -e "${BLUE}\$${NC} ${1}"
}

function printerror {
	echo -e "${RED}ERROR${NC}${1}"
	[ "$2" == "noexit" ] || exit 1
}

[ -s "/usr/bin/node" ] || printerror 'could not find node'

if [ -z "$1" ] || [ "$1" == "start" ]
then {
	[ -n "$DEBUG" ] && printcmd 'nohup serve-n8n start &'
	nohup node $DIR/scripts/serve-n8n.mjs start >$DIR/logs/nohup.out 2>&1 &
} else {
	[ -n "$DEBUG" ] && printcmd "serve-n8n $@"
	node $DIR/scripts/serve-n8n.mjs $@
} fi
