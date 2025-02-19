#!/bin/bash

# written by Chris.McDonald@uwa.edu.au

MYSERVER="./station-server"
port="4000"

# ---------------------------------------

usage() {
    echo "Usage: $0 adjacencyfile startstations.sh"
    exit 1
}

if [ $# != "2" ]; then
    usage
fi
if [ ! -r $1 ]; then
    echo cannot read file $1
    usage
fi

# ---------------------------------------

PATH="/bin:/usr/bin"

TMPA="/tmp/ap-a$$"
TMPB="/tmp/ap-b$$"

cleanup() {
    rm -f $TMPA $TMPB
}

trap "cleanup ; exit 1" INT TERM

find_ports_in_use() {
    case `uname` in
	Linux*)
	    /bin/netstat -tulpn 2>&1 | \
		cut -c21-40 | sed 's/.*\:\(.*\)/\1/'
	    ;;
	Darwin*)
	    /usr/sbin/netstat -an | grep -E '^tcp|udp' | \
		cut -c22-40 | sed 's/.*\.\(.*\)/\1/'
	    ;;
    esac | grep '^[0-9]' | sort -nu
}

port_in_use() {
    grep -q "^$1\$" < $TMPA
}

build_sed() {
    SED="sed "
    while read from neighbours ; do
	while true ; do
	    (( port = port + 1 ))
	    if port_in_use $port ; then
		continue
	    fi
	    tport=$port
	    (( port = port + 1 ))
	    if port_in_use $port ; then
		continue
	    fi
	    SED="$SED -e \"s/^$from /$from XXX$tport XXX$port /\" -e \"s/ $from/ $port/\""
	    break
	done
    done < $TMPB
    SED="$SED -e \"s,^,$MYSERVER ,\" -e 's/\$/ \&/' -e 's/ \([0-9]\)/ localhost:\1/g' -e 's/XXX//g'"
}

# ---------------------------------------

find_ports_in_use       > $TMPA
echo reading file $1
expand < $1 | sed -e 's/^ *//' | tr -s ' ' | grep '^[A-Za-z]' > $TMPB

build_sed
eval $SED < $TMPB > $2

echo "creating file $2"
chmod +x $2

cleanup
exit 0
