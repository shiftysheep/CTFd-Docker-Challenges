# Known Issues

## Active Bugs

- **Challenge modal becomes unclickable after first close**
    - Location: docker_challenges/assets/view.js (lines 8-16, 45-209)
    - Issue: After viewing a challenge modal and closing it (via close button or clicking outside), subsequent challenge clicks do not open modals until page refresh
    - Reproduction:
        1. Navigate to /challenges
        2. Click any challenge to open modal
        3. Launch Docker instance (optional)
        4. Close modal (either close button or click outside)
        5. Attempt to click another challenge - modal does not appear
        6. Refresh page - clicking works again
    - Impact: Critical UX blocker - users cannot navigate between challenges without refresh
    - Workaround: Refresh page after each challenge view
    - Root Cause: **Identified - Two related issues:**
        1. **Timer/Memory Leak**: Alpine.js `containerStatus()` component creates timers (`pollTimeoutId` at line 74, `countdownInterval` at line 165) that are never cleared when modal closes. No cleanup lifecycle hook exists.
        2. **Global State Pollution**: Plugin sets `CTFd._internal.challenge.render = null` (line 14), breaking CTFd's ability to render subsequent challenges after first modal close.
        3. **Missing Modal Lifecycle**: No Bootstrap modal event listeners (`hide.bs.modal`) to trigger cleanup when modal closes.
    - Fix Strategy:
        1. Add Alpine.js cleanup lifecycle (`destroy()` method or `$watch` for modal state)
        2. Clear timers (`clearTimeout(pollTimeoutId)`, `clearTimeout(countdownInterval)`)
        3. Add Bootstrap modal `hide.bs.modal` event listener for cleanup
        4. Restore or properly manage `CTFd._internal.challenge.render` function
    - Effort: 2-3 hours (requires testing modal lifecycle with CTFd core)

- **Docker tag aliasing behavior**
    - Location: docker_challenges/functions/general.py (get_repositories)
    - Issue: Plugin reads first tag in image RepoTags array
    - Impact: Images with multiple tags may not appear correctly in repository dropdown
    - Workaround: Remove unwanted tags, leaving only desired tag as primary
    - Effort: TBD (requires Docker API research)

## ℹ️ Suggestions / Technical Debt

### Architecture

- **Inconsistent frontend technology stack**
    - Issue: jQuery + Alpine.js + vanilla JS hybrid across files
    - Impact: Confusing for contributors, larger bundle size
    - Fix: Commit fully to Alpine.js (aligns with CTFd 3.8.0+ core theme)
    - Effort: 6 hours

## Feature Requests

- Create secrets from CTFd into docker
- Autocreate connection info based on service type
- Dynamic port pointing (avoid hardcoded port ranges)
- Individual secret permissions (per-secret permission control)
- Mark flags as secret (autocreate secrets from flag values)
- WebSocket/Server-Sent Events for real-time status updates (replace polling entirely for better scalability)
- TypeScript migration for type safety
- Database indexes for performance (team_id+challenge_id, timestamp)
