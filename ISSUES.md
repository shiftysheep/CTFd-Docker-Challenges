# Known Issues

## Active Bugs

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

- Autocreate connection info based on service type
- Dynamic port pointing (avoid hardcoded port ranges)
- Individual secret permissions (per-secret permission control)
- Mark flags as secret (autocreate secrets from flag values)
- WebSocket/Server-Sent Events for real-time status updates (replace polling entirely for better scalability)
- TypeScript migration for type safety
- Database indexes for performance (team_id+challenge_id, timestamp)

## Resolved Issues

- **Challenge modal not reopenable after close** — Top-level `const` declarations in view.js threw SyntaxError on script re-evaluation; changed to `var` and added Alpine.js timer cleanup lifecycle (#19, 813832f)
- **Secret ID path traversal** — Regex validation on secret_id prevents directory traversal in DELETE endpoint (38dba8f)
- **Secret transmission security** — Require both HTTPS and Docker TLS before transmitting secret values (b70019b)
- **URL encoding in secret DELETE** — Added `encodeURIComponent` to prevent malformed URLs (40fd1ef)
- **MD5 security warning** — Added `usedforsecurity=False` to container/service naming hashes (a982149)
- **XSS `| safe` filter removal** — Removed 4 unsafe Jinja2 filters from admin_docker_status.html (e6f9c2b)
- **`do_request` safety checks** — Changed return type to `Response | None` and guarded all callers (248bfaa)
- **HTTP 403→404 fix** — Return correct status code for "challenge not found" (065e46d)
