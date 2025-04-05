CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$
    const md = _CTFd.lib.markdown()
    $(document).ready(function() {
        $.getJSON("/api/v1/docker", function(result) {
            const images = result['data'].sort((a, b) => a.name.localeCompare(b.name));
            $.each(images, function(i, item) {
                $("#dockerimage_select").append($("<option />").val(item.name).text(item.name));
            });
            $("#dockerimage_select").val(DOCKER_IMAGE).change();
        });
    });
});