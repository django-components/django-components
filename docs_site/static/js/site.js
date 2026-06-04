/**
 * Site interactivity for the django-components docs site.
 *
 * Spec: docs_site/design/DESIGN_spike_11.md sections 3.3, 4.1, 7.1, 9.1.
 *
 * Features:
 * - Theme toggle (auto / light / dark cycle)
 * - Sidebar group collapse/expand with localStorage persistence
 * - Right-rail TOC scroll-spy
 * - Scroll active sidebar item into view on page load
 * - Code block language label + copy button
 */

(function () {
  'use strict';

  // ----------------------------------------------------------------
  // Theme toggle (3-mode: auto -> light -> dark -> auto)
  // ----------------------------------------------------------------
  var THEME_KEY = 'djc-theme';
  var themeBtn = document.querySelector('.djc-theme-toggle');

  function getStoredTheme() {
    return localStorage.getItem(THEME_KEY) || 'auto';
  }

  function applyTheme(theme) {
    if (theme === 'auto') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }

  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var current = getStoredTheme();
      var next = current === 'auto' ? 'light' : current === 'light' ? 'dark' : 'auto';
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }

  // ----------------------------------------------------------------
  // Sidebar group collapse/expand
  // ----------------------------------------------------------------
  var SIDEBAR_KEY = 'djc-sidebar-state';

  function getSidebarState() {
    try {
      return JSON.parse(localStorage.getItem(SIDEBAR_KEY) || '{}');
    } catch (e) {
      return {};
    }
  }

  function saveSidebarState(state) {
    localStorage.setItem(SIDEBAR_KEY, JSON.stringify(state));
  }

  var groups = document.querySelectorAll('.djc-sidebar__group');
  var sidebarState = getSidebarState();

  groups.forEach(function (group) {
    var btn = group.querySelector('.djc-sidebar__group-label');
    var items = group.querySelector('.djc-sidebar__items');
    if (!btn || !items) return;

    var label = btn.querySelector('span:first-child');
    var key = label ? label.textContent.trim() : '';

    // Restore from localStorage (but don't override if group has active item)
    if (key && sidebarState[key] !== undefined && group.getAttribute('data-open') !== 'true') {
      var isOpen = sidebarState[key];
      group.setAttribute('data-open', isOpen ? 'true' : 'false');
      btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      items.hidden = !isOpen;
    }

    btn.addEventListener('click', function () {
      var nowOpen = group.getAttribute('data-open') === 'true';
      var nextOpen = !nowOpen;
      group.setAttribute('data-open', nextOpen ? 'true' : 'false');
      btn.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
      items.hidden = !nextOpen;

      if (key) {
        var state = getSidebarState();
        state[key] = nextOpen;
        saveSidebarState(state);
      }
    });
  });

  // Scroll active sidebar item into view
  var activeLink = document.querySelector('.djc-sidebar__link.is-active');
  if (activeLink) {
    activeLink.scrollIntoView({ block: 'nearest' });
  }

  // ----------------------------------------------------------------
  // Right-rail TOC scroll-spy
  // ----------------------------------------------------------------
  var tocLinks = document.querySelectorAll('.djc-toc__link');
  if (tocLinks.length > 0) {
    var headingIds = [];
    tocLinks.forEach(function (link) {
      var href = link.getAttribute('href');
      if (href && href.startsWith('#')) {
        headingIds.push(href.slice(1));
      }
    });

    var headingElements = headingIds
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);

    if (headingElements.length > 0) {
      var observer = new IntersectionObserver(
        function (entries) {
          // Find the first heading currently intersecting
          var activeId = null;
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              activeId = entry.target.id;
            }
          });

          if (activeId) {
            tocLinks.forEach(function (link) {
              var href = link.getAttribute('href');
              if (href === '#' + activeId) {
                link.classList.add('is-active');
              } else {
                link.classList.remove('is-active');
              }
            });
          }
        },
        {
          rootMargin: '-80px 0px -70% 0px',
          threshold: 0,
        }
      );

      headingElements.forEach(function (el) {
        observer.observe(el);
      });
    }
  }

  // ----------------------------------------------------------------
  // Code block: language label + copy button
  // Spec: DESIGN_spike_11.md section 6.2
  // ----------------------------------------------------------------
  document.querySelectorAll('.highlight').forEach(function (block) {
    var pre = block.querySelector('pre');
    if (!pre) return;

    // Detect language from the <code> class (e.g. "language-python" or just "python")
    var code = pre.querySelector('code');
    var lang = '';
    if (code) {
      var classes = code.className.split(/\s+/);
      for (var i = 0; i < classes.length; i++) {
        var cls = classes[i];
        if (cls.startsWith('language-')) {
          lang = cls.slice(9);
          break;
        } else if (cls && cls !== 'highlight' && !cls.startsWith('djc-')) {
          lang = cls;
          break;
        }
      }
    }

    // Make the pre position-relative for absolute children
    pre.style.position = 'relative';

    // Language label (top-right, always visible)
    if (lang) {
      var label = document.createElement('span');
      label.className = 'djc-code-lang';
      label.textContent = lang;
      pre.appendChild(label);
    }

    // Copy button (top-right, visible on hover)
    var btn = document.createElement('button');
    btn.className = 'djc-code-copy';
    btn.setAttribute('aria-label', 'Copy code');
    btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">' +
      '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
      '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>' +
      '</svg>';

    btn.addEventListener('click', function () {
      var text = code ? code.textContent : pre.textContent;
      navigator.clipboard.writeText(text).then(function () {
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">' +
          '<polyline points="20 6 9 17 4 12"/>' +
          '</svg>';
        setTimeout(function () {
          btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">' +
            '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
            '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>' +
            '</svg>';
        }, 1500);
      });
    });

    pre.appendChild(btn);
  });
})();
