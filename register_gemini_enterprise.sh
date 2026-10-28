#!/usr/bin/env bash
# Register the deployed A2UI Component Showcase Agent into Gemini Enterprise.
# Reads all variables from config.json in the same directory (or $CONFIG_FILE).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/config.json}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Error: Config file not found at ${CONFIG_FILE}" >&2
  exit 1
fi

eval "$(python3 - "${CONFIG_FILE}" <<'PYEOF'
import json, shlex, sys
with open(sys.argv[1], encoding="utf-8") as f:
    c = json.load(f)
for k in (
    "project_id",
    "ge_location",
    "ge_app_id",
    "reasoning_engine",
    "agent_display_name",
    "agent_description",
    "tool_description",
):
    print(f"{k.upper()}={shlex.quote(str(c.get(k, '')).strip())}")
PYEOF
)"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "YOUR_PROJECT_ID" ]]; then
  echo "Error: Set a valid 'project_id' in ${CONFIG_FILE}" >&2
  exit 1
fi
if [[ -z "${GE_APP_ID}" || "${GE_APP_ID}" == "YOUR_GEMINI_ENTERPRISE_APP_ID" ]]; then
  echo "Error: Set a valid 'ge_app_id' in ${CONFIG_FILE}" >&2
  exit 1
fi
if [[ -z "${REASONING_ENGINE}" ]]; then
  echo "Error: 'reasoning_engine' is empty in ${CONFIG_FILE}. Run 'python3 deploy.py' first or set it manually." >&2
  exit 1
fi

GE_LOCATION="${GE_LOCATION:-global}"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
ADC_TOKEN=$(gcloud auth application-default print-access-token)

if [[ "${GE_LOCATION}" == "global" ]]; then
  ENDPOINT="https://discoveryengine.googleapis.com"
else
  ENDPOINT="https://${GE_LOCATION}-discoveryengine.googleapis.com"
fi

PARENT="projects/${PROJECT_NUMBER}/locations/${GE_LOCATION}/collections/default_collection/engines/${GE_APP_ID}/assistants/default_assistant"

BODY=$(python3 - "${AGENT_DISPLAY_NAME}" "${AGENT_DESCRIPTION}" "${TOOL_DESCRIPTION}" "${REASONING_ENGINE}" <<'PYEOF'
import json, sys
display_name, description, tool_desc, re_name = sys.argv[1:5]
print(json.dumps({
    "displayName": display_name,
    "description": description,
    "adkAgentDefinition": {
        "toolSettings": {"toolDescription": tool_desc},
        "provisionedReasoningEngine": {"reasoningEngine": re_name},
    },
}))
PYEOF
)

echo "Registering ${REASONING_ENGINE} into Gemini Enterprise app ${GE_APP_ID} (${GE_LOCATION})..."

curl -sS -X POST \
  -H "Authorization: Bearer ${ADC_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${ENDPOINT}/v1alpha/${PARENT}/agents" \
  -d "${BODY}"
echo ""