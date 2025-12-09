# Testing Guide: CTFd Docker Challenges v3.0.0

This guide explains how to use the Docker-in-Docker testing environment to validate the Alpine.js + Bootstrap 5 migration.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for Docker
- Port 8000 available on your host machine

## Quick Start

### 1. Start the Test Environment

```bash
# Start all services in detached mode
docker-compose -f docker-compose.test.yml up -d

# Watch logs in real-time
docker-compose -f docker-compose.test.yml logs -f
```

**Services started:**
- `ctfd` - CTFd application on port 8000
- `docker-host` - Docker-in-Docker service (DinD) providing Docker API at `docker-host:2375`
- `db` - MariaDB database
- `cache` - Redis cache

### 2. Wait for Services to Initialize

```bash
# Check service health
docker-compose -f docker-compose.test.yml ps

# Wait for docker-host to be ready (~10 seconds)
docker-compose -f docker-compose.test.yml logs docker-host | grep "API listen on"
```

### 3. Load Test Challenge Images

```bash
# Pull test images into docker-host
docker exec ctfd_docker_host docker pull alpine:latest
docker exec ctfd_docker_host docker pull nginx:alpine
docker exec ctfd_docker_host docker pull python:3.9-alpine

# Tag as test challenge images
docker exec ctfd_docker_host docker tag alpine:latest test/challenge1:latest
docker exec ctfd_docker_host docker tag nginx:alpine test/challenge2:latest
docker exec ctfd_docker_host docker tag python:3.9-alpine test/challenge3:latest

# Verify images loaded
docker exec ctfd_docker_host docker images
```

### 4. Initialize CTFd

Open your browser to `http://localhost:8000` and complete the CTFd setup wizard:

**Setup Information:**
- Admin Email: admin@example.com
- Admin Password: (choose a password)
- CTF Name: Test CTF
- CTF Description: Testing Docker Challenges Plugin
- User Mode: Users (or Teams)
- CTF Mode: Standard

### 5. Configure Docker Challenges Plugin

Navigate to `/admin/docker_config`:

**Configuration:**
- **Hostname**: `docker-host:2375`
- **TLS Enabled**: No (for testing)
- **Repositories**: Select `test` from the dropdown
- Click **Submit**

You should see a success message and the repositories list should populate.

## Automated Verification Checks

Run these commands to verify the migration was successful:

### Check for jQuery Usage (should be 0 matches)

```bash
# Check JavaScript files for jQuery usage
grep -r '\$(' docker_challenges/assets/*.js

# Expected: No matches (or only CTFd.lib.$ which is acceptable)
```

### Check for Inline onclick Handlers (should be 0 matches)

```bash
# Check templates for inline event handlers
grep -r 'onclick=' docker_challenges/templates/*.html docker_challenges/assets/*.html

# Expected: No matches
```

### Check for Bootstrap 4 Data Attributes (should be 0 matches)

```bash
# Check for old data-toggle attributes
grep -r 'data-toggle' docker_challenges/

# Expected: No matches (all should be data-bs-toggle)
```

### Check for Alpine.js Components

```bash
# Verify Alpine.js directives are present
grep -r 'x-data' docker_challenges/templates/*.html docker_challenges/assets/*.html

# Expected: Matches in docker_config.html and view.html
```

## Manual Testing Checklist

### ✅ Admin Configuration (`/admin/docker_config`)

- [ ] Form loads without console errors
- [ ] TLS radio toggle works (Yes/No)
- [ ] Certificate fields enable when TLS=Yes
- [ ] Certificate fields disable when TLS=No
- [ ] Repository multi-select displays `test` repository
- [ ] Form submission saves configuration
- [ ] Page reload shows saved settings

**Test Steps:**
1. Toggle TLS between Yes and No - certificate fields should enable/disable instantly
2. Select `test` repository and click Submit
3. Reload page - verify `test` repository is still selected

### ✅ Challenge Creation (`/admin/challenges`)

