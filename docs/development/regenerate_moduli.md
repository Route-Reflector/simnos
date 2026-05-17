# Regenerating bundled moduli

SIMNOS bundles a Diffie-Hellman Group Exchange (DH-GEX) moduli file at
`simnos/plugins/servers/moduli` so that the paramiko-based SSH server can
support GEX key exchange on hosts that lack a system moduli file (typically
Windows / macOS). This page documents why the file exists, how often it
should be regenerated, and the exact procedure.

## Why SIMNOS bundles moduli

paramiko itself does not ship a moduli file. It expects the host system to
provide one at `/etc/ssh/moduli` or `/usr/local/etc/moduli`, which Windows
and macOS hosts typically do not have. Without a moduli file, paramiko's
GEX server-mode hits a stale-snapshot bug (paramiko issue
[2126](https://github.com/paramiko/paramiko/issues/2126)) which forces
SIMNOS to disable all GEX algorithms server-side as a workaround. Combined
with the SHA-1 KEX removal in paramiko 5.0, this produces an empty KEX
overlap with SHA-1-leaning legacy clients such as
`netmiko.fortinet.FortinetSSH`, leading to deterministic connection
failures on Windows / macOS.

Bundling our own moduli file lets the server advertise `gex-sha256` again
on those platforms, restoring connectivity without re-introducing SHA-1
KEX. See the [follow-up comment on paramiko issue
2126](https://github.com/paramiko/paramiko/issues/2126#issuecomment-4458397596)
for the full root-cause analysis.

### Why not rely on paramiko's bundled moduli?

paramiko does not ship one (verified: no `moduli` file exists inside the
installed paramiko package). By bundling our own, SIMNOS becomes
self-contained on platforms without an OpenSSH server installed.

### Why not copy OpenSSH's openssh-portable moduli directly?

Possible (license is BSD-style, compatible with the SIMNOS MIT license),
but generating our own via `ssh-keygen` gives us:

- A known generation date (recorded in the file by the ssh-keygen `# Time`
  header).
- A clear rotation responsibility (we control when to regenerate).
- Independence from OpenSSH's release cadence.

The cost is just a one-time multi-hour generation on a maintainer machine.

## Note: moduli is public information

DH primes are sent to the client during every KEX, so they are not
secret. OpenSSH itself ships moduli in the
[`openssh-portable`](https://github.com/openssh/openssh-portable)
public repository. Bundling the moduli file in this public repo follows
the same practice — there is no security implication.

## Rotation policy

- **Every 3 years** (next recommended: **2029-05** for the current
  bundle, computed from the ssh-keygen generation timestamp in the first
  column of each moduli line — `YYYYMMDDHHMMSS` format — plus 3 years).
- **Ad-hoc** if a new logjam-class precomputation attack is reported
  against 2048-bit-or-larger DH-GEX.

The rotation cadence is intentionally relaxed — DH primes of 2048 bits
or larger remain outside the practical reach of precomputation attacks,
and SIMNOS is primarily used as a test simulator rather than a
production SSH server. The 3-year baseline mirrors the typical refresh
interval used by major Linux distributions.

## Procedure

Run on a Linux maintainer machine. The `-M screen` step is CPU-bound and
single-threaded. On a physical host the total runtime is in the hours;
inside a VM it may run much longer, so the 3072-bit and 4096-bit steps
are split across multiple parallel `ssh-keygen` processes via
`split -n l/N`. The file is generated once and committed; CI does not
regenerate it.

The current bundle contains 2048-bit, 3072-bit, and 4096-bit primes.
The 4096-bit batch was generated on a Windows host (see the
[Alternative: Windows PowerShell](#alternative-windows-powershell) section
below) because `ssh-keygen -M screen` for 4096-bit candidates is
prohibitively slow inside the VM host used for the 2048/3072 batch.

```bash
# 1. Generate candidates for each bit size (fast — seconds to minutes)
ssh-keygen -M generate -O bits=2048 moduli-2048.candidates
ssh-keygen -M generate -O bits=3072 moduli-3072.candidates
ssh-keygen -M generate -O bits=4096 moduli-4096.candidates

# 2a. Screen the 2048-bit candidates in a single process (~30 min - 3 h)
ssh-keygen -M screen -f moduli-2048.candidates moduli-2048

# 2b. Screen the 3072-bit candidates by splitting the candidate file and
#     running multiple ssh-keygen processes in parallel (one per available
#     CPU). Adjust `N` (= 8 below) to your physical / virtual core count,
#     which you can inspect with `nproc` on Linux.
split -n l/8 moduli-3072.candidates moduli-3072.chunk.
for chunk in moduli-3072.chunk.*; do
  (ssh-keygen -M screen -f "$chunk" "${chunk}.screened") &
done
wait
cat moduli-3072.chunk.*.screened > moduli-3072

# 2c. Same parallel pattern for 4096-bit candidates. Single-process
#     screening for 4096 typically runs 10 hours or more on a VM, so
#     parallel split is strongly recommended (a bare-metal 8-core box
#     finishes the screened batch in roughly 1 hour).
split -n l/8 moduli-4096.candidates moduli-4096.chunk.
for chunk in moduli-4096.chunk.*; do
  (ssh-keygen -M screen -f "$chunk" "${chunk}.screened") &
done
wait
cat moduli-4096.chunk.*.screened > moduli-4096

# 3. Concatenate into the bundled file (file name has no extension,
#    matching the OpenSSH convention)
cat moduli-2048 moduli-3072 moduli-4096 > simnos/plugins/servers/moduli

# 4. Clean up intermediates (`-f` to ignore missing files on partial runs)
rm -f moduli-*.candidates moduli-2048 moduli-3072 moduli-4096 \
      moduli-3072.chunk.* moduli-3072.chunk.*.screened \
      moduli-4096.chunk.* moduli-4096.chunk.*.screened

# 5. Verify (should be a few hundred to a few thousand lines).
# Each line starts with the ssh-keygen generation timestamp in
# YYYYMMDDHHMMSS format, e.g. `20260516054136 2 6 100 2047 2 D5AC...`
wc -l simnos/plugins/servers/moduli
head -1 simnos/plugins/servers/moduli
```

These commands write only to the current directory; the system's
`/etc/ssh/moduli` is not touched and no root privileges are required.

## Alternative: Windows PowerShell

If the maintainer's Linux host is a VM, the 4096-bit screening step
can take 10+ hours. Running directly on a Windows host with PowerShell
7 (using the built-in OpenSSH client) avoids the VM overhead and
finishes much faster — roughly 1 hour for 4096-bit on a bare-metal
8-core machine.

```powershell
# Run from any working directory (writes to cwd only).
# Requires: Windows 10/11 with OpenSSH Client enabled and PowerShell 7+
#          (ForEach-Object -Parallel is unavailable on PowerShell 5.1).

# 1. Generate candidates (single-threaded, ~5-15 min for 4096-bit)
ssh-keygen -M generate -O bits=4096 candidates-4096.txt

# 2. Split candidates into 8 chunks (adjust 8 to your physical core count)
$lines = Get-Content candidates-4096.txt
$chunkSize = [Math]::Ceiling($lines.Count / 8)
0..7 | ForEach-Object {
    $start = $_ * $chunkSize
    $end = [Math]::Min($start + $chunkSize - 1, $lines.Count - 1)
    $lines[$start..$end] | Set-Content "candidates-4096.part$_.txt"
}

# 3. Screen in parallel (-ThrottleLimit = chunk count from step 2)
0..7 | ForEach-Object -Parallel {
    ssh-keygen -M screen -f "candidates-4096.part$_.txt" "moduli-4096.part$_.txt"
} -ThrottleLimit 8

# 4. Merge parts. Set-Content writes CRLF on Windows; the moduli file
#    must be LF-only, so re-write via [IO.File]::WriteAllText.
$content = (0..7 | ForEach-Object { Get-Content "moduli-4096.part$_.txt" -Raw }) -join ""
$content = $content -replace "`r`n", "`n"
[IO.File]::WriteAllText("$pwd\moduli-4096-lf.txt", $content)

# 5. Transfer moduli-4096-lf.txt to the Linux maintainer machine, then
#    concatenate with the existing 2048 / 3072 bundle:
#      cat moduli-4096-lf.txt >> simnos/plugins/servers/moduli
```

Note: ssh-keygen on Windows shares the same `-M generate / -M screen`
flags as the Unix build, so the output format is identical and can be
concatenated directly with batches produced on Linux.

## Verifying the wheel includes the moduli file

After committing the new file, build the wheel locally and confirm the
moduli file is shipped inside it:

```bash
uv build
unzip -l dist/simnos-*.whl | grep moduli
tar tzf dist/simnos-*.tar.gz | grep moduli
```

Both commands should print the moduli path. `uv_build` (current
backend) includes every non-Python file under the package directory by
default, so **no `pyproject.toml` change is needed** for the current
build. The check above exists to catch a future regression in that
default behaviour.

If a future `uv_build` version (or a different backend) ever drops the
file, the fallback is to add an explicit include:

```toml
[tool.uv.build-backend]
source-include = ["simnos/plugins/servers/moduli"]
```

The release CI workflow (`.github/workflows/pypi-publish.yml`) also
asserts the moduli file is present in both the built wheel and sdist
before publishing.

## Commit and PR

- Commit message: `chore: regenerate bundled moduli (#NNN)`
- PR description: record the new "next recommended rotation" date
  (generation date + 3 years).
- Include a brief note of which logjam-class trigger (if any) prompted
  the regeneration.
