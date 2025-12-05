# Documentation Index

This folder contains detailed technical documentation, analysis reports, and legacy information for the GitHub SBOM API Fetcher project.

---

## Getting Started

**Start here** → [Main README](../README.md) - Current solution documentation

---

## Diagnostic & Troubleshooting Guides

### Active Documentation

| Document | Description |
|----------|-------------|
| **[DEBUG_MAPPING_GUIDE.md](DEBUG_MAPPING_GUIDE.md)** | Generic debugging guide for package mapping failures (works with any repository) |
| **[DEBUG_RUN_ANALYSIS.md](DEBUG_RUN_ANALYSIS.md)** | Complete diagnostic analysis of beatBot test run with --debug flag |
| **[FINAL_DIAGNOSTIC_SUMMARY.md](FINAL_DIAGNOSTIC_SUMMARY.md)** | Comprehensive summary of all findings, fixes, and solutions |
| **[FIXES_SUMMARY.md](FIXES_SUMMARY.md)** | All implemented fixes with before/after comparisons |

### How To Use Debug Mode

1. **Read**: [DEBUG_MAPPING_GUIDE.md](DEBUG_MAPPING_GUIDE.md) - Understand how to use `--debug` flag
2. **Run**: `python -m sbom_fetcher --gh-user USER --gh-repo REPO --debug`
3. **Analyze**: See [DEBUG_RUN_ANALYSIS.md](DEBUG_RUN_ANALYSIS.md) for example analysis
4. **Solutions**: Check [FINAL_DIAGNOSTIC_SUMMARY.md](FINAL_DIAGNOSTIC_SUMMARY.md) for common issues

---

## Technical Analysis

### Package Mapping

| Document | Description |
|----------|-------------|
| **[MAPPER_INVESTIGATION_NEEDED.md](MAPPER_INVESTIGATION_NEEDED.md)** | Investigation of mapper failures and root cause analysis |
| **[UNMAPPED_PACKAGES_LISTING.md](UNMAPPED_PACKAGES_LISTING.md)** | Details on packages that couldn't be mapped and why |

### Key Findings

