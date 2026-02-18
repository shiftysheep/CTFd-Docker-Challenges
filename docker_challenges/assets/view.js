// Inline constants (cannot use ES6 imports due to Alpine.js race condition)
// See CLAUDE.md for explanation of why ES6 modules don't work for challenge views
// Using var so the script can be re-evaluated when switching between Docker challenges
var CONTAINER_POLL_INTERVAL_MS = 30000; // 30 seconds (base interval)
var CONTAINER_POLL_MAX_INTERVAL_MS = 300000; // 5 minutes (max backoff)
var CONTAINER_POLL_BACKOFF_MULTIPLIER = 2; // Double interval on each failure
var MS_PER_SECOND = 1000;

CTFd._internal.challenge.data = undefined;

CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function () {};

CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function () {};

CTFd._internal.challenge.submit = function (preview) {
    var challenge_id = parseInt(CTFd.lib.$('#challenge-id').val());
    var submission = CTFd.lib.$('#challenge-input').val();

    var body = {
        challenge_id: challenge_id,
        submission: submission,
    };
    var params = {};
    if (preview) {
        params['preview'] = true;
    }

    return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
        if (response.status === 429) {
            // User was ratelimited but process response
            return response;
        }
        if (response.status === 403) {
            // User is not logged in or CTF is paused.
            return response;
        }
        return response;
    });
};

// Alpine.js component factory for container status management
function containerStatus(container, challengeId) {
    return {
        containerRunning: false,
        host: '',
        ports: '',
        revertTime: null,
        countdownText: '',
        countdownInterval: null,
        // Exponential backoff state
        currentPollInterval: CONTAINER_POLL_INTERVAL_MS,
        pollTimeoutId: null,
        consecutiveFailures: 0,
        _destroyed: false,
        _onModalHidden: null,

        async init() {
            await this.pollStatus();
            // Schedule next poll with dynamic interval
            this.schedulePoll();

            // Clean up timers when challenge modal closes
            const modal = this.$el.closest('.modal');
            if (modal) {
                this._onModalHidden = () => this.destroy();
                modal.addEventListener('hidden.bs.modal', this._onModalHidden, { once: true });
            }
        },

        destroy() {
            this._destroyed = true;
            if (this.pollTimeoutId) {
                clearTimeout(this.pollTimeoutId);
                this.pollTimeoutId = null;
            }
            if (this.countdownInterval) {
                clearTimeout(this.countdownInterval);
                this.countdownInterval = null;
            }
            const modal = this.$el?.closest('.modal');
            if (modal && this._onModalHidden) {
                modal.removeEventListener('hidden.bs.modal', this._onModalHidden);
                this._onModalHidden = null;
            }
        },

        /**
         * Schedule the next status poll with current interval
         * Uses setTimeout for dynamic interval adjustment
         */
        schedulePoll() {
            // Clear any existing timeout
            if (this.pollTimeoutId) {
                clearTimeout(this.pollTimeoutId);
            }
            if (this._destroyed) return;

            this.pollTimeoutId = setTimeout(() => this.pollStatus(), this.currentPollInterval);
        },

        /**
         * Calculate next poll interval with exponential backoff
         * Doubles interval on each failure, capped at CONTAINER_POLL_MAX_INTERVAL_MS
         */
        calculateBackoffInterval() {
            const nextInterval = this.currentPollInterval * CONTAINER_POLL_BACKOFF_MULTIPLIER;
            return Math.min(nextInterval, CONTAINER_POLL_MAX_INTERVAL_MS);
        },

        /**
         * Reset polling interval to base value after successful poll
         */
        resetPollInterval() {
            this.currentPollInterval = CONTAINER_POLL_INTERVAL_MS;
            this.consecutiveFailures = 0;
        },

        async pollStatus() {
            if (this._destroyed) return;
            try {
                const response = await fetch('/api/v1/docker_status');
                const result = await response.json();

                if (result.data && result.data.length > 0) {
                    const containerInfo = result.data.find(
                        (item) => item.challenge_id == challengeId && item.docker_image == container
                    );

                    if (containerInfo) {
                        this.containerRunning = true;
                        this.host = containerInfo.host;
                        this.ports = String(containerInfo.ports);
                        this.revertTime = parseInt(containerInfo.revert_time) * MS_PER_SECOND; // Convert to milliseconds
                        this.updateCountdown();
                    } else {
                        this.containerRunning = false;
                    }
                }

                // Success - reset backoff interval
                this.resetPollInterval();
            } catch (error) {
                console.error('Error polling status:', error);

                // Increment failure count and apply exponential backoff
                this.consecutiveFailures++;
                this.currentPollInterval = this.calculateBackoffInterval();

                console.log(
                    `Poll failed (${this.consecutiveFailures} consecutive). ` +
                        `Next poll in ${this.currentPollInterval / 1000}s`
                );

                // Only show alert if this is a persistent error (after initial load)
                if (this.containerRunning) {
                    ezal({
                        title: 'Status Update Failed',
                        body: 'Could not refresh container status. Your container may still be running, but the displayed information might be outdated.',
                        button: 'Got it!',
                    });
                }
            } finally {
                // Schedule next poll regardless of success/failure
                this.schedulePoll();
            }
        },

        updateCountdown() {
            // Clear any existing interval
            if (this.countdownInterval) {
                clearTimeout(this.countdownInterval);
            }

            const updateTimer = () => {
                if (this._destroyed) return;
                const now = Date.now();
                const distance = this.revertTime - now;

                if (distance <= 0) {
                    this.countdownText = 'Revert Available';
                    return;
                }

                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                const secondsStr = seconds < 10 ? '0' + seconds : seconds;

                this.countdownText = 'Next Revert Available in ' + minutes + ':' + secondsStr;

                // Recursively call after 1 second
                this.countdownInterval = setTimeout(updateTimer, 1000);
            };

            updateTimer();
        },

        async startContainer() {
            try {
                const response = await fetch('/api/v1/container', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'CSRF-Token': init.csrfNonce,
                    },
                    body: JSON.stringify({ challenge_id: challengeId }),
                });

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(result.error || 'Container creation failed');
                }

                await this.pollStatus();
            } catch (error) {
                ezal({
                    title: 'Container Error',
                    body:
                        error.message ||
                        'You can only revert a container once per 5 minutes! Please be patient.',
                    button: 'Got it!',
                });
                await this.pollStatus();
            }
        },

        getConnectionInfo() {
            if (!this.containerRunning) return '';

            const portList = this.ports.split(',');
            const lines = portList.map((port) => `Host: ${this.host} Port: ${port.trim()}`);
            return 'Docker Container Information:\n' + lines.join('\n');
        },
    };
}

