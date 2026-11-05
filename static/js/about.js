(() => {
  const side = document.querySelector('.sidebar');
  const scrim = document.querySelector('.mobile-scrim');
  const toggle = document.querySelector('.sidebar-toggle');
  const close = () => {
    side?.classList.remove('open');
    scrim?.classList.remove('open');
    toggle?.setAttribute('aria-expanded', 'false');
  };
  toggle?.addEventListener('click', () => {
    const open = !side.classList.contains('open');
    side.classList.toggle('open', open);
    scrim?.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  });
  scrim?.addEventListener('click', close);
  side?.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', close));
})();
