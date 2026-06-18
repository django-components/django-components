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
 * - Mobile nav drawer (hamburger toggle, overlay/Esc to close)
 * - Mobile header overflow menu (version + theme + GitHub)
 * - Back-to-top button (revealed after scrolling a screenful down)
 */

(function () {
  'use strict';

  // ----------------------------------------------------------------
  // Theme picker (3-button: light / auto / dark)
  // ----------------------------------------------------------------
  var THEME_KEY = 'djc-theme';
  var themeBtns = document.querySelectorAll('.djc-theme-picker__btn');

  function getStoredTheme() {
    return localStorage.getItem(THEME_KEY) || 'auto';
  }

  function applyTheme(theme) {
    if (theme === 'auto') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    // Highlight the active button
    themeBtns.forEach(function (btn) {
      var val = btn.getAttribute('data-theme-value');
      if (val === theme) {
        btn.classList.add('is-active');
      } else {
        btn.classList.remove('is-active');
      }
    });
  }

  // Set initial active state
  applyTheme(getStoredTheme());

  themeBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var theme = btn.getAttribute('data-theme-value');
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    });
  });

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

  // Sidebar scroll persistence: keep the left-nav scroll position when moving
  // between pages in the SAME nav section; only re-center on the active item
  // when entering a section we have no saved position for. Without this, every
  // click is a full page load that snaps the sidebar back near the top.
  var sidebar = document.getElementById('djc-sidebar');
  if (sidebar) {
    var SIDEBAR_SCROLL_KEY = 'djc-sidebar-scroll';

    // Which top-level section the active page lives in. Stable across pages (the
    // sidebar always renders every section), so it identifies "the same nav".
    var activeSectionSig = function () {
      var active = sidebar.querySelector('.djc-sidebar__link.is-active');
      var section = active && active.closest('.djc-sidebar__section');
      if (!section) return null;
      var sections = sidebar.querySelectorAll('.djc-sidebar__section');
      return String(Array.prototype.indexOf.call(sections, section));
    };

    var loadScrollMap = function () {
      try {
        return JSON.parse(sessionStorage.getItem(SIDEBAR_SCROLL_KEY) || '{}');
      } catch (e) {
        return {};
      }
    };

    // Restore this section's saved scroll, else bring the active item into view.
    var sig = activeSectionSig();
    var savedTop = sig !== null ? loadScrollMap()[sig] : undefined;
    if (savedTop !== undefined) {
      sidebar.scrollTop = savedTop;
    } else {
      var activeNavLink = sidebar.querySelector('.djc-sidebar__link.is-active');
      if (activeNavLink) activeNavLink.scrollIntoView({ block: 'nearest' });
    }

    // Persist the current section's scroll (debounced while scrolling, flushed
    // on navigate-away) so the next same-section page can restore it.
    var persistScroll = function () {
      var s = activeSectionSig();
      if (s === null) return;
      var map = loadScrollMap();
      map[s] = sidebar.scrollTop;
      try {
        sessionStorage.setItem(SIDEBAR_SCROLL_KEY, JSON.stringify(map));
      } catch (e) {
        /* sessionStorage unavailable (private mode / quota) - skip */
      }
    };

    var scrollTimer = null;
    sidebar.addEventListener('scroll', function () {
      if (scrollTimer) clearTimeout(scrollTimer);
      scrollTimer = setTimeout(persistScroll, 150);
    });
    window.addEventListener('pagehide', persistScroll);
  }

  // ----------------------------------------------------------------
  // Mobile nav drawer (the sidebar becomes off-canvas below 768px)
  // ----------------------------------------------------------------
  var hamburger = document.querySelector('.djc-hamburger');
  var drawerOverlay = document.querySelector('.djc-drawer-overlay');

  function setDrawer(open) {
    document.body.classList.toggle('djc-drawer-open', open);
    if (hamburger) {
      hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
  }

  if (hamburger) {
    hamburger.addEventListener('click', function () {
      setDrawer(!document.body.classList.contains('djc-drawer-open'));
    });
  }

  if (drawerOverlay) {
    drawerOverlay.addEventListener('click', function () {
      setDrawer(false);
    });
  }

  // ----------------------------------------------------------------
  // Header overflow menu (mobile home for version + theme + GitHub)
  // ----------------------------------------------------------------
  var overflowEl = document.querySelector('.djc-overflow');
  var overflowBtn = document.querySelector('.djc-overflow__btn');

  function closeOverflow() {
    if (overflowEl && overflowEl.classList.contains('is-open')) {
      overflowEl.classList.remove('is-open');
      overflowBtn.setAttribute('aria-expanded', 'false');
    }
  }

  if (overflowEl && overflowBtn) {
    overflowBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = overflowEl.classList.toggle('is-open');
      overflowBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Click anywhere outside the menu closes it
    document.addEventListener('click', function (e) {
      if (!overflowEl.contains(e.target)) {
        closeOverflow();
      }
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      setDrawer(false);
      closeOverflow();
    }
  });

  // ----------------------------------------------------------------
  // Tabbed content (pymdownx.tabbed alternate style + ExampleCard)
  // ----------------------------------------------------------------
  document.querySelectorAll('.tabbed-set').forEach(function (set) {
    var inputs = set.querySelectorAll(':scope > input[type="radio"]');
    var labels = set.querySelectorAll(':scope > .tabbed-labels > label');
    var blocks = set.querySelectorAll(':scope > .tabbed-content > .tabbed-block');

    function activate(index) {
      labels.forEach(function (l, i) {
        l.classList.toggle('is-active', i === index);
      });
      blocks.forEach(function (b, i) {
        b.classList.toggle('is-active', i === index);
      });
      inputs.forEach(function (inp, i) {
        inp.checked = i === index;
      });
    }

    activate(0);

    labels.forEach(function (label, index) {
      label.addEventListener('click', function (e) {
        e.preventDefault();
        activate(index);
      });
    });
  });

  // ----------------------------------------------------------------
  // Right-rail TOC scroll-spy
  // ----------------------------------------------------------------
  var tocLinks = document.querySelectorAll('.djc-toc__link');
  if (tocLinks.length > 0) {
    // Expand a collapsible class when it (or one of its members) is active, or
    // when the reader pinned it open; collapse the rest. Keeps the rail compact
    // on big reference pages while always revealing where you are.
    var setExpanded = function (item, expanded) {
      item.classList.toggle('djc-toc__item--expanded', expanded);
      var toggle = item.querySelector('.djc-toc__toggle');
      if (toggle) toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    };

    var syncExpansion = function (activeLink) {
      var activeItem = activeLink ? activeLink.closest('.djc-toc__item--collapsible') : null;
      document.querySelectorAll('.djc-toc__item--collapsible').forEach(function (item) {
        setExpanded(item, item === activeItem || item.hasAttribute('data-toc-pinned'));
      });
    };

    // Manual toggle: pin a class open (or collapse it) regardless of scroll.
    document.querySelectorAll('.djc-toc__toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var item = btn.closest('.djc-toc__item--collapsible');
        if (!item) return;
        var expand = !item.classList.contains('djc-toc__item--expanded');
        if (expand) {
          item.setAttribute('data-toc-pinned', '');
        } else {
          item.removeAttribute('data-toc-pinned');
        }
        setExpanded(item, expand);
      });
    });

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
            var activeLink = null;
            tocLinks.forEach(function (link) {
              var isActive = link.getAttribute('href') === '#' + activeId;
              link.classList.toggle('is-active', isActive);
              if (isActive) activeLink = link;
            });
            syncExpansion(activeLink);
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

    // Anchor the label + copy button to the .highlight wrapper, NOT the <pre>.
    // <pre> is the horizontally-scrolling element, so an absolute child of it
    // scrolls away with the code; .highlight is the stationary box around it.
    // (.highlight is already position:relative in site.css.)

    // Language label (top-right, always visible)
    if (lang) {
      var label = document.createElement('span');
      label.className = 'djc-code-lang';
      label.textContent = lang;
      block.appendChild(label);
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

    block.appendChild(btn);
  });

  // ----------------------------------------------------------------
  // Resizable sidebar dividers
  // ----------------------------------------------------------------
  var RESIZE_KEY = 'djc-panel-widths';

  function getStoredWidths() {
    try { return JSON.parse(localStorage.getItem(RESIZE_KEY) || '{}'); }
    catch (e) { return {}; }
  }

  function saveStoredWidths(widths) {
    localStorage.setItem(RESIZE_KEY, JSON.stringify(widths));
  }

  // Restore saved widths on load
  var storedWidths = getStoredWidths();
  Object.keys(storedWidths).forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.style.width = storedWidths[id] + 'px';
  });

  // Wire up each resize handle
  document.querySelectorAll('.djc-resize-handle').forEach(function (handle) {
    var targetId = handle.getAttribute('data-target');
    var direction = handle.getAttribute('data-direction');
    var target = document.getElementById(targetId);
    if (!target) return;

    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      var startX = e.clientX;
      var startWidth = target.getBoundingClientRect().width;

      handle.classList.add('is-dragging');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      function onMove(ev) {
        var delta = ev.clientX - startX;
        // "left" panels grow when you drag right; "right" panels grow when you drag left
        var newWidth = direction === 'left'
          ? startWidth + delta
          : startWidth - delta;

        // Clamp to reasonable bounds
        newWidth = Math.max(160, Math.min(500, newWidth));
        target.style.width = newWidth + 'px';
      }

      function onUp() {
        handle.classList.remove('is-dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);

        // Persist the width
        var widths = getStoredWidths();
        widths[targetId] = Math.round(target.getBoundingClientRect().width);
        saveStoredWidths(widths);
      }

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  });

  // -- Version picker --------------------------------------------------------
  // Populate the header <select> from versions.json and redirect on change.
  // The picker (VersionPicker component) is seeded with the current version, so
  // if the page isn't served under /v/<version>/ (local dev) or the manifest
  // can't be fetched, it stays a static one-option control.
  document.querySelectorAll('[data-version-picker]').forEach(function (picker) {
    var select = picker.querySelector('select');
    if (!select) return;
    var current = picker.getAttribute('data-current');

    // The page lives at <base>/v/<version>/<page>. Capture "<base>/v/" so the
    // picker is agnostic to the site's base path (e.g. /django-components/).
    var match = window.location.pathname.match(/^(.*\/v\/)[^/]+\//);
    if (!match) return; // not under /v/<version>/ -> leave the seeded label
    var versionsRoot = match[1];

    // On change, go to the selected version's home. The same page may not
    // exist across versions, so we don't try to preserve the sub-path here
    // (avoids cross-version 404s); that's a later (Phase 7) enhancement.
    select.addEventListener('change', function () {
      window.location.href = versionsRoot + select.value + '/';
    });

    fetch(versionsRoot + 'versions.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (manifest) {
        if (!manifest || !manifest.length) return;
        select.innerHTML = '';
        manifest.forEach(function (row) {
          // Hidden versions (e.g. unreleased previews) stay out of the list
          // unless they're the page you're currently on.
          if (row.properties && row.properties.hidden && row.version !== current) return;
          var isCurrent = row.version === current ||
            (row.aliases && row.aliases.indexOf(current) !== -1);
          select.add(new Option(row.title, row.version, isCurrent, isCurrent));
        });
      })
      .catch(function () { /* keep the seeded current-version option */ });
  });

  // -- Back-to-top button ----------------------------------------------------
  // Reveal the button once the reader is a screenful down the page, then
  // smooth-scroll to the top on click. Mirrors Material's navigation.top.
  var backToTop = document.querySelector('.djc-back-to-top');
  if (backToTop) {
    var syncBackToTop = function () {
      backToTop.hidden = window.scrollY <= window.innerHeight;
    };
    syncBackToTop();
    window.addEventListener('scroll', syncBackToTop, { passive: true });
    backToTop.addEventListener('click', function () {
      // Honor reduced-motion: skip the smooth animation if the OS asks for it.
      var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  }
})();
