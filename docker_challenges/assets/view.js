// Inline constants (cannot use ES6 imports due to Alpine.js race condition)
// See CLAUDE.md for explanation of why ES6 modules don't work for challenge views
const CONTAINER_POLL_INTERVAL_MS = 30000; // 30 seconds
const MS_PER_SECOND = 1000;

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

        async init() {
            await this.pollStatus();
            // Poll at configured interval
            setInterval(() => this.pollStatus(), CONTAINER_POLL_INTERVAL_MS);
        },

        async pollStatus() {
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
            } catch (error) {
                console.error('Error polling status:', error);
                // Only show alert if this is a persistent error (after initial load)
                if (this.containerRunning) {
                    ezal({
                        title: 'Status Update Failed',
                        body: 'Could not refresh container status. Your container may still be running, but the displayed information might be outdated.',
                        button: 'Got it!',
                    });
                }
            }
        },

        updateCountdown() {
            // Clear any existing interval
            if (this.countdownInterval) {
                clearTimeout(this.countdownInterval);
            }

            const updateTimer = () => {
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
                await fetch('/api/v1/container?id=' + challengeId);
                await this.pollStatus();
            } catch (error) {
                ezal({
                    title: 'Attention!',
                    body: 'You can only revert a container once per 5 minutes! Please be patient.',
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

// Check if Alpine.js and Bootstrap are available
function hasAlpineAndBootstrap() {
    return typeof Alpine !== 'undefined' && typeof bootstrap !== 'undefined' && bootstrap.Modal;
}

// Alert modal function (CTFd Pattern with Alpine.js)
function ezal(args) {
    if (!hasAlpineAndBootstrap()) {
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

    // Show modal using Bootstrap Modal API
    const modalElement = document.querySelector('[x-ref="alertModal"]');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

// Expose containerStatus to global scope for Alpine.js x-data directives
window.containerStatus = containerStatus;
