CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$
    const md = _CTFd.lib.markdown()

    // Initialize tooltips using Bootstrap 5 API
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el);
        });

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
                selectElement.dispatchEvent(new Event('change'));
            })
            .catch(error => {
                console.error('Error fetching Docker images:', error);
            });
    });
});
