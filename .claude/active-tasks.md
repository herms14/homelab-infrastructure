# Active Tasks

> Check this file BEFORE starting any work to avoid conflicts with other sessions.
> Update this file IMMEDIATELY when starting or completing work.

---

## Currently In Progress

*No active tasks*

---

## Recently Completed (Last 24 Hours)

## Discord Bot Reorganization
**Completed**: 2025-12-26 ~22:00
**Session**: MacBook via Tailscale
**Changes**:
- Created Argus bot for container updates (`#container-updates`)
  - Watchtower webhook integration (port 5050)
  - Button-based update approvals
  - Commands: `/check`, `/update`, `/updateall`, `/containers`, `/status`
- Created Chronos bot for project management (`#project-management`)
  - GitLab Boards integration
  - Commands: `/todo`, `/tasks`, `/done`, `/close`, `/board`, `/quick`
- Enhanced Mnemosyne for media downloads (`#media-downloads`)
  - Added: `/availablemovies`, `/availableseries`, `/showlist`
  - Progress notifications at 50%, 80%, 100%
- Fixed channel restriction checking with debug logging
**Files Created**:
- `ansible-playbooks/container-updates/argus-bot.py`
- `ansible-playbooks/container-updates/deploy-argus-bot.yml`
- `ansible-playbooks/project-management/chronos-bot.py`
- `ansible-playbooks/project-management/deploy-chronos-bot.yml`
- `docs/DISCORD_BOTS.md`

## Glance Web & Reddit Page Enhancement
**Completed**: 2025-12-26 ~16:30
**Session**: MacBook via Tailscale
**Changes**:
- Revamped Web page as comprehensive tech news aggregator with 9 collapsible sections
- Added Tech YouTube widget with 7 channels (MKBHD, LTT, Mrwhosetheboss, Dave2D, Austin Evans, JerryRigEverything, Fireship)
- Expanded news sources: The Verge, XDA, TechCrunch, Ars Technica, AWS Blog
- Added categories: Android/Mobile, AI/ML, Cloud, Big Tech, Gaming, PC Builds, Travel
- Updated Reddit Manager with 16 subreddits (added datahoarder, technology, programming, webdev, sysadmin, netsec, gaming, pcmasterrace, buildapc, mechanicalkeyboards)
- Changed Reddit view to "grouped" mode with thumbnails
- Added native Reddit widgets for r/technology, r/programming, r/sysadmin
**Files Created**:
- temp-glance-web-reddit-update.py
- ansible-playbooks/glance/deploy-web-reddit-update.yml
**Files Modified on Server**:
- /opt/glance/config/glance.yml
- /opt/reddit-manager/data/subreddits.json
- /opt/reddit-manager/data/settings.json

## NBA Stats API + Yahoo Fantasy Integration
**Completed**: 2025-12-26 ~14:00
**Session**: MacBook via Tailscale
**Changes**:
- Deployed NBA Stats API to docker-utilities:5060 (fixed port conflict from 5055)
- Fixed ESPN standings URL (v2 endpoint)
- Implemented Yahoo Fantasy OAuth headless flow
- Fixed Yahoo Fantasy API (game ID 466, league key `466.l.12095`)
- Added `/fantasy/matchups` endpoint for weekly matchups
- Added `/fantasy/recommendations` endpoint for player pickup analysis
- Added NBA team logos to games and standings widgets (ESPN CDN)
- Added Sports tab to Glance (8 pages now)
- Created docs/DOCKER_SERVICES.md - comprehensive Docker services inventory
**API Endpoints**:
- `http://192.168.40.10:5060/games` - NBA games with logos
- `http://192.168.40.10:5060/standings` - NBA standings with logos
- `http://192.168.40.10:5060/fantasy` - Fantasy league standings
- `http://192.168.40.10:5060/fantasy/matchups` - Current week matchups
- `http://192.168.40.10:5060/fantasy/recommendations` - Player pickup recommendations
**Files on Server**:
- /opt/nba-stats-api/nba-stats-api.py
- /opt/nba-stats-api/yahoo_fantasy.py
- /opt/nba-stats-api/fantasy_recommendations.py
- /opt/nba-stats-api/data/yahoo_token.json
- /opt/glance/config/glance.yml (Sports tab)

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
- Glance Home, Media, Compute, Storage, Network, and Sports pages are protected - don't modify without permission
- Synology NAS Storage dashboard is protected - UID: `synology-nas-modern`, height: 1350px
- Yahoo Fantasy OAuth token stored at `/opt/nba-stats-api/data/yahoo_token.json` - auto-refreshes