- [ ] Click "Create Challenge" → Select challenge type `docker`
- [ ] Docker image dropdown populates with test/challenge1, test/challenge2, test/challenge3
- [ ] Images sorted alphabetically
- [ ] Tooltips work on help icons
- [ ] Challenge creation succeeds

**Test Steps:**
1. Create a new Docker challenge:
   - Name: "Test Challenge 1"
   - Category: "Testing"
   - Docker Image: test/challenge1:latest
   - Flag: `flag{test123}`
2. Click Create
3. Verify challenge appears in challenges list

### ✅ Challenge View (User Perspective)

- [ ] Navigate to challenge as non-admin user
- [ ] "Start Docker Instance" button visible
- [ ] Click button - spinner shows during creation
- [ ] Connection details display: "Host: docker-host Port: XXXXX"
- [ ] Countdown timer shows "5:00" initially
- [ ] Timer counts down: 5:00 → 4:59 → 4:58...
- [ ] Timer updates smoothly (≤100ms delay per second)
- [ ] Refresh page - countdown recalculates correctly
- [ ] After 5 minutes - "Revert Available" message shows
- [ ] No console errors

**Test Steps:**
1. Create a test user account
2. View the challenge created earlier
3. Click "Start Docker Instance"
4. Watch countdown timer for 30 seconds (verify smooth updates)
5. Refresh page - verify countdown continues correctly
6. Test connection to the container (if port is accessible)

### ✅ Challenge Update (`/admin/challenges`)

- [ ] Edit existing Docker challenge
- [ ] Form pre-populates with current settings
- [ ] Docker image dropdown shows current selection
- [ ] Form submission saves changes
- [ ] Changes reflect in challenge view

**Test Steps:**
1. Edit the challenge created earlier
2. Change Docker image to test/challenge2:latest
3. Click Update
4. View challenge - verify new image is used

### ✅ Admin Dashboard (`/admin/docker_status`)

- [ ] Table loads showing active container(s)
- [ ] Columns display: ID, User, Docker Image, Instance ID, Actions
- [ ] Click table headers to sort (ID, User, Image, Instance ID)
- [ ] Ascending sort on first click
- [ ] Descending sort on second click
- [ ] Click delete icon - confirmation modal shows
- [ ] Modal has "Yes" and "No" buttons
- [ ] Click "Yes" - container deletes, row disappears
- [ ] Click "No" - modal closes, nothing deleted
- [ ] "Nuke All Containers" button shows confirmation
- [ ] No console errors

**Test Steps:**
1. With active container from previous test, go to `/admin/docker_status`
2. Test column sorting by clicking headers
3. Click delete icon for the container
4. Click "Yes" in confirmation modal
5. Verify container disappears from list

### ✅ Service Challenges (`docker_service` type)

**Note:** Requires Docker Swarm mode

**Setup Swarm:**
```bash
# Initialize swarm in docker-host
docker exec ctfd_docker_host docker swarm init

# Create test secret
echo "test-secret-value" | docker exec -i ctfd_docker_host docker secret create test-secret -

# Verify secret created
docker exec ctfd_docker_host docker secret ls
```

**Test Steps:**
- [ ] Create challenge with type `docker_service`
- [ ] Docker secrets dropdown populates
- [ ] Secrets sorted alphabetically
- [ ] Multi-select allows choosing multiple secrets
- [ ] Service challenge creates successfully
- [ ] Service update form pre-populates secrets

### ✅ Modal Functionality

Test both modal types (`ezal` and `ezq`):

**Alert Modal (`ezal`):**
- [ ] Try to revert container before 5 minutes - alert modal shows
- [ ] Modal displays title, body, and button
- [ ] Click button or X - modal closes cleanly
- [ ] No DOM artifacts remain (check DevTools)

**Confirmation Modal (`ezq`):**
- [ ] Delete container - confirmation modal shows
- [ ] Modal has Yes and No buttons
- [ ] Yes executes action, No cancels
- [ ] Multiple sequential modals work correctly

### ✅ Performance Testing

