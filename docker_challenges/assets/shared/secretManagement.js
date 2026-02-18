/**
 * Shared utility functions for Docker secrets and image management.
 *
 * This module provides reusable functions for:
 * - Fetching and populating Docker images dropdown
 * - List-based Docker secrets management with per-secret protection
 * - Quick secret creation modal handling
 *
 * Pattern: Callback-based initialization for flexibility across create/update forms
 * Similar to portManagement.js pattern
 */

import { showModal, hideModal, bindDismissButtons } from './modalUtils.js';

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
 * Populate the secrets dropdown, excluding already-added IDs.
 */
export function populateDropdown(dropdownId, secrets, excludeIds = []) {
    const dropdown = document.getElementById(dropdownId);
    // Keep only the placeholder option
    while (dropdown.options.length > 1) {
        dropdown.remove(1);
    }
    dropdown.disabled = false;

    const filtered = secrets
        .filter((s) => !excludeIds.includes(s.id))
        .sort((a, b) => a.name.localeCompare(b.name));

    if (filtered.length === 0 && secrets.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '(No secrets available)';
        dropdown.appendChild(opt);
        dropdown.disabled = true;
    }

    filtered.forEach((s) => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = s.name;
        dropdown.appendChild(opt);
    });
}

/**
 * Read all secret rows and write JSON to hidden input.
 */
export function syncHiddenInput(listId, hiddenInputId) {
    const list = document.getElementById(listId);
    const rows = list.querySelectorAll('[data-secret-id]');
    const secrets = [];
    rows.forEach((row) => {
        secrets.push({
            id: row.dataset.secretId,
            protected: row.querySelector('.secret-protect-cb').checked,
        });
    });
    document.getElementById(hiddenInputId).value = JSON.stringify(secrets);
}

/**
 * Add a secret row to the list UI.
 */
export function addSecretToList(
    listId,
    hiddenInputId,
    dropdownId,
    secretId,
    secretName,
    protect = true
) {
    const list = document.getElementById(listId);

    const row = document.createElement('div');
    row.className = 'd-flex align-items-center border rounded p-2 mb-1';
    row.dataset.secretId = secretId;
    row.dataset.secretName = secretName;

    const nameSpan = document.createElement('span');
    nameSpan.className = 'fw-bold';
    nameSpan.style.flex = '1';
    nameSpan.style.minWidth = '0';
    nameSpan.textContent = secretName;

    const protectLabel = document.createElement('label');
    protectLabel.className = 'd-flex align-items-center ms-3 me-3 flex-shrink-0';
    protectLabel.style.cursor = 'pointer';

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'form-check-input me-1 secret-protect-cb';
    cb.checked = protect;
    cb.addEventListener('change', () => syncHiddenInput(listId, hiddenInputId));

    const protectText = document.createElement('small');
    protectText.className = 'text-muted';
    protectText.textContent = 'Protected';

    protectLabel.appendChild(cb);
    protectLabel.appendChild(protectText);

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-sm btn-outline-danger ms-2 secret-remove-btn';
    removeBtn.innerHTML = '&times;';
    removeBtn.addEventListener('click', () =>
        removeSecretFromList(row, listId, hiddenInputId, dropdownId)
    );

    row.appendChild(nameSpan);
    row.appendChild(protectLabel);
    row.appendChild(removeBtn);
    list.appendChild(row);

    // Remove from dropdown
    const dropdown = document.getElementById(dropdownId);
    for (let i = 0; i < dropdown.options.length; i++) {
        if (dropdown.options[i].value === secretId) {
            dropdown.remove(i);
            break;
        }
    }
    dropdown.value = '';

    syncHiddenInput(listId, hiddenInputId);
}

/**
 * Remove a secret row and re-add to dropdown.
 */
export function removeSecretFromList(row, listId, hiddenInputId, dropdownId) {
    const secretId = row.dataset.secretId;
    const secretName = row.dataset.secretName;
    row.remove();

    // Re-add to dropdown
    const dropdown = document.getElementById(dropdownId);
    const opt = document.createElement('option');
    opt.value = secretId;
    opt.textContent = secretName;
    dropdown.appendChild(opt);

    syncHiddenInput(listId, hiddenInputId);
}

/**
 * Initialize the secrets manager: fetch secrets, populate dropdown, wire Add button.
 *
 * @param {string} dropdownId - ID of the single-select dropdown
 * @param {string} listId - ID of the secrets list container div
 * @param {string} hiddenInputId - ID of the hidden input for JSON
 * @param {Object} options - Optional config
 * @param {string|Array} options.existingSecrets - JSON string or array of existing secrets for pre-population
 */
