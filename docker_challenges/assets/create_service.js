import {
    addPortRow as addPortRowShared,
    updatePortsTextarea,
    loadExistingPorts as loadExistingPortsShared,
    setupPortValidation,
} from './shared/portManagement.js';

window.CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$;
    const md = _CTFd.lib.markdown();
    $('a[href="#new-desc-preview"]').on('shown.bs.tab', function (event) {
        if (event.target.hash == '#new-desc-preview') {
            var editor_value = $('#new-desc-editor').val();
            $(event.target.hash).html(md.render(editor_value));
        }
    });

    // Toggle Advanced Settings
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

    // Port Management - using shared module
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

    // Fetch Docker images
    fetch('/api/v1/docker')
        .then((response) => response.json())
        .then((result) => {
            const images = result.data.sort((a, b) => a.name.localeCompare(b.name));
            const selectElement = document.getElementById('dockerimage_select');

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
        })
        .catch((error) => {
            console.error('Error fetching Docker images:', error);
            ezal({
                title: 'Error Loading Images',
                body: 'Failed to fetch available Docker images. The challenge form may not work correctly. Please refresh the page or contact an administrator.',
                button: 'Got it!',
            });
        });

    // Fetch Docker secrets
    fetch('/api/v1/secret')
        .then((response) => response.json())
        .then((result) => {
            const secrets = result.data.sort((a, b) => a.name.localeCompare(b.name));
            const selectElement = document.getElementById('dockersecrets_select');

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
                    selectElement.appendChild(option);
                }
            });
        })
        .catch((error) => {
            console.error('Error fetching Docker secrets:', error);
            ezal({
                title: 'Error Loading Secrets',
                body: 'Failed to fetch available Docker secrets. Service challenges may not work correctly. Please refresh the page or contact an administrator.',
                button: 'Got it!',
            });
        });

    // Setup form validation using shared module
    setupPortValidation();
});
