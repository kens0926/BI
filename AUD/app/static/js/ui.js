document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('toggleSidebar');
  if (!sidebar || !toggle) return;

  function setExpanded(exp) {
    toggle.setAttribute('aria-expanded', String(!!exp));
  }

  toggle.addEventListener('click', (e) => {
    e.stopPropagation();
    if (window.innerWidth >= 768) return;
    const shown = sidebar.classList.toggle('show');
    setExpanded(shown);
    if (shown) {
      // focus first link for keyboard users
      const first = sidebar.querySelector('a.nav-link');
      if (first) first.focus();
      // show overlay
      showOverlay();
    } else {
      hideOverlay();
    }
  });

  function showOverlay() {
    let ov = document.querySelector('.overlay');
    if (!ov) {
      ov = document.createElement('div');
      ov.className = 'overlay';
      document.body.appendChild(ov);
      ov.addEventListener('click', () => {
        sidebar.classList.remove('show');
        setExpanded(false);
        hideOverlay();
      });
    }
    ov.classList.add('show');
  }
  function hideOverlay(){
    const ov = document.querySelector('.overlay');
    if (ov) ov.classList.remove('show');
  }

  // close when clicking outside
  document.addEventListener('click', (e) => {
    if (window.innerWidth >= 768) return;
    if (!sidebar.classList.contains('show')) return;
    if (sidebar.contains(e.target) || toggle.contains(e.target)) return;
    sidebar.classList.remove('show');
    setExpanded(false);
    hideOverlay();
  });

  // close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar.classList.contains('show')) {
      sidebar.classList.remove('show');
      setExpanded(false);
      hideOverlay();
    }
  });

  // Theme handling
  const themeSelect = document.getElementById('themeSelect');
  function applyTheme(name){
    document.body.classList.remove('theme-green', 'theme-dark');
    if (name === 'green') document.body.classList.add('theme-green');
    if (name === 'dark') document.body.classList.add('theme-dark');
    try{ localStorage.setItem('iams_theme', name); }catch(e){}
  }
  function initTheme(){
    const saved = localStorage.getItem('iams_theme') || 'default';
    if (themeSelect) themeSelect.value = saved;
    applyTheme(saved);
  }
  if (themeSelect){
    themeSelect.addEventListener('change', () => applyTheme(themeSelect.value));
  }
  initTheme();
});
