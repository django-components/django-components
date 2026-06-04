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
})();