- [ ] Page load time with 50+ containers ≤2 seconds
- [ ] Countdown timer ≤100ms delay over 5-minute duration
- [ ] Status polling doesn't degrade over 10+ minutes
- [ ] No memory leaks (check DevTools Memory tab)

**Performance Test Script:**
```bash
# Create multiple containers for performance testing
for i in {1..10}; do
  curl "http://localhost:8000/api/v1/container?id=CHALLENGE_ID"
  sleep 1
done
```

### ✅ Edge Cases

- [ ] Container creation when Docker API unavailable (error alert shows)
- [ ] Attempt revert before 5 minutes (error alert shows)
- [ ] Multiple users creating containers simultaneously
- [ ] Challenge solve auto-deletes container
- [ ] Stale containers (>2 hours) auto-cleanup
- [ ] Modal cleanup: open/close 10+ sequential modals

## Browser Console Monitoring

Open browser DevTools (F12) and check:

**Console Tab:**
- Zero errors (red messages)
- Zero warnings (yellow messages)
- Info messages are acceptable

**Network Tab:**
- `/api/v1/docker_status` polls every 30 seconds
- No failed requests (4xx/5xx errors)
- Response times <500ms

**Application Tab:**
- LocalStorage/SessionStorage working correctly
- No excessive data stored

## Cleanup

### Stop Test Environment

```bash
# Stop and remove containers
docker-compose -f docker-compose.test.yml down

# Remove volumes (resets database)
docker-compose -f docker-compose.test.yml down -v
```

### Full Cleanup

```bash
# Remove all test data including images
docker-compose -f docker-compose.test.yml down -v --rmi all

# Remove orphaned volumes
docker volume prune -f
```

## Troubleshooting

### CTFd Won't Start

```bash
# Check logs
docker-compose -f docker-compose.test.yml logs ctfd

# Common issues:
# - Database not ready: Wait 30 seconds and retry
# - Port 8000 in use: Change port in docker-compose.test.yml
```

### Docker-Host Not Accessible

```bash
# Verify docker-host is running
docker-compose -f docker-compose.test.yml ps docker-host

# Check API is listening
docker exec ctfd_docker_host netstat -ln | grep 2375

# Test connectivity from ctfd container
docker-compose -f docker-compose.test.yml exec ctfd curl docker-host:2375/version
```

### Containers Won't Start

```bash
# Check docker-host logs
docker-compose -f docker-compose.test.yml logs docker-host

# Verify images exist
docker exec ctfd_docker_host docker images

# Check port availability
docker exec ctfd_docker_host docker ps
```

### Database Connection Errors

```bash
# Restart database
docker-compose -f docker-compose.test.yml restart db

# Wait for initialization
docker-compose -f docker-compose.test.yml logs db | grep "ready for connections"
```

## Success Criteria

All tests pass when:

✅ **Automated Checks:**
- 0 jQuery references in plugin code
- 0 inline onclick handlers
- 0 Bootstrap 4 data attributes
- Alpine.js directives present

✅ **Manual Tests:**
- All 8 manual testing sections complete
- Zero console errors across all pages
- All interactive features work
- Modals open/close cleanly

✅ **Performance:**
- Page loads ≤2 seconds with 50+ containers
- Countdown accuracy ≤100ms over 5 minutes
- No memory leaks detected

## CI/CD Integration

To integrate with CI/CD pipelines:

```yaml
# .github/workflows/test.yml example
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Start test environment
      run: docker-compose -f docker-compose.test.yml up -d
    - name: Wait for services
      run: sleep 30
    - name: Run automated checks
      run: |
        bash scripts/verify-migration.sh
    - name: Cleanup
      run: docker-compose -f docker-compose.test.yml down -v
```

## Next Steps

After successful testing:
1. ✅ All automated checks pass
2. ✅ All manual tests complete
3. ✅ Performance benchmarks met
4. 🚀 Ready for production deployment

See [MIGRATION.md](MIGRATION.md) for production deployment instructions.
