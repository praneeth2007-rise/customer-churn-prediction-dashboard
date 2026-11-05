(() => {
  const button = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#nav');
  if (button && nav) {
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!open));
      button.setAttribute('aria-label', open ? 'Open navigation' : 'Close navigation');
      nav.classList.toggle('open', !open);
    });
    nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      nav.classList.remove('open');
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-label', 'Open navigation');
    }));
  }
})();
