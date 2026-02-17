/**
 * Vanilla JS modal helpers for Bootstrap CSS-based modals.
 *
 * CTFd does not expose `bootstrap` as a reliable global variable for plugins.
 * These helpers toggle modal visibility via CSS classes, which works with both
 * Bootstrap 4 and Bootstrap 5 stylesheets without requiring their JS bundles.
 */

export function showModal(modalEl) {
    modalEl.classList.add('show');
    modalEl.style.display = 'block';
    modalEl.setAttribute('aria-modal', 'true');
    modalEl.removeAttribute('aria-hidden');

    let backdrop = document.querySelector('.modal-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        document.body.appendChild(backdrop);
    }

    document.body.classList.add('modal-open');
}

export function hideModal(modalEl) {
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    modalEl.removeAttribute('aria-modal');
    modalEl.setAttribute('aria-hidden', 'true');

    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) backdrop.remove();

    document.body.classList.remove('modal-open');
}

export function bindDismissButtons(modalEl) {
    modalEl.querySelectorAll('[data-bs-dismiss="modal"], [data-dismiss="modal"]').forEach((btn) => {
        btn.addEventListener('click', () => hideModal(modalEl));
    });
}
