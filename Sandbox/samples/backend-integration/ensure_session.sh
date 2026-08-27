#!/usr/bin/env bash
set -euo pipefail

: "${LMT_TOOL_ID:?set LMT_TOOL_ID}"
: "${LMT_SESSION_ID:=lmt-backend-session}"

# The CLI owns endpoint creation and temporary authorization. This wrapper only
# exposes the stable Tool/Session identifiers to the application layer.
agentkit sandbox shell \
  --tool-id "$LMT_TOOL_ID" \
  --tool-type CodeEnv \
  --sid "$LMT_SESSION_ID" \
  --command 'printf LMT_BACKEND_SESSION_OK'
