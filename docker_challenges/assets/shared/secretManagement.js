/**
 * Shared utility functions for Docker secrets and image management.
 *
 * This module provides reusable functions for:
 * - Fetching and populating Docker images dropdown
 * - Fetching and populating Docker secrets dropdown
 * - Quick secret creation modal handling
 * - Secrets dropdown refresh after creation
 *
 * Pattern: Callback-based initialization for flexibility across create/update forms
 * Similar to portManagement.js pattern
 */

/**
 * Fetch Docker images and populate dropdown with auto-port population.
 *
 * @param {string} selectElementId - ID of the select element
 * @param {Object} options - Configuration options
 * @param {Function} options.onLoad - Callback after images loaded (receives selectElement)
 * @param {Function} options.onError - Callback on fetch error
 * @param {Function} options.loadExistingPorts - Function to reload port UI
 */
export function fetchDockerImages(selectElementId, options = {}) {
    const { onLoad, onError, loadExistingPorts } = options;

    fetch('/api/v1/docker')
        .then((response) => response.json())
        .then((result) => {
            const images = result.data.sort((a, b) => a.name.localeCompare(b.name));
            const selectElement = document.getElementById(selectElementId);

            images.forEach((item) => {
                if (item.name === 'Error in Docker Config!') {
                    selectElement.disabled = true;
                    const label = document.querySelector("label[for='DockerImage']");
                    if (label) {
                        label.textContent = 'Docker Image ' + item.name;
                    }
                } else {
                    const option = document.createElement('option');
                    option.value = item.name;
                    option.textContent = item.name;
                    selectElement.appendChild(option);
                }
            });

            // Auto-populate exposed ports when image is selected
            selectElement.addEventListener('change', function () {
                const imageName = this.value;
                if (!imageName) return;

                fetch(`/api/v1/image_ports?image=${encodeURIComponent(imageName)}`)
                    .then((response) => response.json())
                    .then((result) => {
                        if (result.success) {
                            const portsTextarea = document.getElementById('exposed_ports');

                            // Always update ports based on selected image
                            if (result.ports && result.ports.length > 0) {
                                portsTextarea.value = result.ports.join(',');
                            } else {
                                // Clear ports if image has none
                                portsTextarea.value = '';
                            }

                            // Reload UI with new ports (callback provided)
                            if (loadExistingPorts) {
                                loadExistingPorts();
                            }
                        } else {
                            if (typeof ezal !== 'undefined') {
                                ezal({
                                    title: 'Error Loading Ports',
                                    body: 'Failed to fetch exposed ports for the selected image. Please try again or configure ports manually.',
                                    button: 'Got it!',
                                });
                            }
                        }
                    })
                    .catch((error) => {
                        console.error('Error fetching image ports:', error);
                        if (typeof ezal !== 'undefined') {
                            ezal({
                                title: 'Network Error',
                                body: 'Could not connect to server to fetch image ports. Please check your connection and try again.',
                                button: 'Got it!',
                            });
                        }
                    });
            });

            // Call onLoad callback if provided (for update form pre-selection)
            if (onLoad) {
                onLoad(selectElement);
            }
        })
        .catch((error) => {
            console.error('Error fetching Docker images:', error);
            if (typeof ezal !== 'undefined') {
                ezal({
                    title: 'Error Loading Images',
                    body: 'Failed to fetch available Docker images. The challenge form may not work correctly. Please refresh the page or contact an administrator.',
                    button: 'Got it!',
                });
            }

            // Call onError callback if provided
            if (onError) {
                onError(error);
            }
        });
}

/**
 * Fetch Docker secrets and populate dropdown.
 *
 * @param {string} selectElementId - ID of the select element
 * @param {Object} options - Configuration options
 * @param {Function} options.onLoad - Callback after secrets loaded (receives selectElement)
 * @param {Function} options.onError - Callback on fetch error
 * @param {Array<string>} options.selectedSecrets - Array of secret IDs to pre-select (for update form)
 */
