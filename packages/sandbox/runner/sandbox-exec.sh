#!/bin/bash
# sandbox-exec.sh - Secure code execution with Bubblewrap

WORKSPACE="$1"
COMMAND="$2"
TIMEOUT="${3:-60}"

bwrap \
    --unshare-all \
    --share-net \
    --die-with-parent \
    --new-session \
    --ro-bind /usr /usr \
    --ro-bind /lib /lib \
    --ro-bind /lib64 /lib64 \
    --ro-bind /bin /bin \
    --bind "$WORKSPACE" /workspace \
    --dev /dev \
    --proc /proc \
    --tmpfs /tmp \
    --setenv PATH "/usr/local/bin:/usr/bin:/bin" \
    --setenv HOME "/tmp" \
    --timeout "$TIMEOUT" \
    sh -c "cd /workspace && $COMMAND"
