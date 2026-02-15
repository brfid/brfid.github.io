# ARPANET Production Infrastructure

---
**⚠️ DEPRECATED (2026-02-14)**

This CDK stack (ArpanetProductionStack) has been destroyed and replaced with edcloud backend.
See `edcloud/MIGRATION.md` and `edcloud/README.md` for current deployment.

Retained for historical reference only.

---

Permanent two-machine setup with shared EFS logging.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Account                          │
│                                                             │
│  ┌─────────────────────┐      ┌─────────────────────┐     │
│  │   VAX Host          │      │   PDP-11 Host       │     │
│  │   t3.micro          │      │   t3.micro          │     │
│  │   $7.50/mo          │      │   $7.50/mo          │     │
│  │                     │      │                     │     │
│  │   Root: 8GB gp3     │      │   Root: 8GB gp3     │     │
│  │   $0.64/mo          │      │   $0.64/mo          │     │
│  └──────────┬──────────┘      └──────────┬──────────┘     │
│             │                            │                 │
│             └────────────┬───────────────┘                 │
│                          │                                 │
│                   ┌──────▼──────┐                          │
│                   │  EFS Volume  │                         │
│                   │  Shared Logs │                         │
│                   │  ~$0.73/mo   │                         │
│                   │              │                         │
│                   │ Lifecycle:   │                         │
│                   │ 7d → IA tier │                         │
│                   └──────┬───────┘                         │
│                          │                                 │
│                   ┌──────▼───────┐                         │
│                   │  S3 Bucket   │                         │
│                   │  Log Archive │                         │
│                   │  ~$0.02/mo   │                         │
│                   │              │                         │
│                   │ 30d → Glacier│                         │
│                   └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Cost Breakdown

| Resource | Specification | Monthly Cost |
|----------|---------------|--------------|
| VAX EC2 | t3.micro | $7.50 |
| PDP-11 EC2 | t3.micro | $7.50 |
| VAX root volume | 8GB gp3 | $0.64 |
| PDP-11 root volume | 8GB gp3 | $0.64 |
| EFS logs (shared) | ~10GB with IA | $0.73 |
| S3 archive | ~1GB (minimal) | $0.02 |
| **Total** | | **~$17.90/month** |

## Deployment

### Prerequisites

```bash
cd /home/whf/brfid.github.io
source .venv/bin/activate
cd infra/cdk
```

### Deploy Production Stack

```bash
# Synthesize to check for errors
cdk synth -a "python3 app_production.py"

# Deploy (creates both instances + EFS + S3)
cdk deploy -a "python3 app_production.py" ArpanetProductionStack

# Outputs will show:
# - VaxPublicIP
# - Pdp11PublicIP
# - EfsFileSystemId
# - LogArchiveBucket
# - SSH commands
```

### Post-Deployment

```bash
# Get instance IPs from output
VAX_IP=$(aws cloudformation describe-stacks \
  --stack-name ArpanetProductionStack \
  --query 'Stacks[0].Outputs[?OutputKey==`VaxPublicIP`].OutputValue' \
  --output text)

PDP11_IP=$(aws cloudformation describe-stacks \
  --stack-name ArpanetProductionStack \
  --query 'Stacks[0].Outputs[?OutputKey==`Pdp11PublicIP`].OutputValue' \
  --output text)

# SSH to instances (wait ~5 min for user data to complete)
ssh ubuntu@$VAX_IP
ssh ubuntu@$PDP11_IP

# Verify EFS mounted
df -h | grep arpanet-logs
ls -la /mnt/arpanet-logs
```

## Log Storage Structure

### On EFS (`/mnt/arpanet-logs/`)

```
/mnt/arpanet-logs/
├── vax/
│   ├── boot.log          # VAX boot logs
│   ├── network.log       # VAX network logs
│   └── arpanet.log       # ARPANET protocol logs
├── pdp11/
│   ├── boot.log          # PDP-11 boot logs
│   ├── network.log       # PDP-11 network logs
│   └── arpanet.log       # ARPANET protocol logs
└── shared/
    ├── orchestrator.log  # Multi-host orchestration
    └── pipeline.log      # Build pipeline logs
```

### Lifecycle

```
Day 0-7:   Files on EFS Standard tier ($0.30/GB-month)
Day 8+:    Files auto-move to EFS-IA tier ($0.016/GB-month)
Daily:     Files sync to S3 (arpanet-logs-<account>)
Day 30+:   S3 files move to Glacier IR ($0.004/GB-month)
```

## Docker Compose Integration

### Update docker-compose for production

```yaml
version: '3.8'

services:
  vax:
    # ... existing config ...
    volumes:
      - /mnt/arpanet-logs/vax:/var/log/arpanet

  pdp11:
    # ... existing config ...
    volumes:
      - /mnt/arpanet-logs/pdp11:/var/log/arpanet
```

## Accessing Logs

### Real-time (SSH to instance)

