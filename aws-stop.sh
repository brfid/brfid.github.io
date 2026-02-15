#!/bin/bash
# Stop the single edcloud instance without requiring a local edcloud checkout.
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

case "${STATE}" in
  stopped)
    echo "Instance already stopped: ${INSTANCE_ID}"
    ;;
  stopping)
    echo "Instance already stopping: ${INSTANCE_ID}"
    aws ec2 wait instance-stopped --instance-ids "${INSTANCE_ID}"
    echo "Instance is stopped."
    ;;
  *)
    echo "Stopping instance: ${INSTANCE_ID}"
    aws ec2 stop-instances --instance-ids "${INSTANCE_ID}" >/dev/null
    aws ec2 wait instance-stopped --instance-ids "${INSTANCE_ID}"
    echo "Instance is stopped."
    ;;
esac
