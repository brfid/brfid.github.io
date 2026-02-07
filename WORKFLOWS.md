# Build & Publish Workflows

This document explains the 4 different build modes and how to use them.

## 🎯 The Four Modes

### Mode 1: Push Without Build
**Use when**: Updating docs, comments, or non-code changes

```bash
git commit -m "Update documentation [skip ci]"
git push
```

**Magic keywords** (in commit message):
- `[skip ci]`
- `[ci skip]`
- `[no ci]`
- `[skip actions]`
- `[actions skip]`

**Result**: Code pushed, no workflows run
**Time**: Instant

---

### Mode 2: Test Only (No Publish)
**Use when**: Developing features, validating changes

```bash
git checkout -b feature/my-feature
git commit -m "Add new feature"
git push origin feature/my-feature
```

**Triggers on**:
- Push to any branch (except `main`)
- Pull requests

**Workflow**: `.github/workflows/test.yml`

**What runs**:
- ✅ Quality checks (ruff, mypy, pytest, pylint, vulture)
- ✅ ARPANET Phase 1 test (VAX + IMP connectivity)
- ✅ Logs captured as artifacts
- ❌ No site generation
- ❌ No publish

**Time**: ~5-7 minutes
**Cost**: Free

---

### Mode 3: Publish Fast (VAX Local)
**Use when**: Quick publishes, minor updates, most releases

```bash
# Quick publish
git tag publish
git push origin publish

# Or with date
git tag publish-$(date +%Y%m%d)
git push origin publish-$(date +%Y%m%d)
```

**Triggers on**:
- Tags: `publish` or `publish-*` (except `publish-arpanet*` and `publish-full*`)

**Workflow**: `.github/workflows/deploy.yml`

**What runs**:
- ✅ Quality checks
- ✅ Site generation with `--vax-mode local` (host compiler)
- ✅ Playwright browser caching (optimized)
- ✅ Deploy to GitHub Pages
- ❌ No ARPANET network

**Time**: ~3-5 minutes (optimized with caching)
**Cost**: Free

---

### Mode 4: Publish Full (ARPANET)
**Use when**: Major releases, demos, maximum authenticity

```bash
# ARPANET publish
git tag publish-arpanet
git push origin publish-arpanet

# Or with date
git tag publish-arpanet-$(date +%Y%m%d)
git push origin publish-arpanet-$(date +%Y%m%d)

# Or using 'full' alias
git tag publish-full
git push origin publish-full
```

**Triggers on**:
- Tags: `publish-arpanet`, `publish-arpanet-*`, `publish-full`, `publish-full-*`

**Workflow**: `.github/workflows/deploy.yml` (ARPANET mode)

**What runs**:
- ✅ Quality checks
- ✅ Start ARPANET network (VAX + IMP containers)
- ✅ Site generation with `--vax-mode arpanet`
- ✅ ARPANET logs captured and published
- ✅ Deploy to GitHub Pages
- ✅ Network diagram included

**Time**: ~10-12 minutes (optimized)
**Cost**: Free (public repo)

---

## 📊 Quick Reference

| Mode | Command | Time | Publishes | ARPANET |
|------|---------|------|-----------|---------|
| 1 | Commit with `[skip ci]` | 0 min | ❌ | ❌ |
| 2 | Push to feature branch | 5-7 min | ❌ | Test only |
| 3 | `git tag publish` | 3-5 min | ✅ | ❌ |
| 4 | `git tag publish-arpanet` | 10-12 min | ✅ | ✅ |

---

## 🚀 Common Workflows

### Daily Development
```bash
# Work on feature branch
git checkout -b feature/new-thing
# ... make changes ...
git commit -m "Add new feature"
git push origin feature/new-thing
# → Mode 2: Tests run automatically
```

### Quick Documentation Update
```bash
git checkout main
git add README.md
git commit -m "Fix typo [skip ci]"
git push
# → Mode 1: No build
```

### Regular Release
```bash
git checkout main
git pull
git tag publish-20260206
git push origin publish-20260206
# → Mode 3: Fast publish (3-5 min)
```

### Special Release (With ARPANET)
```bash
git checkout main
git pull
git tag publish-arpanet-v1.0
git push origin publish-arpanet-v1.0
# → Mode 4: Full ARPANET build (10-12 min)
```

---

## 🎮 Manual Trigger (GitHub UI)

You can also trigger publishes manually:

1. Go to **Actions** tab on GitHub
2. Select **Publish Site** workflow
3. Click **Run workflow**
4. Choose VAX mode:
   - `local` → Fast publish (Mode 3)
   - `arpanet` → ARPANET publish (Mode 4)
5. Click **Run workflow**

---

## 🔍 Viewing Results

### Test Results (Mode 2)
1. Go to **Actions** tab
2. Click on your workflow run
3. Expand **arpanet-phase1-test** job
4. View logs in each step
5. Download artifacts: **arpanet-phase1-test-logs**

### Published Site (Modes 3 & 4)
- **URL**: https://brfid.github.io/
- **ARPANET logs** (Mode 4 only): https://brfid.github.io/arpanet-logs/

---

## ⚙️ Optimizations Applied

### Playwright Caching
- Browsers cached between runs
- **Saves**: ~45 seconds per build

### Conditional ARPANET
- Only starts network in Mode 4
- Mode 3 stays fast with local compilation

### Parallel Jobs (Mode 2)
- Quality checks and ARPANET test run independently
- Can view results separately

---

## 🐛 Troubleshooting

### "Workflow not triggering"
- Check commit message for `[skip ci]` keywords
- Verify tag name matches patterns
- Ensure you pushed the tag: `git push origin <tagname>`

### "ARPANET test failing"
- Check artifacts for logs
- VAX boot can take 60+ seconds
- Network issues may cause timeouts

### "Publish taking too long"
- Use Mode 3 (local) for faster builds
- Mode 4 (ARPANET) intentionally slower for authenticity

### "Want to cancel a running workflow"
- Go to Actions tab
- Click on running workflow
- Click "Cancel workflow" button

---

## 📚 Related Files

- `.github/workflows/test.yml` - Mode 2 (test only)
- `.github/workflows/deploy.yml` - Modes 3 & 4 (publish)
- `.github/workflows/ci.yml` - Existing CI for `main` branch
- `docker-compose.arpanet.phase1.yml` - ARPANET network config
- `arpanet/TESTING-GUIDE.md` - Detailed testing procedures

---

## 🎯 Best Practices

1. **Use Mode 2 for development** - Fast feedback on changes
2. **Use Mode 3 for regular releases** - Keep publish times short
3. **Use Mode 4 sparingly** - Major releases, demos, special occasions
4. **Use Mode 1 for docs** - Skip CI for non-code changes

---

## 💡 Tips

- **Tags are permanent** - Choose names carefully
- **Date tags help** - `publish-20260206` is clear and sortable
- **Check Actions tab** - See all workflow runs and status
- **Download artifacts** - Get detailed logs from test runs
- **Use draft PRs** - Test in Mode 2 before merging

---

**Last Updated**: 2026-02-06
**Workflows Version**: 1.0 (with optimizations)
