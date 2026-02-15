# ARPANET Production Deployment Guide

---
**⚠️ DEPRECATED (2026-02-14)**

This guide documents the old ArpanetProductionStack (2x t3.micro + EFS).
**Current deployment**: See edcloud docs:
- `https://github.com/brfid/edcloud/blob/main/README.md`
- `https://github.com/brfid/edcloud/blob/main/MIGRATION.md`

Stack destroyed 2026-02-14. Retained for historical reference only.

---

## Overview

This guide deploys the permanent two-machine ARPANET infrastructure to AWS.

**What you get:**
- 2x EC2 t3.micro instances (VAX + PDP-11)
- Shared EFS log storage (~$0.73/month)
- S3 log archival (negligible cost)
- **Total: ~$17.90/month**

---

## Quick Start

### 1. Deploy Infrastructure

```bash
cd /home/whf/brfid.github.io
source .venv/bin/activate
cd infra/cdk

# Deploy
cdk deploy -a "python3 app_production.py" ArpanetProductionStack

# Note the outputs:
# - VaxPublicIP
# - Pdp11PublicIP
# - EfsFileSystemId
# - LogArchiveBucket
```

**Wait ~5 minutes** for user data scripts to complete (installs Docker, mounts EFS, clones repo).

### 2. Verify Setup

```bash
# Get IPs from CDK output
VAX_IP=<from-output>
PDP11_IP=<from-output>

# SSH to VAX
ssh ubuntu@$VAX_IP

# Verify EFS mounted
df -h | grep arpanet-logs
ls -la /mnt/arpanet-logs

# Verify Docker
docker --version
docker compose version

# Verify repo cloned
ls ~/brfid.github.io
```

### 3. Start ARPANET Services

```bash
# On VAX instance
cd ~/brfid.github.io
docker compose -f docker-compose.production.yml up -d

# Check status
docker ps
docker logs arpanet-vax --tail 50

# Verify logs writing to EFS
ls -lh /mnt/arpanet-logs/vax/
tail -f /mnt/arpanet-logs/vax/boot.log
```

### 4. Access Systems

```bash
# VAX console
telnet $VAX_IP 2323

# PDP-11 console
telnet $PDP11_IP 2327

# Or from local machine:
telnet <vax-public-ip> 2323
```

---

## Architecture

```
AWS EC2 Instances (t3.micro)
┌────────────────────┐      ┌────────────────────┐
│   VAX Host         │      │   PDP-11 Host      │
│   $7.50/mo         │      │   $7.50/mo         │
│                    │      │                    │
│   Docker:          │      │   Docker:          │
│   ├─ vax           │      │   ├─ pdp11         │
│   ├─ imp1          │      │   ├─ imp2          │
│   └─ logger        │      │   └─ logger        │
│                    │      │                    │
│   Writes to:       │      │   Writes to:       │
│   /mnt/arpanet-logs/vax/  │   /mnt/arpanet-logs/pdp11/
└─────────┬──────────┘      └─────────┬──────────┘
          │                           │
          └──────────┬────────────────┘
                     │
              ┌──────▼──────┐
              │ EFS Volume  │
              │ ~$0.73/mo   │
              │             │
              │ Auto-move   │
              │ to IA after │
              │ 7 days      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │ S3 Bucket   │
              │ ~$0.02/mo   │
              │             │
              │ Daily sync  │
              │ Archive 30d │
              └─────────────┘
```

---

## Log Storage Layout

### EFS Mount: `/mnt/arpanet-logs/`

```
/mnt/arpanet-logs/
├── vax/
│   ├── boot.log              # VAX boot sequences
│   ├── network.log           # VAX network activity
│   ├── arpanet.log           # ARPANET protocol messages
│   └── build-pipeline.log    # Resume build logs
│
├── pdp11/
│   ├── boot.log              # PDP-11 boot sequences
│   ├── network.log           # PDP-11 network activity
│   └── arpanet.log           # ARPANET protocol messages
│
└── shared/
    ├── imp1.log              # IMP #1 logs
    ├── imp2.log              # IMP #2 logs
    ├── orchestrator.log      # Multi-host coordination
    └── pipeline.log          # Build pipeline overall
```

### Automatic Lifecycle

```
Day 0-7:   Standard EFS tier ($0.30/GB-month)
Day 8+:    Infrequent Access tier ($0.016/GB-month)
Daily:     Sync to S3 (2 AM cron job)
Day 30+:   S3 → Glacier Instant Retrieval ($0.004/GB-month)
```

---

## Monitoring

### Check Instance Health

```bash
# List instances
aws ec2 describe-instances \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=ArpanetProductionStack" \
  --query 'Reservations[*].Instances[*].[Tags[?Key==`Name`].Value|[0],State.Name,PublicIpAddress]' \
  --output table
```

### Check Logs

```bash
# SSH to instance
ssh ubuntu@$VAX_IP

# Recent activity
tail -f /mnt/arpanet-logs/vax/boot.log

# Log sizes
du -sh /mnt/arpanet-logs/*

# EFS usage
df -h /mnt/arpanet-logs
```

### Check S3 Archives

