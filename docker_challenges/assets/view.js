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
            // Poll every 30 seconds
            setInterval(() => this.pollStatus(), 30000);
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
                        this.revertTime = parseInt(containerInfo.revert_time) * 1000; // Convert to milliseconds
                        this.updateCountdown();
                    } else {
                        this.containerRunning = false;
                    }
                }
            } catch (error) {
                console.error('Error polling status:', error);
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

// Get Bootstrap Modal constructor (handle different loading methods)
function getBootstrapModal() {
    // Check if bootstrap is available globally
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        return bootstrap.Modal;
    }
    // Check if it's available via window.bootstrap
    if (typeof window.bootstrap !== 'undefined' && window.bootstrap.Modal) {
        return window.bootstrap.Modal;
    }
    // Fallback: return null if Bootstrap isn't available (native dialogs will be used)
    return null;
}

function ezal(args) {
    const Modal = getBootstrapModal();
    if (!Modal) {
        // Fallback if Bootstrap isn't available: use native alert
        alert(args.title + '\n\n' + args.body);
        return null;
    }

    // Create modal element using Bootstrap 5 native API
    const modalElement = document.createElement('div');
    modalElement.className = 'modal fade';
    modalElement.tabIndex = -1;
    modalElement.setAttribute('role', 'dialog');
    modalElement.innerHTML = `
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">${args.title}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <p>${args.body}</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">${args.button}</button>
          </div>
        </div>
      </div>
    `;

    // Append to document body
    document.body.appendChild(modalElement);

    // Initialize Bootstrap 5 modal
    const modal = new Modal(modalElement);

    // Add cleanup listener
    modalElement.addEventListener('hidden.bs.modal', function () {
        modal.dispose();
        modalElement.remove();
    });

    // Show modal
    modal.show();

    return modalElement;
}
