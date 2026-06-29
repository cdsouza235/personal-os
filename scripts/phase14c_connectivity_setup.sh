#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repo_root/.env.local"

quote_shell() {
  local value="$1"
  printf "%q" "$value"
}

prompt_secret() {
  local label="$1"
  local var_name="$2"
  local value
  printf "%s: " "$label" >&2
  IFS= read -r -s value
  printf "\n" >&2
  if [[ -z "$value" ]]; then
    printf "error: %s cannot be empty\n" "$var_name" >&2
    exit 1
  fi
  printf "%s=%s\n" "$var_name" "$(quote_shell "$value")" >> "$env_file"
}

prompt_plain_default() {
  local label="$1"
  local var_name="$2"
  local default_value="$3"
  local value
  printf "%s [%s]: " "$label" "$default_value" >&2
  IFS= read -r value
  value="${value:-$default_value}"
  if [[ -z "$value" ]]; then
    printf "error: %s cannot be empty\n" "$var_name" >&2
    exit 1
  fi
  printf "%s=%s\n" "$var_name" "$(quote_shell "$value")" >> "$env_file"
}

cat >&2 <<'EOF'
Phase 14-C connectivity setup

This writes .env.local in the repo root. .env.local is gitignored.
Do not paste tokens into chat. Type them only into this local prompt.
No values are printed by this script.
EOF

umask 077
: > "$env_file"
chmod 600 "$env_file"

prompt_plain_default \
  "Gmail credential label or connector label" \
  "PERSONALOS_PHASE14C_GMAIL_CREDENTIAL" \
  "gmail_connector"

prompt_secret \
  "Controlled Gmail recipient for the self-send smoke" \
  "PHASE14C_GMAIL_CONTROLLED_RECIPIENT"

prompt_secret \
  "Todoist API token" \
  "PERSONALOS_PHASE14C_TODOIST_TOKEN"

prompt_plain_default \
  "Google Calendar credential label" \
  "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL" \
  "google_calendar_connector"

prompt_plain_default \
  "OpenClaw local/test/sandbox mode" \
  "PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE" \
  "local_test_sandbox"

prompt_plain_default \
  "OpenClaw model provider" \
  "PERSONALOS_OPENCLAW_MODEL_PROVIDER" \
  "openrouter"

prompt_secret \
  "OpenRouter API key" \
  "PERSONALOS_OPENCLAW_MODEL_API_KEY"

prompt_plain_default \
  "OpenRouter Nemotron Super model ID" \
  "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL" \
  "nvidia/nemotron-3-super-120b-a12b"

prompt_plain_default \
  "OpenRouter GLM 5.2 model ID" \
  "PERSONALOS_OPENCLAW_GLM_5_2_MODEL" \
  "z-ai/glm-5.2"

cat >&2 <<EOF

Wrote $env_file with mode 600.

Next verification command:
  set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c connectivity-setup --json
EOF
