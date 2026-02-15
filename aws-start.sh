#!/bin/bash
# Start the single edcloud instance without requiring a local edcloud checkout.
#
# Optional overrides:
#   EDCLOUD_INSTANCE_ID   Explicit EC2 instance ID
#   EDCLOUD_NAME_TAG      Name tag to match (default: edcloud)
#   EDCLOUD_MANAGER_TAG   Manager tag key (default: edcloud:managed)
#   EDCLOUD_MANAGER_VALUE Manager tag value (default: true)

set -euo pipefail

NAME_TAG="${EDCLOUD_NAME_TAG:-edcloud}"
MANAGER_TAG="${EDCLOUD_MANAGER_TAG:-edcloud:managed}"
MANAGER_VALUE="${EDCLOUD_MANAGER_VALUE:-true}"

resolve_instance_id() {
  if [[ -n "${EDCLOUD_INSTANCE_ID:-}" ]]; then
    echo "${EDCLOUD_INSTANCE_ID}"
    return 0
  fi

  local id
  id="$(aws ec2 describe-instances \
    --filters \
      "Name=tag:${MANAGER_TAG},Values=${MANAGER_VALUE}" \
      "Name=tag:Name,Values=${NAME_TAG}" \
      "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query "Reservations[].Instances[] | sort_by(@, &LaunchTime)[-1].InstanceId" \
    --output text)"

  if [[ -z "${id}" || "${id}" == "None" ]]; then
    echo "No edcloud-managed instance found."
    echo "Set EDCLOUD_INSTANCE_ID or provision edcloud first."
    exit 1
  fi

  echo "${id}"
}

INSTANCE_ID="$(resolve_instance_id)"
STATE="$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --query "Reservations[0].Instances[0].State.Name" \
  --output text)"

if [[ "${STATE}" == "running" ]]; then
  echo "Instance already running: ${INSTANCE_ID}"
else
  echo "Starting instance: ${INSTANCE_ID}"
  aws ec2 start-instances --instance-ids "${INSTANCE_ID}" >/dev/null
  echo "Waiting for running state..."
  aws ec2 wait instance-running --instance-ids "${INSTANCE_ID}"
fi

PUBLIC_IP="$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)"

echo "Instance is running."
if [[ -n "${PUBLIC_IP}" && "${PUBLIC_IP}" != "None" ]]; then
  echo "Public IP: ${PUBLIC_IP}"
  echo "SSH (public): ssh ubuntu@${PUBLIC_IP}"
fi
echo "Tailscale host: edcloud"
