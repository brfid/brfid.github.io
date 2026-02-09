# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses date-based release headings in `YYYY-DD-MM` format.

## [Unreleased]

### Added
- ARPANET stage scaffold execute-path resilience: one retry on `docker exec` failure.
- Transfer-output classification (`ok`, `empty-output`, `fatal-marker-detected`) with hard fail on non-`ok`.
- Execution attempt breadcrumbs and validation markers in `site/arpanet-transfer.log`.
- Root-level handoff brief for ITS runtime debugging: `LLM-PROBLEM-SUMMARY.md`.

### Changed
- ARPANET stage wraps unexpected exceptions with explicit stage context.
- Documented latest AWS ITS runtime validation outcome (build complete, runtime restart-loop due to simulator/config mismatch markers).

## [0.2.0] - 2026-08-02

### Added
- ARPANET build integration path and Phase 1/2/3 documentation baseline.
- Centralized ARPANET logging package and IMP/1822 parser foundation.
- ARPANET-oriented test coverage for routing and orchestration support scripts.

### Changed
- Refactored project docs/testing workflow to support phased ARPANET transport work.

## [0.1.0] - 2026-25-01

### Added
- First stable VAX pipeline milestone: local VAX stage, landing page integration, manifest generation, CI baseline.

### Changed
- Established YAML-driven resume build flow and typed/tested Python packaging foundation.
