#!/bin/zsh
cd "$(dirname "$0")"
unset ELECTRON_RUN_AS_NODE
echo "Starting SafeClaw local Electron app..."
echo "Close this Terminal window to stop the app."
npm start
