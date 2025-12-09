# Migration Guide: CTFd Docker Challenges v3.0.0

## Overview

This document provides upgrade instructions for migrating from previous versions of the CTFd Docker Challenges plugin to v3.0.0, which adds support for CTFd's new core theme with Alpine.js and Bootstrap 5.

## Breaking Changes

**None** - This is a frontend-only migration. The database schema, REST APIs, and Docker integration remain unchanged.

## Requirements

### Before Migration
- CTFd 3.7.x or earlier
- jQuery available globally
- Bootstrap 4

### After Migration
- **CTFd 3.8.0+** (includes core theme with Alpine.js 3.9.1 and Bootstrap 5.3.3)
- Modern browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- No IE11 support

## Migration Steps

### 1. Backup Current Installation

```bash
# Backup plugin directory
cp -r CTFd/CTFd/plugins/docker_challenges CTFd/CTFd/plugins/docker_challenges.backup

# Backup database (recommended)
mysqldump -u ctfd -p ctfd > ctfd_backup_$(date +%Y%m%d).sql
```

### 2. Update CTFd

Ensure you're running CTFd 3.8.0 or later:

```bash
cd CTFd
git fetch
git checkout 3.8.0  # or later version
```

### 3. Replace Plugin Files

```bash
# Remove old plugin files
rm -rf CTFd/CTFd/plugins/docker_challenges

# Install updated plugin (from this repository)
git clone https://github.com/[your-repo]/CTFd-Docker-Challenges.git CTFd/CTFd/plugins/docker_challenges
cd CTFd/CTFd/plugins/docker_challenges
git checkout feat/beta-compatibility  # or main after merge
```

### 4. Restart CTFd

```bash
# If using Docker Compose
docker-compose restart ctfd

# If using systemd
sudo systemctl restart ctfd

# If running manually
# Stop the current process and restart
python3 serve.py
```

### 5. Verify Installation

1. **Access Admin Configuration**
   - Navigate to `/admin/docker_config`
   - Verify TLS toggle enables/disables certificate fields reactively
   - Verify repository selection works

2. **Test Challenge View**
   - Create or view an existing Docker challenge
   - Click "Start Docker Instance" button
   - Verify countdown timer displays and updates every second
   - Verify connection details show (host:port format)

3. **Test Admin Dashboard**
   - Navigate to `/admin/docker_status`
   - Verify active containers display
   - Test table column sorting (click headers)
   - Test delete confirmation modals

4. **Check Browser Console**
   - Open browser DevTools (F12)
   - Navigate through plugin pages
   - Verify **zero console errors**

## What Changed

### Frontend Modernization

**JavaScript Framework Migration:**
- jQuery → Alpine.js 3.9.1 for reactivity
- jQuery AJAX → native `fetch()` API
- jQuery `.modal()` → Bootstrap 5 `new bootstrap.Modal()` API

**Bootstrap Upgrade:**
- Bootstrap 4 → Bootstrap 5.3.3
- Data attributes: `data-dismiss` → `data-bs-dismiss`
- Close buttons: `<span>&times;</span>` → `<button class="btn-close">`
- Modal API: jQuery plugin → native JavaScript API

**Code Quality Improvements:**
- Removed all inline `onclick` handlers (CSP compliance)
- Self-correcting countdown timer (timestamp-based calculations)
- Proper modal cleanup (prevents DOM artifacts)
- Error handling for fetch() requests

### Backend Updates

**CTFd 4.0 Preparation:**
- `attempt()` methods now return `ChallengeResponse` objects instead of tuples
- Backward compatible with CTFd 3.8.x (ChallengeResponse implements `__iter__()`)

### Files Modified

**Backend (2 files):**
- `docker_challenges/models/container.py` - ChallengeResponse migration
- `docker_challenges/models/service.py` - ChallengeResponse migration

**Frontend Templates (3 files):**
- `docker_challenges/templates/docker_config.html` - Alpine.js reactive forms
- `docker_challenges/templates/admin_docker_status.html` - Bootstrap 5 + vanilla JS
- `docker_challenges/assets/view.html` - Alpine.js challenge view

**Frontend JavaScript (5 files):**
- `docker_challenges/assets/view.js` - Alpine.js countdown timer
- `docker_challenges/assets/create.js` - fetch() API
- `docker_challenges/assets/update.js` - fetch() API
- `docker_challenges/assets/create_service.js` - fetch() API
- `docker_challenges/assets/update_service.js` - fetch() API

## Rollback Instructions

If you encounter issues, you can rollback to the previous version:

```bash
# Restore plugin directory
rm -rf CTFd/CTFd/plugins/docker_challenges
mv CTFd/CTFd/plugins/docker_challenges.backup CTFd/CTFd/plugins/docker_challenges

# Restart CTFd
docker-compose restart ctfd  # or your restart method

# Clear browser cache
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete
```

**Important:** No database changes were made, so active containers continue running during upgrade or rollback.

## Known Issues

None identified. All 7 implementation phases passed validation.

If you encounter issues, please report them at: https://github.com/[your-repo]/CTFd-Docker-Challenges/issues

## Testing Checklist

Use this checklist to verify successful migration:

### Admin Configuration (`/admin/docker_config`)
- [ ] Form loads without console errors
- [ ] TLS toggle works (enables/disables cert fields)
- [ ] Repository multi-select works
- [ ] Form submission saves settings
- [ ] Settings persist after page reload

### Challenge Creation (`/admin/challenges`)
- [ ] Docker challenge type available
- [ ] Image dropdown populates sorted alphabetically
- [ ] Form submits successfully
- [ ] Service challenge type works with secrets dropdown

### Challenge View (user-facing)
- [ ] "Start Docker Instance" button visible when no container
- [ ] Container starts successfully
- [ ] Connection details display (host:port)
- [ ] Countdown timer shows "5:00" and counts down
- [ ] Countdown updates every second without lag
- [ ] Page refresh recalculates countdown correctly
- [ ] "Revert Available" shows when timer expires

### Admin Dashboard (`/admin/docker_status`)
- [ ] Table loads with active containers
- [ ] Column sorting works (click headers)
- [ ] Delete confirmation modal shows
- [ ] Delete works (row disappears)
- [ ] "Nuke All" confirmation shows
- [ ] No console errors

## Support

For questions or issues:
- GitHub Issues: https://github.com/[your-repo]/CTFd-Docker-Challenges/issues
- CTFd Slack: #plugins channel
- Documentation: See README.md

## Version Compatibility

| Plugin Version | CTFd Version | Status |
|---------------|--------------|--------|
| v3.0.0+ | 3.8.0+ | ✅ Supported (core theme) |
| v2.x | 3.2.1 - 3.7.x | ⚠️ Legacy (deprecated theme) |
| v2.x | < 3.2.1 | ❌ Unsupported |

## Next Steps

After successful migration:
1. Monitor logs for 24 hours for any unexpected errors
2. Test challenge creation and container lifecycle
3. Update any custom integrations or scripts
4. Consider enabling Content Security Policy (now compatible)
