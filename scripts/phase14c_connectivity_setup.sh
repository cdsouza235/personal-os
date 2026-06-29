#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repo_root/.env.local"
tmp_env_file="${env_file}.tmp.$$"

cleanup() {
  rm -f "$tmp_env_file"
}
trap cleanup EXIT HUP INT TERM

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
  printf "%s=%s\n" "$var_name" "$(quote_shell "$value")" >> "$tmp_env_file"
}

prompt_plain() {
  local label="$1"
  local var_name="$2"
  local value
  printf "%s: " "$label" >&2
  IFS= read -r value
  if [[ -z "$value" ]]; then
    printf "error: %s cannot be empty\n" "$var_name" >&2
    exit 1
  fi
  printf "%s=%s\n" "$var_name" "$(quote_shell "$value")" >> "$tmp_env_file"
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
  printf "%s=%s\n" "$var_name" "$(quote_shell "$value")" >> "$tmp_env_file"
}

cat >&2 <<'EOF'
Phase 14-C connectivity setup

This writes .env.local in the repo root. .env.local is gitignored.
If .env.local already exists, this script refuses to overwrite it.
Do not paste tokens into chat. Type them only into this local prompt.
Token and API key values are not printed by this script.
EOF

if [[ -e "$env_file" ]]; then
  cat >&2 <<EOF
error: $env_file already exists.
Refusing to overwrite local configuration.
Move or remove that file before rerunning this setup script.
EOF
  exit 1
fi

umask 077
: > "$tmp_env_file"
chmod 600 "$tmp_env_file"

prompt_plain_default \
  "Gmail credential label or connector label" \
  "PERSONALOS_PHASE14C_GMAIL_CREDENTIAL" \
  "gmail_connector"

prompt_plain \
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

if [[ -e "$env_file" ]]; then
  cat >&2 <<EOF
error: $env_file was created while setup was running.
Refusing to overwrite local configuration.
EOF
  exit 1
fi
mv "$tmp_env_file" "$env_file"
trap - EXIT HUP INT TERM

cat >&2 <<EOF

Wrote $env_file with mode 600.

Next verification command:
  set -a; source .env.local; set +a; PYTHONPATH=src python3 -m personalos.cli phase14c connectivity-setup --json
EOF
