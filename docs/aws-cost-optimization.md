# AWS Cost Optimization Analysis

## Current Infrastructure

### EC2 Instance
**Type:** `t3.medium`
- 2 vCPUs, 4 GB RAM
- x86_64 architecture
- **Cost:** $0.0416/hour = $30.37/month (if running 24/7)

### Storage
1. **Root Volume:** 30 GB GP3 EBS
   - Encrypted, deleted on termination
   - **Cost:** $2.40/month

2. **Logs Volume:** 20 GB GP3 EBS
   - Encrypted, **persistent** (survives termination)
   - **Cost:** $1.60/month

### Current Usage Pattern
- **Ephemeral instances** - Created on-demand, destroyed after use
- **Typical usage:** 2 sessions/week, 2 hours each = ~16 hours/month
- **Actual monthly cost:** ~$0.70/month (instance) + $4.00 (storage) = **$4.70/month**

---

## Cost Breakdown

| Resource | Size | Type | Monthly Cost | Notes |
|----------|------|------|--------------|-------|
| **EC2 t3.medium** | 2 vCPU, 4GB | On-demand | $30.37 (if 24/7) | Actual: ~$0.70/mo |
| **Root EBS (GP3)** | 30 GB | Ephemeral | $2.40 | Deleted with instance |
| **Logs EBS (GP3)** | 20 GB | Persistent | $1.60 | ⚠️ **Always charged** |
| **Data Transfer** | - | Out to Internet | ~$0.10 | Minimal usage |
| **Total (typical)** | - | - | **~$4.70/month** | 16 hours/month usage |

---

## 💰 Cost Optimization Opportunities

### 1. **Downsize Instance Type** ⭐⭐⭐ HIGH IMPACT

Your workload (Docker builds, ARPANET testing) doesn't need 4 GB RAM for most tasks.

| Instance Type | vCPU | RAM | Cost/hour | Cost/16hrs | Savings vs Current |
|---------------|------|-----|-----------|------------|-------------------|
| **t3.medium** (current) | 2 | 4 GB | $0.0416 | $0.67 | - |
| **t3.small** | 2 | 2 GB | $0.0208 | $0.33 | **50% ($0.34/mo)** ⭐ |
| **t3.micro** | 2 | 1 GB | $0.0104 | $0.17 | **75% ($0.50/mo)** ⭐⭐ |
| **t4g.small** (ARM) | 2 | 2 GB | $0.0168 | $0.27 | **60% ($0.40/mo)** |

