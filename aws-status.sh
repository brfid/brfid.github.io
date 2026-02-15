#!/bin/bash
# Check edcloud host status without requiring a local edcloud repo checkout.
#
# Optional overrides:
#   EDCLOUD_INSTANCE_ID   Explicit EC2 instance ID
#   EDCLOUD_NAME_TAG      Name tag to match (default: edcloud)
#   EDCLOUD_MANAGER_TAG   Manager tag key (default: edcloud:managed)
#   EDCLOUD_MANAGER_VALUE Manager tag value (default: true)
#   EDCLOUD_HOSTNAME      Tailscale hostname hint (default: edcloud)

set -euo pipefail

NAME_TAG="${EDCLOUD_NAME_TAG:-edcloud}"
MANAGER_TAG="${EDCLOUD_MANAGER_TAG:-edcloud:managed}"
MANAGER_VALUE="${EDCLOUD_MANAGER_VALUE:-true}"
TAILSCALE_HOST="${EDCLOUD_HOSTNAME:-edcloud}"

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

INSTANCE_TYPE="$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --query "Reservations[0].Instances[0].InstanceType" \
  --output text)"

PUBLIC_IP="$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)"

LAUNCH_TIME="$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --query "Reservations[0].Instances[0].LaunchTime" \
  --output text)"

echo "Instance:  ${INSTANCE_ID}"
echo "State:     ${STATE}"
echo "Type:      ${INSTANCE_TYPE}"
if [[ -n "${PUBLIC_IP}" && "${PUBLIC_IP}" != "None" ]]; then
  echo "Public IP: ${PUBLIC_IP}"
fi

echo "Tailscale: ${TAILSCALE_HOST} (connect from your tailnet)"

if [[ -n "${LAUNCH_TIME}" && "${LAUNCH_TIME}" != "None" ]]; then
  echo "Launched:  ${LAUNCH_TIME}"
fi

VOLUMES="$(aws ec2 describe-volumes \
  --filters "Name=attachment.instance-id,Values=${INSTANCE_ID}" \
  --query "Volumes[].[VolumeId,Size,VolumeType,State]" \
  --output text || true)"
if [[ -n "${VOLUMES}" ]]; then
  while read -r VOL_ID VOL_SIZE VOL_TYPE VOL_STATE; do
    [[ -z "${VOL_ID:-}" ]] && continue
    echo "Volume:    ${VOL_ID}  ${VOL_SIZE}GB ${VOL_TYPE}  (${VOL_STATE})"
  done <<<"${VOLUMES}"
fi

echo
echo "Estimated monthly cost (Assumes 4hrs/day runtime):"
echo "  Compute: \$4.51"
echo "  Storage: \$6.40"
echo "  Total:   \$10.91"
