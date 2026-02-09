import {
    addPortRow as addPortRowShared,
    updatePortsTextarea,
    loadExistingPorts as loadExistingPortsShared,
    setupPortValidation,
} from './shared/portManagement.js';
import {
    fetchDockerImages,
    fetchDockerSecrets,
    setupQuickSecretModal,
    refreshSecretsDropdown,
} from './shared/secretManagement.js';

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

    // Fetch Docker images using shared module
    fetchDockerImages('dockerimage_select', {
        loadExistingPorts: loadExistingPorts,
    });

    // Fetch Docker secrets using shared module
    fetchDockerSecrets('dockersecrets_select');

    // Setup quick secret creation modal using shared module
    setupQuickSecretModal('add-secret-btn', 'addSecretModal', 'quickSecretForm', (newSecretId) =>
        refreshSecretsDropdown('dockersecrets_select', newSecretId)
    );

    // Setup form validation using shared module
    setupPortValidation();
});
