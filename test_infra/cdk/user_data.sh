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

# Clone repository as ubuntu user
echo "Cloning repository..."
su - ubuntu -c "git clone ${git_repo} /home/ubuntu/brfid.github.io"
su - ubuntu -c "cd /home/ubuntu/brfid.github.io && git checkout ${git_branch}"

# Set up logs volume and retention policy via Python manager
echo "Configuring logs volume and retention policy..."
python3 /home/ubuntu/brfid.github.io/test_infra/scripts/manage_logs_volume.py \
  --mode setup \
  --logs-enabled ${logs_volume_enabled} \
  --retention-days ${logs_retention_days}

cat >/etc/cron.d/arpanet-log-retention <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
17 3 * * * root /usr/bin/python3 /home/ubuntu/brfid.github.io/test_infra/scripts/manage_logs_volume.py --mode cleanup --retention-days ${logs_retention_days} >> /var/log/arpanet-log-retention.log 2>&1
CRON
chmod 0644 /etc/cron.d/arpanet-log-retention
echo "Daily log retention cleanup scheduled (3:17 AM)"

# Run setup script
echo "Running setup script..."
su - ubuntu -c "cd /home/ubuntu/brfid.github.io && ./test_infra/setup.sh"

# Pre-pull VAX image to save time
echo "Pre-pulling VAX Docker image..."
su - ubuntu -c "docker pull jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215"

echo "Setup complete at: $(date)"
echo "Instance ready for testing"
