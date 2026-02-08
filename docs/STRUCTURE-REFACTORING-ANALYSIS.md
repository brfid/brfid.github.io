# Structure & Refactoring Analysis for pdoc Documentation

> Analysis of codebase organization for optimal pdoc-generated documentation. 
> Created while editing is in progress - do not modify files yet.

## Current Package Structure Overview

```
brfid.github.io/
├── resume_generator/          # 15 modules, flat structure
│   ├── __init__.py           # EMPTY __all__ = [] - HIDES everything from pdoc
│   ├── cli.py                # build_html(), build_site(), main()
│   ├── render.py             # load_resume(), render_resume_html(), write_text()
│   ├── landing.py            # build_landing_page()
│   ├── pdf.py                # build_pdf()
│   ├── manpage.py            # parse_brad_roff_summary(), render_brad_man_txt()
│   ├── manifest.py           # build_manifest_entries(), write_manifest()
│   ├── normalize.py          # normalize_resume(), format_date_range()
│   ├── types.py              # TypedDict definitions
│   ├── vax_stage.py          # VaxStageRunner, TelnetSession
│   ├── vax_yaml.py           # build_vax_resume_v1(), emit_vax_yaml()
│   ├── uudecode.py           # decode_uuencode_block(), decode_marked_uuencode()
│   ├── contact_json.py       # generate_contact_json()
│   ├── resume_fields.py      # safe_str(), get_profile_url()
│   ├── vax_arpanet_stage.py  # VaxArpanetStageRunner
│   └── __main__.py           # Entry point
│
├── arpanet_logging/          # Well-organized subpackage structure
│   ├── __init__.py           # Exports: LogEntry, BuildMetadata, LogStorage, etc.
│   ├── core/                 # Subpackage
│   │   ├── __init__.py       # Exports models, storage, parser, collector
│   │   ├── models.py         # LogEntry, BuildMetadata dataclasses
│   │   ├── storage.py        # LogStorage class
│   │   ├── collector.py      # BaseCollector class
│   │   └── parser.py         # BaseParser class
│   ├── collectors/           # Subpackage
│   │   ├── __init__.py       # Registry pattern: get_collector_class()
│   │   ├── vax.py            # VAXCollector
│   │   └── imp.py            # IMPCollector
│   ├── parsers/              # Subpackage
│   │   ├── __init__.py       # BSDParser, ArpanetParser
│   │   ├── bsd.py
│   │   └── arpanet.py
│   └── orchestrator.py       # LogOrchestrator
│
└── arpanet/topology/         # Clean subpackage
    ├── __init__.py           # Exports: PHASE1_TOPOLOGY, HostConfig, etc.
    ├── registry.py           # Dataclass definitions
    ├── definitions.py        # PHASE1_TOPOLOGY, PHASE2_TOPOLOGY
    ├── generators.py         # generate_docker_compose()
    └── cli.py                # arpanet-topology command
```

## Critical Issue: resume_generator __init__.py

**Problem**: `resume_generator/__init__.py` has `__all__ = []`

This means pdoc will show an empty package! The public API functions are hidden.

### Recommended Fix

Update `resume_generator/__init__.py` to export the key public functions:

```python
"""Resume generator package.

This package provides tools for generating a static resume site including:
- HTML/CSS resume pages
- PDF generation via Playwright
- VAX/SIMH manpage generation
- ARPANET topology integration
"""

from resume_generator.cli import build_html, build_site, BuildRequest, VaxOptions
from resume_generator.render import load_resume, render_resume_html, write_text
from resume_generator.landing import build_landing_page
from resume_generator.pdf import build_pdf
from resume_generator.types import Resume, ResumeView
from resume_generator.manifest import write_manifest

# Version info
__version__ = "0.1.0"

__all__ = [
    # Main entry points
    "build_html",
    "build_site", 
    "BuildRequest",
    "VaxOptions",
    # Core functions
    "load_resume",
    "render_resume_html",
    "build_landing_page",
    "build_pdf",
    "write_manifest",
    # Types
    "Resume",
    "ResumeView",
    # Utilities
    "write_text",
]
```

## Structure Comparison

| Aspect | resume_generator | arpanet_logging | arpanet/topology |
|--------|-----------------|-----------------|------------------|
| Organization | Flat (15 modules) | Hierarchical (subpackages) | Hierarchical |
| `__init__.py` | **Empty exports** | Good exports | Good exports |
| pdoc visibility | **Will be empty** | Excellent | Excellent |
| Module count | 15 (crowded) | 3 subpackages | 5 modules |
| Scalability | Hard to navigate | Easy to extend | Easy to extend |

## Refactoring Recommendations (Optional)

### Option 1: Keep Flat, Fix Exports (Minimal Change)

Just fix `__init__.py` exports. Pros: minimal disruption. Cons: 15 modules in one namespace.

### Option 2: Create Subpackages (Better Organization)

Reorganize `resume_generator/` into logical subpackages:

