#!/usr/bin/env bash
# Builds the pre-seeded deck, days before the event, from the station question
# lists alone. Run this as soon as the question lists exist.
#
# The point is that from that moment on there is always a presentable deck on
# disk. Every later run can only improve on it, and no failure on the night can
# leave Fleet Command standing in front of the room with nothing.
#
# This is just synthesize.sh with MODE=seeded. It reads the same stations/*/
# inputs, so if a transcript somehow already exists it will use it.
set -euo pipefail
export MODE=seeded
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/synthesize.sh" "$@"