// Initialize Alpine.js store for alert modal (CTFd Pattern)
// Initialize immediately to avoid undefined store errors
if (typeof Alpine !== 'undefined') {
    Alpine.store('alertModal', {
        title: '',
        body: '',
        button: 'Got it!',
    });
}

// Also listen for alpine:init in case Alpine loads later
document.addEventListener('alpine:init', () => {
    if (!Alpine.store('alertModal')) {
        Alpine.store('alertModal', {
            title: '',
            body: '',
            button: 'Got it!',
        });
    }
});

// Check if Alpine.js is available
function hasAlpine() {
    return typeof Alpine !== 'undefined';
}

// Alert modal function (CTFd Pattern with Alpine.js)
function ezal(args) {
    if (!hasAlpine()) {
        // Fallback to native alert
        alert(args.title + '\n\n' + args.body);
        return;
    }

    // Set Alpine store data
    Alpine.store('alertModal', {
        title: args.title,
        body: args.body,
        button: args.button || 'Got it!',
    });

    // Show modal using vanilla JS (no bootstrap.Modal dependency)
    const modalElement = document.querySelector('[x-ref="alertModal"]');
    if (!modalElement) {
        // Modal template not present (e.g., admin page context) — fall back to native alert
        alert(args.title + '\n\n' + args.body);
        return;
    }
    modalElement.classList.add('show');
    modalElement.style.display = 'block';
    modalElement.setAttribute('aria-modal', 'true');
    modalElement.removeAttribute('aria-hidden');

    var backdrop = document.querySelector('.modal-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        document.body.appendChild(backdrop);
    }
    document.body.classList.add('modal-open');

    // Bind dismiss buttons for close/cancel
    modalElement
        .querySelectorAll('[data-bs-dismiss="modal"], [data-dismiss="modal"]')
        .forEach(function (btn) {
            btn.addEventListener('click', function () {
                modalElement.classList.remove('show');
                modalElement.style.display = 'none';
                modalElement.removeAttribute('aria-modal');
                modalElement.setAttribute('aria-hidden', 'true');
                var bd = document.querySelector('.modal-backdrop');
                if (bd) bd.remove();
                document.body.classList.remove('modal-open');
            });
        });
}

// Expose containerStatus to global scope for Alpine.js x-data directives
window.containerStatus = containerStatus;
