import {
    addPortRow as addPortRowShared,
    updatePortsTextarea,
    loadExistingPorts as loadExistingPortsShared,
    setupPortValidation,
} from './shared/portManagement.js';

/**
 * Setup markdown preview tab handler
 */
function setupMarkdownPreview($, md) {
    $('a[href="#new-desc-preview"]').on('shown.bs.tab', function (event) {
        if (event.target.hash == '#new-desc-preview') {
            var editor_value = $('#new-desc-editor').val();
            $(event.target.hash).html(md.render(editor_value));
        }
    });
}

/**
 * Setup advanced settings collapsible toggle
 */
function setupAdvancedSettingsToggle() {
    document.getElementById('toggleAdvancedSettings').addEventListener('click', function () {
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
}

/**
 * Setup port management UI and handlers
 */
function setupPortManagement() {
    // Wrapper function to bind updatePortsTextarea callback
    function addPortRow(port, protocol) {
        addPortRowShared(port, protocol, updatePortsTextarea);
    }

    function loadExistingPorts() {
        loadExistingPortsShared(addPortRow);
    }

    // Add Port button handler
    document.getElementById('addPortBtn').addEventListener('click', function () {
        addPortRow('', 'tcp');
    });

    // Initialize with one empty port row
    loadExistingPorts();
}

/**
 * Handle image port auto-population when image is selected
 */
function setupImagePortHandler(selectElement, loadExistingPorts) {
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
                    loadExistingPorts(); // Reload UI with new ports
                } else {
                    ezal({
                        title: 'Error Loading Ports',
                        body: 'Failed to fetch exposed ports for the selected image. Please try again or configure ports manually.',
                        button: 'Got it!',
                    });
                }
            })
            .catch((error) => {
                console.error('Error fetching image ports:', error);
                ezal({
                    title: 'Network Error',
                    body: 'Could not connect to server to fetch image ports. Please check your connection and try again.',
                    button: 'Got it!',
                });
            });
    });
}

/**
 * Populate Docker image select dropdown
 */
function populateDockerImages(images) {
    const selectElement = document.getElementById('dockerimage_select');
    const sortedImages = images.sort((a, b) => a.name.localeCompare(b.name));

    sortedImages.forEach((item) => {
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

    return selectElement;
}

/**
 * Setup Docker image selection and port auto-population
 */
function setupDockerImageSelection(loadExistingPorts) {
    fetch('/api/v1/docker')
        .then((response) => response.json())
        .then((result) => {
            const selectElement = populateDockerImages(result.data);
            setupImagePortHandler(selectElement, loadExistingPorts);
        })
        .catch((error) => {
            console.error('Error fetching Docker images:', error);
            ezal({
                title: 'Error Loading Images',
                body: 'Failed to fetch available Docker images. The challenge form may not work correctly. Please refresh the page or contact an administrator.',
                button: 'Got it!',
            });
        });
}

window.CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$;
    const md = _CTFd.lib.markdown();

    // Wrapper for loadExistingPorts that's accessible to setupDockerImageSelection
    function loadExistingPorts() {
        loadExistingPortsShared((port, protocol) => {
            addPortRowShared(port, protocol, updatePortsTextarea);
        });
    }

    setupMarkdownPreview($, md);
    setupAdvancedSettingsToggle();
    setupPortManagement();
    setupDockerImageSelection(loadExistingPorts);
    setupPortValidation();
});