export function initSecretsManager(dropdownId, listId, hiddenInputId, options = {}) {
    const addBtn = document.getElementById('add-selected-secret-btn');

    // Wire Add button to move selected secret from dropdown to list
    addBtn.addEventListener('click', () => {
        const dropdown = document.getElementById(dropdownId);
        const selectedOption = dropdown.options[dropdown.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        addSecretToList(
            listId,
            hiddenInputId,
            dropdownId,
            selectedOption.value,
            selectedOption.textContent
        );
    });

    // Fetch secrets and populate
    fetch('/api/v1/secret')
        .then((response) => response.json())
        .then((result) => {
            if (!result.data) {
                console.warn('No secrets data returned from API');
                return;
            }

            // Parse existing secrets
            let existing = [];
            if (options.existingSecrets) {
                if (typeof options.existingSecrets === 'string') {
                    try {
                        existing = JSON.parse(options.existingSecrets);
                    } catch (e) {
                        existing = [];
                    }
                } else {
                    existing = options.existingSecrets;
                }
            }

            const allSecrets = result.data;
            const excludeIds = existing.map((s) => s.id);

            // Populate dropdown excluding already-added secrets
            populateDropdown(dropdownId, allSecrets, excludeIds);

            // Pre-populate existing secrets in the list
            existing.forEach((sec) => {
                // Find the name from the API data
                const match = allSecrets.find((s) => s.id === sec.id);
                const name = match ? match.name : sec.id;
                addSecretToList(
                    listId,
                    hiddenInputId,
                    dropdownId,
                    sec.id,
                    name,
                    sec.protected !== false
                );
            });
        })
        .catch((error) => {
            console.error('Error fetching Docker secrets:', error);
            if (typeof ezal !== 'undefined') {
                ezal({
                    title: 'Error Loading Secrets',
                    body: 'Failed to fetch available Docker secrets.',
                    button: 'Got it!',
                });
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
    function resetSubmitButton() {
        const submitBtn = document.getElementById('submitQuickSecret');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Create & Select';
    }

    // The quickSecretForm container is a <div> (not a <form>) to avoid nested
    // form issues — CTFd wraps the challenge update template in its own <form>.
    // We use the container to scope input queries for reset/validation.
    function getFormContainer() {
        return document.getElementById(formId) || document.getElementById(modalId);
    }

    function resetFormFields() {
        const container = getFormContainer();
        container.querySelectorAll('input, textarea').forEach((el) => {
            if (el.type === 'checkbox' || el.type === 'radio') {
                el.checked = el.defaultChecked;
            } else {
                el.value = '';
            }
        });
    }

    function validateFields() {
        const name = document.getElementById('quickSecretName');
        const value = document.getElementById('quickSecretValue');
        if (!name.value.trim()) {
            name.focus();
            document.getElementById('quickSecretError').textContent = 'Secret name is required';
            document.getElementById('quickSecretError').style.display = 'block';
            return false;
        }
        if (!name.checkValidity()) {
            name.focus();
            document.getElementById('quickSecretError').textContent =
                'Secret name may only contain letters, numbers, dots, underscores, and hyphens';
            document.getElementById('quickSecretError').style.display = 'block';
            return false;
        }
        if (!value.value.trim()) {
            value.focus();
            document.getElementById('quickSecretError').textContent = 'Secret value is required';
            document.getElementById('quickSecretError').style.display = 'block';
            return false;
        }
        return true;
    }

    // Add Secret button handler
    document.getElementById(addButtonId).addEventListener('click', function () {
        const modalEl = document.getElementById(modalId);
        resetFormFields();
        document.getElementById('quickSecretError').style.display = 'none';
        resetSubmitButton();
        bindDismissButtons(modalEl);
        showModal(modalEl);
    });

    // Submit Quick Secret
    document.getElementById('submitQuickSecret').addEventListener('click', function () {
        if (!validateFields()) {
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
                    hideModal(document.getElementById(modalId));
                    resetSubmitButton();

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
                    resetSubmitButton();
                }
            })
            .catch(() => {
                document.getElementById('quickSecretError').textContent = 'Network error';
                document.getElementById('quickSecretError').style.display = 'block';
                resetSubmitButton();
            });
    });
}
