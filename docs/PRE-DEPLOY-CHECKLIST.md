# Pre-Deploy Checklist

What needs to be done before pushing to GitHub.

## ✅ Completed (Ready to Deploy)

### Code Changes
- [x] Logging scripts enhanced
  - `scripts/arpanet-log.sh` - Renamed from vintage-log.sh, fallback added
  - `scripts/vax-build-and-encode.sh` - Enhanced with tool evidence
  - `scripts/pdp11-validate.sh` - Enhanced with tool evidence
  - `scripts/extract-console-logs.py` - Log extraction from console captures
  - `scripts/generate-build-info.py` - Already existed

### Workflow Updates
- [x] `.github/workflows/deploy.yml` updated
  - Stage 1: Console-based VAX build (executes in BSD)
  - Stage 2: Console transfer with logging script upload
  - Stage 3: PDP-11 validation with log extraction
  - Log extraction from console captures to EFS

### Real Logs
- [x] Retrieved from `build-20260214-121649`
  - `site/build-logs/VAX.log` (25 lines) - Real K&R C compilation
  - `site/build-logs/COURIER.log` (12 lines) - Console transfer
  - `site/build-logs/GITHUB.log` (9 lines) - Orchestration
  - `site/build-logs/merged.log` (46 lines) - Complete timeline
  - `site/build-logs/PDP11.log` (placeholder)

### Documentation
- [x] `docs/LOGS-STATUS.md` - Log analysis and locations
- [x] `docs/MANUAL-BUILD-PROCEDURE.md` - How to run builds
- [x] `docs/integration/EXPECTED-LOG-FORMAT.md` - Format spec and examples
- [x] `STATUS.md` updated with logging architecture
- [x] Example logs: `site/build-logs/*.log.example`

### Templates
- [x] `templates/build-info-widget.html` - Webpage widget ready

### Commits
- [x] `5a58852` - Logging overhaul
- [x] `dd58356` - Log examples & templates
- [x] `c45ac69` - STATUS update
- [x] `31a3048` - Real logs added
- [x] `9bef532` - Manual build procedure
- [x] `4f3c29f` - Logs status doc

---

## ⚠️ Optional Enhancements (Can Deploy Without)

### Task #7: Enhanced Logging Build
**Status**: In progress, not blocking

**What it adds:**
- Vintage tool evidence with dates: "cc from 7 June 1986"
- Binary timestamps: "dated Jun  7  1986"
- Tool sizes: uuencode, uudecode, nroff
- Complete PDP-11 validation logs

**Current**: Basic logs show real compilation without enhanced proof
**Impact**: Webpage can launch with current logs, enhance later

**How to complete:**
1. Run GitHub Actions: `git tag publish-vax-test && git push --tags`
2. Wait for workflow completion
3. Retrieve enhanced logs from EFS
4. Replace `site/build-logs/*.log` with new versions
5. Commit and redeploy

---

## ❌ Required Before Deploy

### 1. Webpage Integration
**Status**: NOT DONE

**Need to:**
- Add build info widget to `site/index.html`
- Link to log files for download
- Style the widget (CSS already in template)
- Test display locally

**Files to modify:**
- `site/index.html` - Add widget HTML
- Copy CSS from `templates/build-info-widget.html`

**Acceptance:**
- Build info section visible on page
- Links to logs work
- Responsive on mobile

### 2. Remove Example Files (Optional)
**Status**: Can keep or remove

**Example files created:**
- `site/build-logs/VAX.log.example`
- `site/build-logs/PDP11.log.example`

**Decision needed:**
- Keep as reference? (yes - good for docs)
- Remove before deploy? (no - they show target format)

### 3. Test Workflow (Recommended)
**Status**: NOT TESTED

**Why test:**
- Workflow heavily modified
- Console automation new
- Log extraction new
- Want to verify before production

**How to test:**
- Use workflow dispatch or tag
- Monitor GitHub Actions run
- Check for errors
- Verify logs generated

**Risk if skip:**
- First deploy might fail
- No logs generated
- Manual debugging needed

---

## 🚀 Deployment Path

### Option A: Deploy Now (Basic Logs)
**Fast path - ready today:**

1. ✅ Code/docs committed
2. ✅ Real logs present
3. ❌ Add webpage widget (30 min)
4. ⚠️ Skip workflow test (risky)
5. 🚀 Push to GitHub

**Result:** Working site with real logs, basic evidence

### Option B: Deploy with Enhanced Logs
**Complete path - need build run:**

1. ✅ Code/docs committed
2. ❌ Run enhanced build (Task #7)
3. ❌ Add webpage widget
4. ⚠️ Test workflow
5. 🚀 Push to GitHub

**Result:** Working site with full vintage tool proof

### Option C: Deploy & Enhance Later
**Recommended - ship fast, iterate:**

1. ✅ Code/docs committed
2. ✅ Real logs present
3. ❌ Add webpage widget (30 min)
4. 🚀 Push to GitHub (v1)
5. ⏭️ Run Task #7 later
6. ⏭️ Update logs
7. 🚀 Push update (v2)

**Result:** Quick launch, enhance with proof later

---

## Summary

### Blocking (Must Do)
- [ ] **Webpage widget integration** (30 min work)
  - Edit `site/index.html`
  - Add build info section
  - Link to logs

### Non-Blocking (Can Do Later)
- [ ] **Enhanced logging build** (Task #7)
  - Current logs are real, just basic
  - Enhanced version adds vintage tool proof
  - Can ship without, update later

- [ ] **Workflow test run**
  - Recommended but not required
  - First deploy will test it anyway
  - Can fix issues post-deploy

### Ready Now
- ✅ All code changes committed
- ✅ Real build logs present
- ✅ Documentation complete
- ✅ Templates ready

### Time Estimate
- **Minimum to deploy:** 30 minutes (webpage integration only)
- **With workflow test:** 2 hours (test + fix issues)
- **With enhanced logs:** 4+ hours (debug console automation)

---

## Recommendation

**Ship Option C:**
1. Add webpage widget integration (30 min)
2. Commit and push to GitHub
3. Site goes live with real logs
4. Run Task #7 in background
5. Update with enhanced logs later

**Why:**
- Unblocks webpage deployment
- Real logs already demonstrate authenticity
- Enhanced proof is nice-to-have, not must-have
- Can iterate after launch