export function fetchDockerSecrets(selectElementId, options = {}) {
    const { onLoad, onError, selectedSecrets = [] } = options;

    fetch('/api/v1/secret')
        .then((response) => response.json())
        .then((result) => {
            // Handle missing data field (API error responses)
            if (!result.data) {
                console.warn('No secrets data returned from API');
                return;
            }

            const secrets = result.data.sort((a, b) => a.name.localeCompare(b.name));
            const selectElement = document.getElementById(selectElementId);

            // Clear existing options
            selectElement.innerHTML = '';

            // Handle empty secrets list (e.g., Docker not in swarm mode)
            if (secrets.length === 0) {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = '(No secrets available - Docker not in swarm mode)';
                selectElement.appendChild(option);
                selectElement.disabled = true;
                return;
            }

            secrets.forEach((item) => {
                if (item.name === 'Error in Docker Config!') {
                    selectElement.disabled = true;
                    const label = document.querySelector("label[for='DockerSecrets']");
                    if (label) {
                        label.textContent = 'Docker Secret ' + item.name;
                    }
                } else {
                    const option = document.createElement('option');
                    option.value = item.id;
                    option.textContent = item.name;

                    // Pre-select if in selectedSecrets array
                    if (selectedSecrets.includes(item.id)) {
                        option.selected = true;
                    }

                    selectElement.appendChild(option);
                }
            });

            // Call onLoad callback if provided
            if (onLoad) {
                onLoad(selectElement);
            }
        })
        .catch((error) => {
            console.error('Error fetching Docker secrets:', error);

            // Note: ezal is a CTFd global function that may not be available in all contexts
            if (typeof ezal !== 'undefined') {
                ezal({
                    title: 'Error Loading Secrets',
                    body: 'Failed to fetch available Docker secrets. Service challenges may not work correctly. Please refresh the page or contact an administrator.',
                    button: 'Got it!',
                });
            }

            // Call onError callback if provided
            if (onError) {
                onError(error);
            }
        });
}

/**
 * Setup quick secret creation modal handlers.
 *
 * Attaches event listeners to the "Add Secret" button and modal form submission.
 *
 * @param {string} addButtonId - ID of the "Add Secret" button
 * @param {string} modalId - ID of the modal element
 * @param {string} formId - ID of the form inside the modal
 * @param {Function} onSuccess - Callback after successful secret creation (receives secret_id)
 */
export function setupQuickSecretModal(addButtonId, modalId, formId, onSuccess) {
    // Add Secret button handler
    document.getElementById(addButtonId).addEventListener('click', function () {
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        document.getElementById(formId).reset();
        document.getElementById('quickSecretError').style.display = 'none';
        modal.show();
    });

    // Submit Quick Secret
    document.getElementById('submitQuickSecret').addEventListener('click', function () {
        const form = document.getElementById(formId);
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const secretName = document.getElementById('quickSecretName').value;
        const secretValue = document.getElementById('quickSecretValue').value;
        const btn = this;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

        fetch('/api/v1/secret', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'CSRF-Token': init.csrfNonce,
            },
            body: JSON.stringify({ name: secretName, data: secretValue }),
        })
            .then((response) => response.json().then((data) => ({ status: response.status, data })))
            .then((result) => {
                if (result.status === 201 && result.data.success) {
                    bootstrap.Modal.getInstance(document.getElementById(modalId)).hide();

                    // Call success callback with new secret ID
                    if (onSuccess) {
                        onSuccess(result.data.data.id, secretName);
                    }

                    if (typeof ezal !== 'undefined') {
                        ezal({
                            title: 'Success',
                            body: `Secret '${secretName}' created and selected!`,
                        });
                    }
                } else {
                    document.getElementById('quickSecretError').textContent =
                        result.data.error || 'Failed';
                    document.getElementById('quickSecretError').style.display = 'block';
                    btn.disabled = false;
                    btn.innerHTML = 'Create & Select';
                }
            })
            .catch(() => {
                document.getElementById('quickSecretError').textContent = 'Network error';
                document.getElementById('quickSecretError').style.display = 'block';
                btn.disabled = false;
                btn.innerHTML = 'Create & Select';
            });
    });
}

/**
 * Refresh secrets dropdown after new secret creation.
 *
 * Fetches updated secrets list and selects the newly created secret.
 *
 * @param {string} selectElementId - ID of the select element
 * @param {string} newSecretId - ID of the newly created secret to select
 */
export function refreshSecretsDropdown(selectElementId, newSecretId) {
    fetch('/api/v1/secret')
        .then((response) => response.json())
        .then((result) => {
            if (!result.data) return;

            const selectElement = document.getElementById(selectElementId);
            selectElement.innerHTML = '';
            selectElement.disabled = false;

            const secrets = result.data.sort((a, b) => a.name.localeCompare(b.name));
            if (secrets.length === 0) {
                selectElement.appendChild(new Option('(No secrets available)', '', false, false));
                selectElement.disabled = true;
                return;
            }

            secrets.forEach((item) => {
                const option = new Option(item.name, item.id, false, item.id === newSecretId);
                selectElement.appendChild(option);
            });

            // Trigger change event to update hidden input
            selectElement.dispatchEvent(new Event('change'));
        })
        .catch((error) => console.error('Error refreshing secrets:', error));
}
