// Global CSRF helper for fetch
function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}
