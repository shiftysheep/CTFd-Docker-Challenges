CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$
    const md = _CTFd.lib.markdown()
    $('a[href="#new-desc-preview"]').on('shown.bs.tab', function (event) {
        if (event.target.hash == '#new-desc-preview') {
            var editor_value = $('#new-desc-editor').val();
            $(event.target.hash).html(
                md.render(editor_value)
            );
        }
    });

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
            })
            .catch(error => {
                console.error('Error fetching Docker images:', error);
            });
    });
});