- **npm metadata issue**: Some packages have GitHub repos but `"repository": null` in npm registry
- **Platform binaries**: @ffmpeg-installer/* packages often lack repository metadata
- **Legacy packages**: Old packages (boolbase, eyes) may not have modern metadata

---

## Validation & Testing

| Document | Description |
|----------|-------------|
| **[VALIDATION_RUN_RESULTS.md](VALIDATION_RUN_RESULTS.md)** | Results from validation runs after implementing fixes |
| **[FINAL_VALIDATION_COMPLETE.md](FINAL_VALIDATION_COMPLETE.md)** | Complete validation after all fixes applied |
| **[FINAL_VALIDATION_REPORT.md](FINAL_VALIDATION_REPORT.md)** | Final validation report with statistics |
| **[PRODUCTION_RUN_SUCCESS.md](PRODUCTION_RUN_SUCCESS.md)** | Production run verification |

---

## Implementation Details

### Refactoring & Architecture

| Document | Description |
|----------|-------------|
| **[REFACTORING_COMPLETE.md](REFACTORING_COMPLETE.md)** | Modular architecture refactoring documentation |
| **[DIRECTORY_STRUCTURE_CORRECTION.md](DIRECTORY_STRUCTURE_CORRECTION.md)** | Output directory structure corrections |
| **[CLEANUP_COMPLETE.md](CLEANUP_COMPLETE.md)** | Codebase cleanup summary |

### Specific Fixes

| Document | Description |
|----------|-------------|
| **[NAMING_FIX_SUMMARY.md](NAMING_FIX_SUMMARY.md)** | SBOM naming convention fixes (branch names) |
| **[NAMING_FIXES_SUMMARY.md](NAMING_FIXES_SUMMARY.md)** | Additional naming corrections |
| **[BRANCH_NAMES_AND_COUNT_EXPLANATION.md](BRANCH_NAMES_AND_COUNT_EXPLANATION.md)** | Explanation of branch name usage and dependency counts |
| **[TERMINOLOGY_AND_BRANCH_ANALYSIS.md](TERMINOLOGY_AND_BRANCH_ANALYSIS.md)** | Terminology updates and branch analysis |
| **[PACKAGE_ECOSYSTEMS_REMOVAL.md](PACKAGE_ECOSYSTEMS_REMOVAL.md)** | Removal of confusing Package Ecosystems section from reports |

---

## Legacy & Historical

### v1.0 HTML Scraper (Deprecated)

| Document | Description |
|----------|-------------|
| **[LEGACY_README.md](LEGACY_README.md)** | Original README with v1.0 HTML scraper documentation |
| **[README_OLD_BACKUP.md](README_OLD_BACKUP.md)** | Backup of README before current rewrite |

### Comparisons

| Document | Description |
|----------|-------------|
| **[BEATBOT_V1_V2_COMPARISON.md](BEATBOT_V1_V2_COMPARISON.md)** | Comparison of v1.0 (HTML scraper) vs v2.0 (API fetcher) |
| **[V1_VS_V2_COMPARISON_REPORT.md](V1_VS_V2_COMPARISON_REPORT.md)** | Detailed performance comparison report |

### Status Reports

| Document | Description |
|----------|-------------|
| **[FINAL_STATUS.md](FINAL_STATUS.md)** | Final status of implementation |

### Historical Run Logs

| Location | Description |
|----------|-------------|
| **[logs/](logs/)** | Historical validation and test run logs from v1/v2 development |

**Log files:**
- `v1_run.log` / `v2_run.log` - Original v1 vs v2 comparison runs
- `beatbot_full_run.log` / `beatbot_final_run.log` - beatBot validation runs
- `debug_validation_run.log` - Debug mode validation with package mapping diagnostics
- `validation_run_post_mapper_fix.log` - Validation after mapper fixes
- `final_validation_run.log` - Final production validation

---

## Quick Navigation

### I need to...

**Debug why packages aren't mapping**
→ [DEBUG_MAPPING_GUIDE.md](DEBUG_MAPPING_GUIDE.md)

**Understand why specific packages failed**
→ [DEBUG_RUN_ANALYSIS.md](DEBUG_RUN_ANALYSIS.md)

**See all fixes that were implemented**
→ [FIXES_SUMMARY.md](FIXES_SUMMARY.md)

**Understand the complete solution**
→ [FINAL_DIAGNOSTIC_SUMMARY.md](FINAL_DIAGNOSTIC_SUMMARY.md)

**Learn about legacy v1.0 tool**
→ [LEGACY_README.md](LEGACY_README.md)

**Compare v1.0 vs current version**
→ [BEATBOT_V1_V2_COMPARISON.md](BEATBOT_V1_V2_COMPARISON.md)

---

## Document Organization

### Current Solution (v2.0+)
- Focus: Modular API-based fetcher with comprehensive diagnostics
- Key docs: DEBUG_MAPPING_GUIDE, DEBUG_RUN_ANALYSIS, FINAL_DIAGNOSTIC_SUMMARY

### Legacy Solution (v1.0)
- Focus: HTML scraper approach (deprecated)
- Key docs: LEGACY_README, BEATBOT_V1_V2_COMPARISON

### Analysis & Fixes
- All implementation details, fixes, validations
- Organized chronologically by development phase

---

## Contributing to Documentation

When adding new documentation:

1. **Place in `docs/` folder** - Keep root directory clean
2. **Update this INDEX** - Add entry to appropriate section
3. **Link from README** - If essential for users
4. **Use descriptive names** - Clear purpose from filename
5. **Include date/context** - Help readers understand timeline

---

**Last Updated**: December 5, 2025  
**Main Documentation**: [README.md](../README.md)