```bash
# Tail VAX logs
ssh ubuntu@$VAX_IP
tail -f /mnt/arpanet-logs/vax/boot.log

# Tail PDP-11 logs
ssh ubuntu@$PDP11_IP
tail -f /mnt/arpanet-logs/pdp11/boot.log

# View all logs (either instance)
cd /mnt/arpanet-logs
tree
```

### Historical (S3)

```bash
# List archived logs
aws s3 ls s3://arpanet-logs-972626128180/ --recursive

# Download specific day
aws s3 cp s3://arpanet-logs-972626128180/vax/2026-02-01-boot.log.gz .
gunzip 2026-02-01-boot.log.gz
less 2026-02-01-boot.log
```

## Monitoring

### Check EFS Usage

```bash
# On either instance
df -h /mnt/arpanet-logs

# Detailed breakdown
du -sh /mnt/arpanet-logs/*
```

### Check S3 Archive Size

```bash
aws s3 ls s3://arpanet-logs-972626128180/ --recursive --summarize
```

### Check Instance Status

```bash
# Via AWS CLI
aws ec2 describe-instances \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=ArpanetProductionStack" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]' \
  --output table
```

## Maintenance

### Rotate Logs Manually

```bash
# On instance
cd /mnt/arpanet-logs
find . -name "*.log" -mtime +7 -exec gzip {} \;
```

### Force S3 Sync

```bash
# On instance
sudo /etc/cron.daily/arpanet-log-sync
```

### Clean Up Old Logs

```bash
# Delete local logs older than 30 days (they're in S3)
find /mnt/arpanet-logs -name "*.log.gz" -mtime +30 -delete
```

## Disaster Recovery

### EFS Backups

EFS has automatic daily backups enabled. To restore:

```bash
aws backup list-recovery-points-by-resource \
  --resource-arn arn:aws:elasticfilesystem:us-east-1:972626128180:file-system/fs-XXXXX
```

### S3 Archive

Logs are redundantly stored in S3. To recover:

```bash
aws s3 sync s3://arpanet-logs-972626128180/ /mnt/arpanet-logs/ --exclude "*"
```

## Scaling

### Increase EFS Size

No action needed - EFS auto-scales and you pay for what you use.

### Increase Instance Size

```python
# In arpanet_production_stack.py, change:
instance_type=ec2.InstanceType.of(
    ec2.InstanceClass.BURSTABLE3,
    ec2.InstanceSize.SMALL,  # Changed from MICRO
),

# Redeploy
cdk deploy -a "python3 app_production.py" ArpanetProductionStack
```

### Add More Instances

1. Add new instance in `arpanet_production_stack.py`
2. Mount same EFS volume
3. Create new log directory: `/mnt/arpanet-logs/pdp8/`
4. Redeploy stack

## Teardown

### Temporary Shutdown (keeps data)

```bash
# Stop instances (no hourly charges)
aws ec2 stop-instances --instance-ids <vax-id> <pdp11-id>

# EFS and S3 still incur storage charges (~$1/month)
```

### Permanent Deletion

```bash
# WARNING: This deletes everything except EFS and S3 (RemovalPolicy.RETAIN)
cdk destroy -a "python3 app_production.py" ArpanetProductionStack --force

# Manually delete EFS if needed
aws efs delete-file-system --file-system-id fs-XXXXX

# Manually delete S3 if needed
aws s3 rb s3://arpanet-logs-972626128180 --force
```

## Troubleshooting

### EFS Not Mounting

```bash
# Check security group allows NFS (port 2049)
sudo mount -t efs fs-XXXXX:/ /mnt/arpanet-logs

# Check efs-utils installed
dpkg -l | grep amazon-efs-utils

# Check logs
sudo journalctl -u efs-mount
```

### Docker Can't Write to Logs

```bash
# Fix permissions
sudo chown -R ubuntu:docker /mnt/arpanet-logs
sudo chmod -R 775 /mnt/arpanet-logs
```

### S3 Sync Not Working

```bash
# Check IAM role
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://arpanet-logs-972626128180/

# Check cron
sudo cat /etc/cron.daily/arpanet-log-sync
sudo run-parts --test /etc/cron.daily
```

## Cost Optimization Tips

1. **Stop instances when not in use**: Saves ~$15/month
2. **Use Spot Instances**: Save ~70% (but can be interrupted)
3. **Delete old S3 archives**: Glacier after 30 days is cheap enough
4. **Monitor EFS usage**: Should stay under 10GB for logs
5. **Compress logs**: gzip reduces size 80-90%

## Security

- ✅ EFS encrypted at rest
- ✅ S3 encrypted at rest
- ✅ IAM roles (no hardcoded credentials)
- ✅ Security groups restrict access
- ✅ SSH key required for access
- ✅ Daily backups enabled

## References

- CDK Documentation: https://docs.aws.amazon.com/cdk/
- EFS Pricing: https://aws.amazon.com/efs/pricing/
- S3 Storage Classes: https://aws.amazon.com/s3/storage-classes/
- t3.micro Specs: https://aws.amazon.com/ec2/instance-types/t3/
