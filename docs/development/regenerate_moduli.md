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

- **Every 3 years** (next recommended: YYYY-MM, computed as the file's
  ssh-keygen `# Time` header + 3 years).
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
inside a VM it may run much longer, so the 3072-bit step is split across
multiple parallel `ssh-keygen` processes via `split -n l/N`. The file is
generated once and committed; CI does not regenerate it.

The current bundle contains 2048-bit and 3072-bit primes. 4096-bit primes
are not bundled (deferred — see the design doc Notes § for the rationale
and the follow-up chore PR to add them).

```bash
# 1. Generate candidates for each bit size (fast — seconds to minutes)
ssh-keygen -M generate -O bits=2048 moduli-2048.candidates
ssh-keygen -M generate -O bits=3072 moduli-3072.candidates

# 2a. Screen the 2048-bit candidates in a single process (~30 min - 3 h)
ssh-keygen -M screen -f moduli-2048.candidates moduli-2048

# 2b. Screen the 3072-bit candidates by splitting the candidate file and
#     running multiple ssh-keygen processes in parallel (one per available
#     CPU). Adjust `N` to your physical / virtual core count.
split -n l/8 moduli-3072.candidates moduli-3072.chunk.
for chunk in moduli-3072.chunk.*; do
  (ssh-keygen -M screen -f "$chunk" "${chunk}.screened") &
done
wait
cat moduli-3072.chunk.*.screened > moduli-3072

# 3. Concatenate into the bundled file (file name has no extension,
#    matching the OpenSSH convention)
cat moduli-2048 moduli-3072 > simnos/plugins/servers/moduli

# 4. Clean up intermediates
rm moduli-*.candidates moduli-2048 moduli-3072 moduli-3072.chunk.*

# 5. Verify (should be a few hundred to a few thousand lines)
wc -l simnos/plugins/servers/moduli
head -1 simnos/plugins/servers/moduli   # confirm the "# Time" header is present
```

These commands write only to the current directory; the system's
`/etc/ssh/moduli` is not touched and no root privileges are required.

## Verifying the wheel includes the moduli file

After committing the new file, build the wheel locally and confirm the
moduli file is shipped inside it:

```bash
uv build
unzip -l dist/simnos-*.whl | grep moduli
tar tzf dist/simnos-*.tar.gz | grep moduli
```

If the file is missing, add an explicit include in `pyproject.toml`:

```toml
[tool.uv.build-backend]
source-include = ["simnos/plugins/servers/moduli"]
```

The release CI workflow also asserts the moduli file is present in the
built wheel before publishing.

## Commit and PR

- Commit message: `chore: regenerate bundled moduli (#NNN)`
- PR description: record the new "next recommended rotation" date
  (generation date + 3 years).
- Include a brief note of which logjam-class trigger (if any) prompted
  the regeneration.
