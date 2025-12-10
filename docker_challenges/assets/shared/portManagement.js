/**
 * Port Management Utilities
 * Shared module for managing exposed ports across Docker challenge forms
 */

/**
 * Validate port number is in valid range (1-65535)
 * @param {string|number} port - Port number to validate
 * @returns {boolean} True if port is valid
 */
export function validatePort(port) {
    const portNum = parseInt(port);
    return portNum >= 1 && portNum <= 65535;
}

/**
 * Add a new port row to the ports container
 * @param {string} port - Port number
 * @param {string} protocol - Protocol (tcp/udp)
 * @param {Function} updateCallback - Callback to call when port is updated
 */
export function addPortRow(port, protocol, updateCallback) {
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
    removeBtn.addEventListener('click', function () {
        row.remove();
        updateCallback();
    });

    const portInput = row.querySelector('.port-input');
    const protocolSelect = row.querySelector('.protocol-select');

    portInput.addEventListener('change', updateCallback);
    protocolSelect.addEventListener('change', updateCallback);

    container.appendChild(row);
}

/**
 * Update the hidden exposed_ports textarea from the UI rows
 */
export function updatePortsTextarea() {
    const rows = document.querySelectorAll('#portsContainer .input-group');
    const ports = [];

    rows.forEach((row) => {
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

/**
 * Load existing ports from textarea and populate UI rows
 * @param {Function} addRowCallback - Callback to add a row (receives port, protocol)
 */
export function loadExistingPorts(addRowCallback) {
    const textarea = document.getElementById('exposed_ports');
    const portsString = textarea.value.trim();

    // Clear existing rows
    document.getElementById('portsContainer').innerHTML = '';

    if (!portsString) {
        // Add one empty row by default
        addRowCallback('', 'tcp');
        return;
    }

    // Parse and create rows
    const ports = portsString.split(',');
    ports.forEach((portStr) => {
        const match = portStr.trim().match(/^(\d+)\/(tcp|udp)$/i);
        if (match) {
            addRowCallback(match[1], match[2].toLowerCase());
        }
    });

    // If no valid ports were parsed, add one empty row
    if (document.querySelectorAll('#portsContainer .input-group').length === 0) {
        addRowCallback('', 'tcp');
    }
}

/**
 * Validate that at least one port is configured
 * @returns {boolean} True if validation passes
 */
export function validatePorts() {
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
        document
            .getElementById('toggleAdvancedSettings')
            .scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Show alert
        alert(
            'ERROR: At least one exposed port must be configured in Advanced Settings.\n\nPlease add a port (e.g., 80/tcp) before submitting.'
        );

        // Remove red border after 3 seconds
        setTimeout(() => {
            portsContainer.style.border = '';
            portsContainer.style.padding = '';
        }, 3000);

        return false;
    }
    return true;
}

/**
 * Setup form validation hooks to ensure ports are configured
 * Hooks into form submission and submit buttons
 */
export function setupPortValidation() {
    // Hook into form submission
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener(
            'submit',
            function (event) {
                if (!validatePorts()) {
                    event.preventDefault();
                    event.stopPropagation();
                    return false;
                }
            },
            true
        ); // Use capture phase to run before other handlers
    }

    // Also hook into submit buttons directly
    setTimeout(() => {
        const submitButtons = document.querySelectorAll(
            'button[type="submit"], input[type="submit"], .submit-button'
        );
        submitButtons.forEach((button) => {
            button.addEventListener(
                'click',
                function (event) {
                    if (!validatePorts()) {
                        event.preventDefault();
                        event.stopPropagation();
                        return false;
                    }
                },
                true
            ); // Use capture phase
        });
    }, 1000); // Delay to ensure buttons are loaded
}
