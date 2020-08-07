#!/bin/bash

set -e

unset ENTRYPOINT_CMD
unset ENTRYPOINT_ARGS
[ "$#" -ge 1 ] && ENTRYPOINT_CMD="$1" && [ "$#" -gt 1 ] && shift 1 && ENTRYPOINT_ARGS=( "$@" )

# modify the UID/GID for the default user/group (for example, 1000 -> 1001)
usermod --non-unique --uid ${PUID:-${DEFAULT_UID}} ${PUSER}
groupmod --non-unique --gid ${PGID:-${DEFAULT_GID}} ${PGROUP}

# change user/group ownership of any files/directories belonging to the original IDs
if [[ -n ${PUID} ]] && [[ "${PUID}" != "${DEFAULT_UID}" ]]; then
  find / -path /sys -prune -o -path /proc -prune -o -user ${DEFAULT_UID} -exec chown -f ${PUID} "{}" \; || true
fi
if [[ -n ${PGID} ]] && [[ "${PGID}" != "${DEFAULT_GID}" ]]; then
  find / -path /sys -prune -o -path /proc -prune -o -group ${DEFAULT_GID} -exec chown -f :${PGID} "{}" \; || true
fi

# if there are semicolon-separated PUSER_CHOWN entries explicitly specified, chown them too
if [[ -n ${PUSER_CHOWN} ]]; then
  IFS=';' read -ra ENTITIES <<< "${PUSER_CHOWN}"
  for ENTITY in "${ENTITIES[@]}"; do
    chown -R ${PUSER}:${PGROUP} "${ENTITY}" || true
  done
fi

# determine if we are now dropping privileges to exec ENTRYPOINT_CMD
if [[ "$PUSER_PRIV_DROP" == "true" ]]; then
  EXEC_USER="${PUSER}"
  USER_HOME="$(getent passwd ${PUSER} | cut -d: -f6)"
else
  EXEC_USER="${USER:-root}"
  USER_HOME="${HOME:-/root}"
fi

# execute the entrypoint command specified
su --shell /bin/bash --preserve-environment ${EXEC_USER} << EOF
export USER="${EXEC_USER}"
export HOME="${USER_HOME}"
whoami
id
if [ ! -z "${ENTRYPOINT_CMD}" ]; then
  if [ -z "${ENTRYPOINT_ARGS}" ]; then
    "${ENTRYPOINT_CMD}"
  else
    "${ENTRYPOINT_CMD}" $(printf "%q " "${ENTRYPOINT_ARGS[@]}")
  fi
fi
EOF