**Recommendation:** Try **t3.small** first
- Same 2 vCPUs (Docker builds won't be slower)
- 2 GB RAM is enough for most builds
- **Saves $0.34/month on compute** (50% reduction)
- If builds succeed, try t3.micro for 75% savings

**Risk:** Low - You can always scale up if builds fail due to memory

---

### 2. **Remove Persistent Logs Volume** ⭐⭐⭐ HIGH IMPACT

The 20 GB logs volume is **persistent** (doesn't delete on termination), costing **$1.60/month continuously**.

**Questions:**
- Do you actually need logs to persist between sessions?
- Are you ever re-attaching this volume to new instances?
- Could logs be stored in cheaper S3 instead?

**Cost if removed:** Save **$1.60/month** (34% of total cost)

**Alternative:** Store logs in S3
- S3 Standard: $0.023/GB-month
- 20 GB = $0.46/month
- **Saves $1.14/month**

**Code change needed:**
```python
# In arpanet_stack.py, remove or comment out:
ec2.BlockDevice(
    device_name="/dev/sdf",
    volume=ec2.BlockDeviceVolume.ebs(
        volume_size=logs_volume_size,
        volume_type=ec2.EbsDeviceVolumeType.GP3,
        delete_on_termination=False,  # ← This makes it persistent
        encrypted=True,
    )
)
```

---

### 3. **Reduce Root Volume Size** ⭐ MEDIUM IMPACT

Current: 30 GB root volume

**Analysis:**
- Ubuntu 22.04: ~4 GB
- Docker + images: ~10-15 GB
- Repository + builds: ~5 GB
- **Total needed: ~20-25 GB**

**Recommendation:** Reduce to **20 GB**
- Still comfortable headroom
- **Saves $0.80/month** (10 GB × $0.08)

**Code change:**
```json
// In cdk.context.json:
{
  "root_volume_size": 20,  // Changed from 30
}
```

---

### 4. **Use Spot Instances** ⭐⭐ MEDIUM-HIGH IMPACT (Advanced)

Spot instances are spare AWS capacity at 50-70% discount.

**Current:** t3.medium on-demand = $0.0416/hour
**Spot:** t3.medium spot = ~$0.0125/hour (70% cheaper)

**Pros:**
- **Massive savings:** $0.50 → $0.15 per 16-hour month
- Same performance
- Good for ephemeral workloads (your use case!)

**Cons:**
- Can be interrupted with 2-minute warning
- Requires CDK code changes
- More complex to manage

**Implementation complexity:** Medium (need to handle interruptions)

---

### 5. **Switch to ARM (t4g instances)** ⭐ MEDIUM IMPACT

AWS Graviton2 (ARM) instances are 20-40% cheaper.

**Current:** t3.medium (x86) = $0.0416/hour
**ARM:** t4g.medium (ARM) = $0.0336/hour (19% cheaper)

**Pros:**
- 19-40% cost savings
- Better performance per dollar
- Native if you develop on ARM (Raspberry Pi)

**Cons:**
- ⚠️ **Your use case needs x86_64!**
- The whole point is testing x86_64 Docker images
- ARM won't help for ARPANET x86 testing

**Recommendation:** ❌ Don't use ARM for this use case

---

## 💵 Optimized Configuration

### Conservative Optimization (Low Risk)

```json
// cdk.context.json
{
  "instance_type": "t3.small",        // ← Changed from t3.medium
  "root_volume_size": 20,             // ← Changed from 30
  "logs_volume_size": 0,              // ← Removed (or use S3)
  // ... rest unchanged
}
```

**Monthly cost:**
- EC2: $0.33 (16 hours × $0.0208)
- Root EBS: $1.60 (20 GB × $0.08)
- Logs EBS: $0.00 (removed)
- **Total: $1.93/month** (was $4.70)
- **Savings: $2.77/month (59% reduction)** ✅

---

### Aggressive Optimization (Higher Risk)

```json
{
  "instance_type": "t3.micro",        // ← Smallest that still has 2 vCPU
  "root_volume_size": 20,
  "logs_volume_size": 0,
}
```

**Monthly cost:**
- EC2: $0.17 (16 hours × $0.0104)
- Root EBS: $1.60
- **Total: $1.77/month** (was $4.70)
- **Savings: $2.93/month (62% reduction)** ✅✅

**Risk:** t3.micro only has 1 GB RAM - builds might fail

---

## 📊 Cost Comparison

| Configuration | Instance | Storage | Monthly Cost | Savings | Risk |
|---------------|----------|---------|--------------|---------|------|
| **Current** | t3.medium | 30+20 GB | **$4.70** | - | - |
| **Conservative** | t3.small | 20 GB | **$1.93** | $2.77 (59%) | ⭐ Low |
| **Aggressive** | t3.micro | 20 GB | **$1.77** | $2.93 (62%) | ⭐⭐ Medium |
| **With Spot** | t3.small spot | 20 GB | **$1.00** | $3.70 (79%) | ⭐⭐⭐ High |

---

## 🎯 Recommended Action Plan

### Phase 1: Low-Hanging Fruit (No Risk)
1. **Remove persistent logs volume** → Save $1.60/month
2. **Reduce root volume to 20 GB** → Save $0.80/month
3. **Test savings:** ~$2.40/month (51% reduction)

### Phase 2: Instance Downsize (Low Risk)
1. **Switch to t3.small** → Save additional $0.34/month
2. **Total savings:** $2.77/month (59% reduction)
3. **Cost:** $1.93/month

### Phase 3: Aggressive Savings (If Builds Work)
1. **Try t3.micro** → Save additional $0.16/month
2. **Total savings:** $2.93/month (62% reduction)
3. **Cost:** $1.77/month

### Phase 4: Advanced (Optional)
1. Research Spot instances for additional 50-70% savings
2. Implement interruption handling
3. Potential cost: ~$1.00/month

---

## 🔍 Detailed Analysis: Why These Savings Work

### Why t3.small is Probably Fine

**Docker builds need:**
- CPU for compilation ✅ (2 vCPU same as t3.medium)
- Disk for layers ✅ (20 GB is enough)
- RAM for build context (2 GB should be OK for your images)

**Your ARPANET images are small:**
- Base Ubuntu/Alpine: ~200 MB
- IMP/PDP10 simulators: ~50 MB
- Total: <500 MB per image

**Docker caching helps:** Layers are reused, reducing memory pressure

### Why Persistent Logs Volume is Wasteful

**It's charged 24/7 whether instance is running or not:**
- 16 hours/month active × $0.0416/hr = $0.67 compute
- 720 hours/month storage × (20 GB × $0.08) = $1.60 storage
- **Storage costs more than compute!**

**Alternative:** Copy logs to S3 before destroying instance:
```bash
# In user_data.sh or manual SSH:
aws s3 cp /mnt/logs/ s3://my-bucket/arpanet-logs/ --recursive
```

---

## 🧪 Testing the Changes

### 1. Update Configuration
```bash
cd test_infra/cdk
vim cdk.context.json

# Change these lines:
  "instance_type": "t3.small",
  "root_volume_size": 20,
  # Remove logs_volume_size or set to 0
```

### 2. Deploy and Test
```bash
make aws-up
make aws-ssh

# On the instance:
cd brfid.github.io
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain

# Check memory usage during build:
free -h
docker stats
```

### 3. If Build Fails (Out of Memory)
```bash
# Revert to t3.medium
make aws-down
# Edit cdk.context.json → "instance_type": "t3.medium"
make aws-up
```

---

## 💡 Other Cost Considerations

### Current Monthly Cost is Already Low!
At $4.70/month, you're spending **$56/year**. Even with optimizations ($1.77/month = $21/year), you're saving ~$35/year.

**Is it worth optimizing?**
- ✅ Good learning exercise
- ✅ Demonstrates cost awareness
- ✅ Scales if usage increases
- ⚠️ Small absolute savings ($2-3/month)

### Compared to Alternatives

| Option | Monthly Cost | Pros | Cons |
|--------|-------------|------|------|
| **Current AWS** | $4.70 | On-demand, easy | Ongoing costs |
| **Optimized AWS** | $1.77 | Cheaper, still easy | Still ongoing |
| **GitHub Actions** | $0 (free tier) | Free for public repos | Limited minutes |
| **Local x86 VM** | $0 | No cloud costs | Need x86 hardware |

**Your current setup is already cost-effective for the use case!**

---

## 📋 Implementation Checklist

- [ ] Backup any important logs from persistent volume (if exists)
- [ ] Update `cdk.context.json`:
  - [ ] Change `instance_type` to `t3.small`
  - [ ] Change `root_volume_size` to `20`
  - [ ] Remove or zero `logs_volume_size`
- [ ] Test build on t3.small
- [ ] Monitor memory usage during builds
- [ ] If successful, try t3.micro
- [ ] Document new configuration
- [ ] Update README.md with new cost estimates

---

## Summary

**Current:** $4.70/month
**Optimized:** $1.93/month (conservative) or $1.77/month (aggressive)
**Savings:** $2.77-$2.93/month (59-62% reduction)

**Key changes:**
1. ⭐⭐⭐ Remove persistent logs volume → $1.60/month saved
2. ⭐⭐⭐ Downsize to t3.small → $0.34/month saved
3. ⭐ Reduce root volume to 20 GB → $0.80/month saved

**Lowest risk, highest impact: Remove logs volume and try t3.small**

Would you like me to implement these changes?
