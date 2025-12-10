// Stub file - actual script loading handled by template with type="module"
// This file exists to satisfy CTFd's getScript() requirement
// Must define CTFd._internal.challenge object for CTFd core compatibility
console.log('Docker challenge view stub loaded');

// Define required challenge interface functions (matching view.js)
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function () {};
CTFd._internal.challenge.render = null;
CTFd._internal.challenge.postRender = function () {};
CTFd._internal.challenge.submit = function (preview) {
    var challenge_id = parseInt(CTFd.lib.$('#challenge-id').val());
    var submission = CTFd.lib.$('#challenge-input').val();

    var body = {
        challenge_id: challenge_id,
        submission: submission,
    };
    var params = {};
    if (preview) {
        params['preview'] = true;
    }

    return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
        if (response.status === 429) {
            // User was ratelimited but process response
            return response;
        }
        if (response.status === 403) {
            // User is not logged in or CTF is paused.
            return response;
        }
        return response;
    });
};
