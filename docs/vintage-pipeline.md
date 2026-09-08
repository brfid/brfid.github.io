# Retiring the vintage bio pipeline

The website once passed its public name, headline, and summary through two emulated Unix systems before Hugo rendered the landing page. The experiment exercised guest-console orchestration and artifact provenance inside an ordinary publication workflow.

## What ran

The host reduced the public YAML inputs to a fixed printable-ASCII contract. A VAX running 4.3BSD compiled and ran a C program that emitted troff, then encoded that output as a UUCP spool. The host transferred the spool to a PDP-11 running 2.11BSD, where `nroff` rendered the bio. Hugo received the validated text together with a build log and pipeline status.

The machines had separate boot, shell, and shutdown state machines. `pexpect` waited for explicit console markers and guest command results. The host transferred the spool because the selected PDP-11 kernel had no working Ethernet. Each guest had read-only inputs, its own output mount, and an isolated container network.

Deployment selected a source-bound pair of immutable container images. Validation compared the guest output with the original public inputs. A separate fast mode reused a checksummed result while retaining the source run's provenance; a missing or invalid matching artifact stopped publication.

## Why it left the publish path

The pipeline's page-content output was a short bio. Keeping that transformation in publication also required emulator image promotion, console diagnostics, reuse fingerprints, and a retained artifact whose availability expired after 90 days. A routine website edit could therefore depend on the continued operation of both historical guests.

Hugo can render the same canonical public inputs directly. Publication now builds HTML and the real resume PDF together, verifies the resulting artifact, and passes it to Pages without a second build. The [operating guide](../README.md) defines that path.

The [ARPANET Redux project](https://github.com/brfid/arpanet-redux) gives historical-system orchestration its own operating lifecycle. The website and the laboratory can change independently.

## Inspect the original implementation

The final pre-retirement revision is [`d9c6a8a04f9de004c31605d967f7fd40d668289f`](https://github.com/brfid/brfid.github.io/tree/d9c6a8a04f9de004c31605d967f7fd40d668289f). Its [operations guide](https://github.com/brfid/brfid.github.io/blob/d9c6a8a04f9de004c31605d967f7fd40d668289f/docs/integration/INDEX.md), [console implementation reference](https://github.com/brfid/brfid.github.io/blob/d9c6a8a04f9de004c31605d967f7fd40d668289f/docs/integration/operations/PEXPECT-PIPELINE-SPEC.md), source, and tests remain available in Git history.

Those documents describe the environment used at that revision. They do not promise that historical container packages, release assets, or retained Actions artifacts will remain available. The current checkout has no emulator execution or image-promotion workflow.
