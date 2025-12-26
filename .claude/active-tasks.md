# Active Tasks

> Check this file BEFORE starting any work to avoid conflicts with other sessions.
> Update this file IMMEDIATELY when starting or completing work.

---

## Currently In Progress

<!--
When starting a task, add an entry here:

## [Task Name]
**Started**: YYYY-MM-DD HH:MM
**Session**: [brief identifier]
**Status**: In Progress
**Working On**: [current step]
**Files Being Modified**:
- file1.md
- file2.yml
-->

*No active tasks*

---

## Recently Completed (Last 24 Hours)

## Synology NAS Storage Dashboard - Protected
**Completed**: 2025-12-25 20:45
**Changes**:
- Created modern Synology NAS dashboard for Storage page
- 6 disk health stat tiles (4 HDDs green, 2 M.2 SSDs purple)
- Summary stats: Uptime, Total/Used Storage, CPU %, Memory %
- Disk temperatures bargauge with gradient coloring
- CPU and Memory time series charts
- Storage Consumption Over Time (7-day window)
- Fixed memory unit display (changed from `deckbytes` to `kbytes`)
- Iframe height: 1350px
- **PROTECTED** - Do not modify without explicit user permission
**Files Modified**:
- temp-synology-nas-dashboard.json
- ansible-playbooks/monitoring/deploy-synology-nas-dashboard.yml
**Documentation Updated**:
- .claude/context.md, .claude/conventions.md, docs/GLANCE.md, claude.md, CHANGELOG.md, session-log.md
- GitHub Wiki: Glance-Dashboard.md
- Obsidian: 23 - Glance Dashboard.md

## Container Status Dashboard - Protected
**Completed**: 2025-12-25 16:30
**Changes**:
- Fixed "No data" and "Too many points" issues
- Added Container Issues table for stopped/restarted containers
- Deployed version 6 of dashboard to Grafana
- Iframe height: 1250px
- **PROTECTED** - Do not modify without explicit user permission
**Files Modified**:
- temp-container-status-fixed.json
- ansible-playbooks/monitoring/deploy-container-status-dashboard.yml
**Documentation Updated**:
- .claude/context.md, .claude/conventions.md, docs/GLANCE.md, claude.md, CHANGELOG.md

## Tailscale Documentation + CLAUDE.md Restructure
**Completed**: 2025-12-25 14:45
**Changes**:
- Added Tailscale remote access to all docs (CLAUDE.md, NETWORKING.md, wiki, Obsidian)
- Created `.claude/` directory structure for multi-session workflow
- Split CLAUDE.md into focused context files
**Files Modified**:
- claude.md (refactored)
- docs/NETWORKING.md
- Proxmox-TerraformDeployments.wiki/Network-Architecture.md
- Obsidian: 01 - Network Architecture.md
- .claude/context.md (new)
- .claude/active-tasks.md (new)
- .claude/session-log.md (new)
- .claude/conventions.md (new)

---

## Interrupted Tasks (Need Resumption)

<!--
If a task was interrupted (tokens ran out, user stopped, etc.), move it here:

## [Task Name]
**Interrupted**: YYYY-MM-DD HH:MM
**Reason**: Tokens exhausted / User stopped / Error
**Completed Steps**:
1. Step that was done
2. Another step done
**Remaining Steps**:
1. What still needs to be done
2. Another pending step
**Resume Instructions**: Specific guidance for picking up this task
**Context**: Any important state or decisions made
-->

*No interrupted tasks*

---

## Notes for Next Session

<!--
Leave notes here for future sessions:
- Pending decisions
- Things to watch out for
- User preferences discovered
-->

- User prefers documentation updates to happen incrementally, not at the end
- Multiple Claude instances may run in parallel - always check active-tasks first
- Glance Home, Media, Compute, and Storage pages are protected - don't modify without permission
- Synology NAS Storage dashboard is protected - UID: `synology-nas-modern`, height: 1350px