```bash
# List archived logs
aws s3 ls s3://arpanet-logs-972626128180/ --recursive --human-readable

# Download specific log
aws s3 cp s3://arpanet-logs-972626128180/vax/2026-02-13-boot.log.gz .
```

---

## Cost Management

### Current Costs (~$17.90/month)

| Item | Cost/Month | Notes |
|------|------------|-------|
| VAX t3.micro | $7.50 | ~$0.25/day |
| PDP-11 t3.micro | $7.50 | ~$0.25/day |
| 2x Root volumes (8GB) | $1.28 | $0.64 each |
| EFS (10GB with IA) | $0.73 | Auto-tiers after 7 days |
| S3 archive | $0.02 | ~1GB, moves to Glacier |
| **Total** | **$17.90** | |

### Reduce Costs

**Stop when not in use** (saves ~$15/month):
```bash
# Stop instances (keeps data)
aws ec2 stop-instances --instance-ids <vax-id> <pdp11-id>

# Storage costs continue: ~$2/month (EFS + S3 + volumes)
```

**Use Spot Instances** (saves ~70%):
- Edit CDK stack to use spot instances
- Risk: Can be interrupted
- Good for: Development/testing

---

## Maintenance

### Update Code

```bash
# SSH to instance
ssh ubuntu@$VAX_IP
cd ~/brfid.github.io

# Pull latest code
git pull origin main

# Rebuild containers
docker compose -f docker-compose.production.yml build

# Restart services
docker compose -f docker-compose.production.yml up -d
```

### Rotate Logs

```bash
# Automatic via cron (daily at 2 AM)
# Manual trigger:
sudo /etc/cron.daily/arpanet-log-sync
```

### Clean Old Logs

```bash
# Compress logs older than 7 days
find /mnt/arpanet-logs -name "*.log" -mtime +7 -exec gzip {} \;

# Delete local archives older than 30 days (they're in S3)
find /mnt/arpanet-logs -name "*.log.gz" -mtime +30 -delete
```

---

## Troubleshooting

### EFS Not Mounted

```bash
# Check mount
mount | grep arpanet-logs

# Remount
sudo mount -a

# Check security group allows NFS
aws ec2 describe-security-groups \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=ArpanetProductionStack"
```

### Docker Containers Not Starting

```bash
# Check logs
docker logs arpanet-vax

# Check EFS permissions
ls -la /mnt/arpanet-logs
sudo chown -R ubuntu:docker /mnt/arpanet-logs

# Restart Docker
sudo systemctl restart docker
```

### S3 Sync Failing

```bash
# Check IAM permissions
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://arpanet-logs-972626128180/

# Manual sync
aws s3 sync /mnt/arpanet-logs/ s3://arpanet-logs-972626128180/ \
  --exclude "*.tmp" --storage-class GLACIER_IR
```

---

## Disaster Recovery

### EFS Backup

Automatic daily backups are enabled. To restore:

```bash
# List recovery points
aws backup list-recovery-points-by-resource \
  --resource-arn <efs-arn>

# Restore from backup
aws backup start-restore-job \
  --recovery-point-arn <point-arn> \
  --metadata file-system-id=<new-fs-id>
```

### S3 Archive

All logs are in S3. To restore:

```bash
# Download all logs
aws s3 sync s3://arpanet-logs-972626128180/ /mnt/arpanet-logs/
```

### Instance Failure

If an instance fails:

```bash
# Terminate failed instance
aws ec2 terminate-instances --instance-ids <failed-id>

# Redeploy stack (creates new instance)
cd /home/whf/brfid.github.io/infra/cdk
cdk deploy -a "python3 app_production.py" ArpanetProductionStack

# EFS and S3 data persist automatically
```

---

## Teardown

### Temporary Shutdown (keeps all data)

```bash
# Stop instances
aws ec2 stop-instances --instance-ids <vax-id> <pdp11-id>

# Costs while stopped: ~$2/month (storage only)
```

### Permanent Deletion

⚠️ **WARNING**: Legacy two-host stack commands below are retained for historical traceability only.
Current lifecycle ownership is in `edcloud`.

```bash
# Current decommission flow (edcloud-managed)
# See: https://github.com/brfid/edcloud/blob/main/SETUP.md

# Legacy examples below were for the retired ArpanetProductionStack model.
```

---

## Next Steps

After deployment:

1. ✅ **Configure PDP-11 logging** (extend arpanet_logging system)
2. ✅ **Test VAX ↔ PDP-11 connectivity** (ping, FTP)
3. ✅ **Verify ARPANET protocol** (IMP routing)
4. ✅ **Set up monitoring alerts** (CloudWatch)
5. ✅ **Document operational procedures**
6. ✅ **Test disaster recovery** (restore from backup)

---

## References

- **Docker compose**: `docker-compose.production.yml`
- **Current platform docs**: `https://github.com/brfid/edcloud/blob/main/README.md`
- **Current setup docs**: `https://github.com/brfid/edcloud/blob/main/SETUP.md`

---

**Estimated Setup Time**: 10-15 minutes
**Estimated Monthly Cost**: $17.90
**Uptime**: Can run 24/7 or stop when not needed
