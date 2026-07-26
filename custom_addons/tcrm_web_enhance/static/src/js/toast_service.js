/**
 * TCRM lightweight toast notifications (backend).
 * Usage: tcrmToast('Saved successfully', 'success');
 */
(function () {
  function ensureContainer() {
    var el = document.getElementById('tcrm_toast_container');
    if (!el) {
      el = document.createElement('div');
      el.id = 'tcrm_toast_container';
      document.body.appendChild(el);
    }
    return el;
  }

  function showToast(message, type, durationMs) {
    type = type || 'info';
    durationMs = durationMs || 4000;
    var container = ensureContainer();
    var toast = document.createElement('div');
    toast.className = 'tcrm_toast tcrm_toast--' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = '0.25s ease';
      setTimeout(function () { toast.remove(); }, 250);
    }, durationMs);
  }

  window.tcrmToast = showToast;
})();
