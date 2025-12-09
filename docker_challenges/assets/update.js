CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$
    const md = _CTFd.lib.markdown()

    // Toggle Advanced Settings
    document.getElementById('toggleAdvancedSettings').addEventListener('click', function() {
        const settingsDiv = document.getElementById('advancedSettings');
        const chevron = document.getElementById('advancedSettingsChevron');

        if (settingsDiv.style.display === 'none') {
            settingsDiv.style.display = 'block';
            chevron.classList.remove('fa-chevron-down');
            chevron.classList.add('fa-chevron-up');
        } else {
            settingsDiv.style.display = 'none';
            chevron.classList.remove('fa-chevron-up');
            chevron.classList.add('fa-chevron-down');
        }
    });

    // Port Management Functions
    function validatePort(port) {
        const portNum = parseInt(port);
        return portNum >= 1 && portNum <= 65535;
    }

    function addPortRow(port, protocol) {
        const container = document.getElementById('portsContainer');
        const row = document.createElement('div');
        row.className = 'input-group mb-2';
        row.innerHTML = `
            <input type="number" class="form-control port-input" placeholder="Port" value="${port || ''}" min="1" max="65535" required>
            <select class="form-control protocol-select" style="max-width: 100px;">
                <option value="tcp" ${protocol === 'tcp' ? 'selected' : ''}>TCP</option>
                <option value="udp" ${protocol === 'udp' ? 'selected' : ''}>UDP</option>
            </select>
            <button type="button" class="btn btn-danger btn-sm remove-port-btn">
                <i class="fas fa-times"></i>
            </button>
        `;

        const removeBtn = row.querySelector('.remove-port-btn');
        removeBtn.addEventListener('click', function() {
            row.remove();
            updatePortsTextarea();
        });

        const portInput = row.querySelector('.port-input');
        const protocolSelect = row.querySelector('.protocol-select');

        portInput.addEventListener('change', updatePortsTextarea);
        protocolSelect.addEventListener('change', updatePortsTextarea);

        container.appendChild(row);
    }

    function updatePortsTextarea() {
        const rows = document.querySelectorAll('#portsContainer .input-group');
        const ports = [];

        rows.forEach(row => {
            const portInput = row.querySelector('.port-input');
            const protocolSelect = row.querySelector('.protocol-select');
            const port = portInput.value.trim();
            const protocol = protocolSelect.value;

            if (port && validatePort(port)) {
                ports.push(`${port}/${protocol}`);
            }
        });

        document.getElementById('exposed_ports').value = ports.join(',');
    }

    function loadExistingPorts() {
        const textarea = document.getElementById('exposed_ports');
        const portsString = textarea.value.trim();

        // Clear existing rows
        document.getElementById('portsContainer').innerHTML = '';

        if (!portsString) {
            // Add one empty row by default
            addPortRow('', 'tcp');
            return;
        }

        // Parse and create rows
        const ports = portsString.split(',');
        ports.forEach(portStr => {
            const match = portStr.trim().match(/^(\d+)\/(tcp|udp)$/i);
            if (match) {
                addPortRow(match[1], match[2].toLowerCase());
            }
        });

        // If no valid ports were parsed, add one empty row
        if (document.querySelectorAll('#portsContainer .input-group').length === 0) {
            addPortRow('', 'tcp');
        }
    }

    // Add Port button handler
    document.getElementById('addPortBtn').addEventListener('click', function() {
        addPortRow('', 'tcp');
    });

    // Initialize with one empty port row
    loadExistingPorts();

    // Fetch Docker images using fetch() API
    fetch("/api/v1/docker")
        .then(response => response.json())
        .then(result => {
            const images = result.data.sort((a, b) => a.name.localeCompare(b.name));
            const selectElement = document.getElementById('dockerimage_select');

            images.forEach(item => {
                const option = document.createElement('option');
                option.value = item.name;
                option.textContent = item.name;
                selectElement.appendChild(option);
            });

            // Pre-select current Docker image
            selectElement.value = DOCKER_IMAGE;

            // Auto-populate exposed ports when image changes
            selectElement.addEventListener('change', function() {
                const imageName = this.value;
                if (!imageName) return;

                fetch(`/api/v1/image_ports?image=${encodeURIComponent(imageName)}`)
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            const portsTextarea = document.getElementById('exposed_ports');

                            // Always update ports based on selected image
                            if (result.ports && result.ports.length > 0) {
                                portsTextarea.value = result.ports.join(',');
                            } else {
                                // Clear ports if image has none
                                portsTextarea.value = '';
                            }
                            loadExistingPorts(); // Reload UI with new ports
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching image ports:', error);
                    });
            });
        })
        .catch(error => {
            console.error('Error fetching Docker images:', error);
        });

    // Form validation: ensure at least one port is configured
    // Hook into multiple submission points to catch CTFd's AJAX submission
    function validatePorts() {
        const portsTextarea = document.getElementById('exposed_ports');
        const ports = portsTextarea.value.trim();

        if (!ports) {
            // Expand Advanced Settings to show the issue
            const settingsDiv = document.getElementById('advancedSettings');
            const chevron = document.getElementById('advancedSettingsChevron');
            if (settingsDiv.style.display === 'none') {
                settingsDiv.style.display = 'block';
                chevron.classList.remove('fa-chevron-down');
                chevron.classList.add('fa-chevron-up');
            }

            // Highlight the ports container with red border
            const portsContainer = document.getElementById('portsContainer');
            portsContainer.style.border = '2px solid red';
            portsContainer.style.padding = '10px';
            portsContainer.style.borderRadius = '4px';

            // Scroll to the Advanced Settings section
            document.getElementById('toggleAdvancedSettings').scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Show alert
            alert('ERROR: At least one exposed port must be configured in Advanced Settings.\n\nPlease add a port (e.g., 80/tcp) before submitting.');

            // Remove red border after 3 seconds
            setTimeout(() => {
                portsContainer.style.border = '';
                portsContainer.style.padding = '';
            }, 3000);

            return false;
        }
        return true;
    }

    // Hook into form submission
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!validatePorts()) {
                event.preventDefault();
                event.stopPropagation();
                return false;
            }
        }, true); // Use capture phase to run before other handlers
    }

    // Also hook into submit buttons directly
    setTimeout(() => {
        const submitButtons = document.querySelectorAll('button[type="submit"], input[type="submit"], .submit-button');
        submitButtons.forEach(button => {
            button.addEventListener('click', function(event) {
                if (!validatePorts()) {
                    event.preventDefault();
                    event.stopPropagation();
                    return false;
                }
            }, true); // Use capture phase
        });
    }, 1000); // Delay to ensure buttons are loaded
});
