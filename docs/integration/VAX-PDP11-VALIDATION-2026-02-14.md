# VAX → PDP-11 End-to-End Validation

**Date**: 2026-02-14
**Status**: Core mechanism validated, full pipeline pending

---

## What Was Validated

### 1. AWS Infrastructure ✅
- Both instances running:
  - VAX: 98.81.160.128 (i-090040c544bb866e8)
  - PDP-11: 52.55.82.23 (i-071ab53e735109c59)
- Shared EFS mounted at `/mnt/arpanet-logs/`
- Cost: ~$0.60/day (~$17.90/month)

### 2. Container Status ✅
- `arpanet-vax` running on VAX instance
  - Ports: 21 (FTP), 23 (telnet), 2323 (console)
- `arpanet-pdp11` running on PDP-11 instance
  - Ports: 21 (FTP), 23 (telnet), 2327 (console)

### 3. Console Access Mechanism ✅
- Screen + telnet works to access BSD inside SIMH
- Tested via AWS host:
  ```bash
  ssh -i ~/.ssh/arpanet-temp.pem ubuntu@98.81.160.128
  screen -S vax-build telnet localhost 2323
  ```
- Successfully sent commands and received output

### 4. File Upload via Console (Heredoc) ✅
- Tested uploading small file via console:
  ```bash
  cat > /tmp/test.txt << ENDOFFILE
  test line 1
  test line 2
  test line 3
  ENDOFFILE
  ```
- File was created successfully in BSD /tmp

### 5. VAX BSD Tools ✅
- Vintage compiler confirmed at `/bin/cc`
- Version: 4.3 BSD UNIX
- Ready for K&R C compilation

### 6. PDP-11 Status ✅
- PDP-11 booted and ready
- /usr filesystem auto-mounted via boot wrapper
- Tools available: uuencode, uudecode, nroff

---

## Current State

### Files Available
- Local: `vax/bradman.c` (1037 lines)
- Local: `build/vax/resume.vax.yaml`
- AWS VAX container: `/tmp/` has test.txt
- AWS PDP-11: waiting for transferred file

### Key Finding: /machines Not Mounted in BSD
The `/machines` directory (from docker volume mount) is NOT accessible inside BSD. Files must be uploaded via console heredoc method.

This is why the console upload scripts exist - they're the correct approach for getting files into BSD.

---

## Validated Approach

### Step 1: Upload Files via Console
Use `scripts/vax-console-upload.sh` to upload files to BSD /tmp:
```bash
./scripts/vax-console-upload.sh vax/bradman.c /tmp/bradman.c localhost
./scripts/vax-console-upload.sh build/vax/resume.vax.yaml /tmp/resume.vax.yaml localhost
```

**Timing**: ~2-3 minutes per 1000 lines

### Step 2: Build on VAX
Use `scripts/vax-console-build.sh` to compile and generate manpage:
```bash
./scripts/vax-console-build.sh <build-id> 98.81.160.128
```

This runs inside BSD with vintage tools.

### Step 3: Transfer to PDP-11
Use console transfer or EFS:
- Console: uuencode output, type to PDP-11 console
- EFS: Copy to shared storage, copy to PDP-11

### Step 4: Validate on PDP-11
Use `scripts/pdp11-validate.sh`:
```bash
./scripts/pdp11-validate.sh <build-id>
```

---

## What Works

1. ✅ Console access via screen+telnet
2. ✅ File upload via heredoc (tested with small file)
3. ✅ Vintage compiler (`/bin/cc`) available
4. ✅ PDP-11 booted with /usr mounted
5. ✅ Both systems accessible on network

## What's Next

1. Complete full file upload (bradman.c + resume.vax.yaml)
2. Run VAX build via console
3. Transfer encoded output to PDP-11
4. Run PDP-11 validation
5. Verify logs captured in EFS
6. Document complete process

---

## Scripts Involved

- `scripts/vax-console-upload.sh` - Upload files via console heredoc
- `scripts/vax-console-build.sh` - Build inside BSD (compile + generate + encode)
- `scripts/pdp11-validate.sh` - Validate on PDP-11 (decode + render)
- `scripts/vintage-log.sh` - Logging to EFS

---

## Key Finding: Container vs BSD Filesystem Separation

**CRITICAL**: The docker container's filesystem is COMPLETELY SEPARATE from BSD's filesystem!

- Container's `/home/` → BSD sees its own `/home/` (different disk ra0g)
- Container's `/tmp/` → BSD sees its own `/tmp/` (in RAM, cleared on boot!)
- Container's `/machines/` → NOT accessible in BSD at all

**Proof**:
```
# Container sees:
docker exec arpanet-vax ls -la /home/
# -rw-r--r-- bradman.c (files present)

# BSD sees:
ls -la /home/
# only lost+found/ (different filesystem!)
```

**Solution**: Console upload is the ONLY way to get files into BSD.
- /tmp is cleared on boot ("clearing /tmp")
- Use /home or /usr/src for persistent storage in BSD

## Notes

- The console upload scripts are the CORRECT approach - container file systems are separate from BSD
- The docker volume mounts (/machines, /var/log/arpanet) are NOT accessible from inside BSD
- Files must be transferred character-by-character via console
- This is by design - ensures vintage toolchain is actually used