```
resume_generator/
├── __init__.py              # Export main API
├── cli.py                   # Keep at top level
├── types.py                 # Keep at top level
├── builders/                # NEW subpackage
│   ├── __init__.py
│   ├── html.py              # was: render.py (rename for clarity)
│   ├── landing.py           # was: landing.py
│   ├── pdf.py               # was: pdf.py
│   └── manifest.py          # was: manifest.py
├── vax/                     # NEW subpackage (was vax_stage.py, vax_yaml.py, etc.)
│   ├── __init__.py
│   ├── stage.py             # was: vax_stage.py
│   ├── yaml.py              # was: vax_yaml.py
│   ├── decode.py            # was: uudecode.py
│   ├── arpanet_stage.py     # was: vax_arpanet_stage.py
│   └── manpage.py           # was: manpage.py
├── parsers/                 # NEW subpackage
│   ├── __init__.py
│   ├── resume.py            # was: resume_fields.py
│   └── normalize.py         # was: normalize.py
└── utils/                   # NEW subpackage
    ├── __init__.py
    ├── contact.py           # was: contact_json.py
    └── io.py                # write_text() from render.py
```

**Pros:**
- Clear module responsibilities
- Easier to navigate codebase
- Better pdoc organization (navigable subpackages)
- Consistent with `arpanet_logging` pattern

**Cons:**
- Major refactoring (affects imports, tests)
- Need to maintain backward compatibility or update all imports

### Option 3: Hybrid Approach (Recommended for Portfolio)

Create subpackages but keep backward compatibility:

1. Create new subpackages
2. Move code to new locations
3. Keep old modules as thin wrappers that re-export (with deprecation warnings)

Example `vax_stage.py` after move:
```python
# DEPRECATED: This module has moved to resume_generator.vax.stage
# Use: from resume_generator.vax import VaxStageRunner
from resume_generator.vax.stage import VaxStageRunner, VaxStageConfig, TelnetSession
import warnings
warnings.warn(
    "vax_stage.py is deprecated. Use resume_generator.vax.stage",
    DeprecationWarning,
    stacklevel=2
)
```

## Specific Code Refactoring Opportunities

### 1. Extract Common I/O Utilities

`write_text()` in `render.py` and similar utilities could move to a shared `utils/io.py`.

### 2. Consolidate VAX-Related Code

Currently spread across:
- `vax_stage.py` (600+ lines) - Docker/local orchestration
- `vax_yaml.py` - YAML emission for VAX
- `uudecode.py` - UUdecode utilities
- `manpage.py` - roff parsing (technically host-side but VAX-related)

These form a cohesive "VAX stage" subsystem that deserves its own package.

### 3. Separate CLI from Library Code

`cli.py` contains both CLI entry points (`main()`) and library functions (`build_html()`, `build_site()`). Consider:

```python
# api.py - library functions (no argparse)
def build_site(req: BuildRequest) -> None: ...

# cli.py - thin CLI wrapper
def main(argv: list[str] | None = None) -> int:
    # parse args, call api.build_site()
```

This makes the library API cleaner for programmatic use.

### 4. Types Organization

`types.py` is good but could benefit from docstrings on each TypedDict explaining the JSON Resume schema mapping (as noted in improvement plan).

## pdoc Configuration Recommendations

### Module Discovery

Current pdoc command from improvement plan:
```bash
pdoc resume_generator arpanet_logging arpanet -o site/api
```

**Issue**: `arpanet` is not a Python package (it's a directory with docs/configs). Only `arpanet.topology` is a package.

**Corrected command**:
```bash
pdoc resume_generator arpanet_logging arpanet.topology -o site/api
```

### pdoc Template Customizations

Consider custom template to:
- Add link back to main site
- Include mermaid diagram from ARCHITECTURE.md
- Add "Portfolio" badge or header

### Submodules to Hide

Some modules are internal implementation details:
- `resume_generator.contact_json` - internal helper
- `resume_generator.resume_fields` - internal helpers

Can hide with:
```bash
pdoc resume_generator arpanet_logging arpanet.topology \
    --hide resume_generator.contact_json \
    --hide resume_generator.resume_fields \
    -o site/api
```

Or use `__pdoc__` dict in `__init__.py`:
```python
__pdoc__ = {
    "contact_json": False,
    "resume_fields": False,
}
```

## Summary: Priority Order

### Must Fix (pdoc will be broken without)
1. **Fix `resume_generator/__init__.py`** - Add public API exports

### Should Fix (Better documentation)
2. **Correct pdoc command** - Use `arpanet.topology` not `arpanet`
3. **Add `__pdoc__` exclusions** - Hide internal modules

### Nice to Have (Better organization)
4. **Create `resume_generator.vax` subpackage** - Consolidate VAX code
5. **Create `resume_generator.builders` subpackage** - Organize builders
6. **Separate cli.py into api.py + cli.py** - Clean library vs CLI boundary

## Testing Structure After Changes

After refactoring, verify pdoc output:

```bash
# Install pdoc
.venv/bin/pip install pdoc

# Generate docs
.venv/bin/pdoc resume_generator arpanet_logging arpanet.topology -o site/api

# Check output
ls site/api/
# Should show: index.html, resume_generator/, arpanet_logging/, arpanet/

# Preview
cd site/api && python -m http.server 8000
# Navigate: http://localhost:8000/resume_generator/
# Should see: Exported classes/functions listed, not empty
```

---

*Analysis completed while editing in progress*
*Key finding: resume_generator/__init__.py blocks all pdoc visibility*
