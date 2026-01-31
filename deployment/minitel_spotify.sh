#!/bin/bash

# set -euxo pipefail

echo PLAYER_EVENT: $PLAYER_EVENT

if [ "$PLAYER_EVENT" = "playing" ] || [ "$PLAYER_EVENT" = "track_changed" ]; then
    curl -X PATCH http://127.0.0.1:8000/current_track/$TRACK_ID &> /dev/null
fi
if [ "$PLAYER_EVENT" = "session_connected" ] ; then
    curl -X POST http://127.0.0.1:8000/reset_minitel &> /dev/null
fi
