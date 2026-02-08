#!/bin/bash
set -e

# Log output
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== ARPANET Test Instance Setup ==="
echo "Starting at: $(date)"

# Update system
echo "Updating system..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Install Docker Compose (latest)
echo "Installing Docker Compose..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -oP '"tag_name": "\K(.*)(?=")')
curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install additional tools
echo "Installing additional tools..."
apt-get install -y git make python3 python3-pip telnet netcat-openbsd

# Set up persistent logs volume
echo "Setting up persistent logs volume..."
# Find the logs volume (should be /dev/nvme1n1 on newer instances)
LOGS_DEVICE=$(lsblk -o NAME,SIZE | grep "20G" | awk '{print "/dev/"$1}' | grep nvme | head -1)
if [ -z "$LOGS_DEVICE" ]; then
    # Fallback for older instance types
    LOGS_DEVICE="/dev/xvdf"
fi

echo "Logs device detected: $LOGS_DEVICE"

# Check if volume already has a filesystem
if ! blkid "$LOGS_DEVICE"; then
    echo "Formatting logs volume as ext4..."
    mkfs.ext4 -L arpanet-logs "$LOGS_DEVICE"
else
    echo "Logs volume already formatted"
fi

# Create mount point
mkdir -p /mnt/arpanet-logs
chown ubuntu:ubuntu /mnt/arpanet-logs

# Mount the volume
echo "Mounting logs volume..."
mount "$LOGS_DEVICE" /mnt/arpanet-logs
chown ubuntu:ubuntu /mnt/arpanet-logs

# Add to fstab for persistence across reboots
if ! grep -q "/mnt/arpanet-logs" /etc/fstab; then
    echo "LABEL=arpanet-logs /mnt/arpanet-logs ext4 defaults,nofail 0 2" >> /etc/fstab
fi

# Create directory structure
su - ubuntu -c "mkdir -p /mnt/arpanet-logs/builds"
su - ubuntu -c "mkdir -p /mnt/arpanet-logs/active"

echo "Logs volume mounted at /mnt/arpanet-logs"

# Clone repository as ubuntu user
echo "Cloning repository..."
su - ubuntu -c "git clone ${git_repo} /home/ubuntu/brfid.github.io"
su - ubuntu -c "cd /home/ubuntu/brfid.github.io && git checkout ${git_branch}"

# Run setup script
echo "Running setup script..."
su - ubuntu -c "cd /home/ubuntu/brfid.github.io && ./test_infra/setup.sh"

# Pre-pull VAX image to save time
echo "Pre-pulling VAX Docker image..."
su - ubuntu -c "docker pull jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215"

echo "Setup complete at: $(date)"
echo "Instance ready for testing"
