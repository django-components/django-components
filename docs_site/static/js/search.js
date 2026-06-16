/**
 * Docs-site search (Phase 5a).
 *
 * Drives the SearchModal component and the cross-cutting in-page highlight:
 *
 * - In-page highlight (?h=): on every page load, wraps the terms passed in the
 *   ?h= query param (set on result links) in <mark> within the article. Runs
 *   independently of the modal.
 * - Modal: lazily loads the Pagefind bundle on first use, runs debounced
 *   queries, renders anchor-level results with highlighted excerpts, and
 *   handles the empty / no-results / error states.
 * - Shortcuts: "/" and Ctrl/Cmd+K open the modal from anywhere; Esc closes.
 * - Deep link (?q=): the open modal mirrors its query into the URL, and a page
 *   loaded with ?q= opens the modal pre-filled.
 * - A11y: focus is trapped in the open dialog and restored to the opener on
 *   close; the trigger reflects state via aria-expanded.
 *
 * Spec: docs_site/design/DESIGN_spike_11.md section 8; main doc 11.1.G.2/G.5.
 */

(function () {
  'use strict';

  var isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent || '');

  // ----------------------------------------------------------------
  // In-page highlight (?h=) - runs on every page, modal or not
  // ----------------------------------------------------------------
  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function highlightInPage() {
    var terms = (new URL(window.location.href).searchParams.get('h') || '')
      .split(/\s+/)
      .map(function (t) {
        return t.trim();
      })
      .filter(function (t) {
        // Skip very short tokens: highlighting single characters is noise.
        return t.length >= 2;
      });
    if (!terms.length) {
      return;
    }
    var root = document.querySelector('.djc-content article.prose') || document.querySelector('article.prose');
    if (!root) {
      return;
    }

    var rx = new RegExp('(' + terms.map(escapeRegExp).join('|') + ')', 'gi');
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue.trim()) {
          return NodeFilter.FILTER_REJECT;
        }
        var tag = node.parentNode && node.parentNode.nodeName;
        // Don't descend into code, scripts, styles, or already-marked text.
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'MARK') {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    var targets = [];
    while (walker.nextNode()) {
      if (rx.test(walker.currentNode.nodeValue)) {
        targets.push(walker.currentNode);
      }
      rx.lastIndex = 0;
    }

    targets.forEach(function (node) {
      var text = node.nodeValue;
      var frag = document.createDocumentFragment();
      var last = 0;
      var m;
      rx.lastIndex = 0;
      while ((m = rx.exec(text)) !== null) {
        if (m.index > last) {
          frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        }
        var mark = document.createElement('mark');
        mark.className = 'djc-highlight';
        mark.textContent = m[0];
        frag.appendChild(mark);
        last = m.index + m[0].length;
        if (m[0].length === 0) {
          rx.lastIndex++;
        }
      }
      if (last < text.length) {
        frag.appendChild(document.createTextNode(text.slice(last)));
      }
      node.parentNode.replaceChild(frag, node);
    });

    // If we navigated without an anchor, bring the first match into view.
    if (!window.location.hash) {
      var first = root.querySelector('mark.djc-highlight');
      if (first) {
        first.scrollIntoView({ block: 'center' });
      }
    }
  }

  highlightInPage();

  // ----------------------------------------------------------------
  // Modal - only wired when the overlay is present
  // ----------------------------------------------------------------
  var overlay = document.querySelector('.djc-search__overlay');
  if (!overlay) {
    return;
  }

  var dialog = overlay.querySelector('.djc-search__dialog');
  var input = overlay.querySelector('.djc-search__input');
  var resultsEl = overlay.querySelector('.djc-search__results');
  var listEl = overlay.querySelector('[data-search-list]');
  var emptyEl = overlay.querySelector('[data-search-empty]');
  var noResultsEl = overlay.querySelector('[data-search-noresults]');
  var errorEl = overlay.querySelector('[data-search-error]');
  var triggers = document.querySelectorAll('[data-search-open]');
  var pagefindPath = overlay.getAttribute('data-pagefind-path') || '/pagefind/pagefind.js';

  // Show the spinner only for queries slower than this, so the common
  // (tens-of-ms) case never flashes a "Searching…" state.
  var SPINNER_DELAY_MS = 400;
  // Cap the number of pages shown; each contributes its own anchor sub-results.
  var MAX_PAGES = 6;

  var pagefindPromise = null;
  var spinnerTimer = null;
  var activeIndex = -1;
  var lastFocused = null;

  // Per-platform shortcut hint on the trigger label.
  document.querySelectorAll('.djc-search-trigger__key').forEach(function (el) {
    el.textContent = isMac ? '⌘K' : 'Ctrl K';
  });

  // ----------------------------------------------------------------
  // Pagefind loading (lazy, once)
  // ----------------------------------------------------------------
  function loadPagefind() {
    if (!pagefindPromise) {
      // Dynamic import of the Pagefind ES module. Rejects (-> error state)
      // when the index is absent, e.g. on the dev server, which serves pages
      // on the fly without a built /pagefind/ bundle.
      pagefindPromise = import(pagefindPath).then(function (pf) {
        return pf;
      });
    }
    return pagefindPromise;
  }

  // ----------------------------------------------------------------
  // Open / close
  // ----------------------------------------------------------------
  function openModal() {
    if (!overlay.hidden) {
      return;
    }
    lastFocused = document.activeElement;
    overlay.hidden = false;
    document.body.classList.add('djc-search-open');
    triggers.forEach(function (t) {
      t.setAttribute('aria-expanded', 'true');
    });
    input.focus();
    input.select();
    // Warm the index so the first keystroke isn't waiting on the import.
    loadPagefind().catch(function () {});
    if (input.value.trim()) {
      runSearch(input.value.trim());
    } else {
      showEmpty();
    }
  }

  function closeModal() {
    overlay.hidden = true;
    document.body.classList.remove('djc-search-open');
    triggers.forEach(function (t) {
      t.setAttribute('aria-expanded', 'false');
    });
    stopSpinner();
    syncQueryParam('');
    // Restore focus to whatever opened the modal (the trigger, usually).
    if (lastFocused && typeof lastFocused.focus === 'function') {
      lastFocused.focus();
    }
  }

  // ----------------------------------------------------------------
  // URL state (?q= deep link)
  // ----------------------------------------------------------------
  function syncQueryParam(value) {
    var url = new URL(window.location.href);
    if (value) {
      url.searchParams.set('q', value);
    } else {
      url.searchParams.delete('q');
    }
    window.history.replaceState(null, '', url);
  }

  // Append the active query to a result URL as ?h=, so matched terms are
  // highlighted on the destination page (preserving any #anchor).
  function withHighlight(url, query) {
    var terms = query.trim();
    if (!terms) {
      return url;
    }
    var hash = '';
    var hashAt = url.indexOf('#');
    if (hashAt !== -1) {
      hash = url.slice(hashAt);
      url = url.slice(0, hashAt);
    }
    var sep = url.indexOf('?') !== -1 ? '&' : '?';
    return url + sep + 'h=' + encodeURIComponent(terms) + hash;
  }

  // ----------------------------------------------------------------
  // State helpers
  // ----------------------------------------------------------------
  function hideStates() {
    emptyEl.hidden = true;
    noResultsEl.hidden = true;
    errorEl.hidden = true;
  }

  function showEmpty() {
    hideStates();
    listEl.innerHTML = '';
    emptyEl.hidden = false;
    resetActive();
  }

  function showNoResults(query) {
    hideStates();
    listEl.innerHTML = '';
    noResultsEl.textContent = 'No results for "' + query + '". Try a different term?';
    noResultsEl.hidden = false;
    resetActive();
  }

  function showError(query) {
    hideStates();
    listEl.innerHTML = '';
    // Pagefind failed to load (e.g. no index). Fall back to a Google site:
    // query so the user isn't stranded.
    errorEl.textContent = 'Search is unavailable right now. ';
    var link = document.createElement('a');
    link.href =
      'https://www.google.com/search?q=site:django-components.github.io+' + encodeURIComponent(query || '');
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'Search with Google instead';
    errorEl.appendChild(link);
    errorEl.hidden = false;
    resetActive();
  }

  function startSpinner() {
    spinnerTimer = setTimeout(function () {
      listEl.innerHTML = '';
      resultsEl.classList.add('is-loading');
    }, SPINNER_DELAY_MS);
  }

  function stopSpinner() {
    clearTimeout(spinnerTimer);
    resultsEl.classList.remove('is-loading');
  }

  // ----------------------------------------------------------------
  // Search + render
  // ----------------------------------------------------------------
  function runSearch(query) {
    syncQueryParam(query);
    if (!query) {
      showEmpty();
      return;
    }
    hideStates();
    startSpinner();

    loadPagefind()
      .then(function (pf) {
        return pf.debouncedSearch(query);
      })
      .then(function (search) {
        stopSpinner();
        // debouncedSearch resolves null when a newer query superseded this one.
        if (search === null) {
          return null;
        }
        return Promise.all(
          search.results.slice(0, MAX_PAGES).map(function (r) {
            return r.data();
          })
        ).then(function (pages) {
          renderResults(pages, query);
        });
      })
      .catch(function () {
        stopSpinner();
        showError(query);
      });
  }

  function renderResults(pages, query) {
    if (!pages.length) {
      showNoResults(query);
      return;
    }
    listEl.innerHTML = '';
    pages.forEach(function (page) {
      listEl.appendChild(buildGroup(page, query));
    });
    resetActive();
  }

  // Build one page's result group: a title/breadcrumb header plus one row per
  // anchor sub-result (or a single row for the page itself when Pagefind
  // returns no sub-results).
  function buildGroup(page, query) {
    var group = document.createElement('div');
    group.className = 'djc-search__group';

    var header = document.createElement('div');
    header.className = 'djc-search__group-title';
    var crumb = document.createElement('span');
    crumb.className = 'djc-search__breadcrumb';
    crumb.textContent = urlToBreadcrumb(page.url);
    header.appendChild(crumb);
    header.appendChild(document.createTextNode((page.meta && page.meta.title) || 'Untitled'));
    group.appendChild(header);

    var subs = page.sub_results && page.sub_results.length ? page.sub_results : null;
    if (subs) {
      subs.forEach(function (sub) {
        group.appendChild(buildResult(sub.url, sub.title || (page.meta && page.meta.title), sub.excerpt, query));
      });
    } else {
      group.appendChild(buildResult(page.url, (page.meta && page.meta.title) || 'Untitled', page.excerpt, query));
    }
    return group;
  }

  function buildResult(url, title, excerpt, query) {
    var a = document.createElement('a');
    a.className = 'djc-search__result';
    a.href = withHighlight(url, query);

    var titleEl = document.createElement('div');
    titleEl.className = 'djc-search__result-title';
    titleEl.textContent = title || 'Untitled';
    a.appendChild(titleEl);

    if (excerpt) {
      var excerptEl = document.createElement('div');
      excerptEl.className = 'djc-search__result-excerpt';
      // Pagefind escapes content and only injects <mark> for matched terms,
      // so this HTML is safe to set directly.
      excerptEl.innerHTML = excerpt;
      a.appendChild(excerptEl);
    }
    return a;
  }

  // Humanize a URL into a short breadcrumb, e.g.
  // "/docs/getting_started/installation/" -> "Docs › Getting started".
  function urlToBreadcrumb(url) {
    var path = url.split('#')[0].split('?')[0];
    var parts = path.split('/').filter(Boolean);
    // Drop the leaf (it's the page, shown as the group title)
    parts = parts.slice(0, -1);
    if (!parts.length) {
      return '';
    }
    return parts
      .map(function (seg) {
        var words = seg.replace(/[_-]+/g, ' ').trim();
        return words.charAt(0).toUpperCase() + words.slice(1);
      })
      .join(' › ');
  }

  // ----------------------------------------------------------------
  // Keyboard navigation + focus trap within the open modal
  // ----------------------------------------------------------------
  // The navigable items depend on the current state: live results when
  // searching, quick links in the empty state.
  function navItems() {
    return Array.prototype.slice.call(
      overlay.querySelectorAll('.djc-search__result, .djc-search__quicklink')
    );
  }

  function resetActive() {
    activeIndex = -1;
  }

  function setActive(index) {
    var items = navItems();
    if (!items.length) {
      return;
    }
    items.forEach(function (el) {
      el.classList.remove('is-active');
    });
    activeIndex = (index + items.length) % items.length;
    var active = items[activeIndex];
    active.classList.add('is-active');
    active.scrollIntoView({ block: 'nearest' });
  }

  function moveActive(delta) {
    var items = navItems();
    if (!items.length) {
      return;
    }
    setActive(activeIndex === -1 ? (delta > 0 ? 0 : items.length - 1) : activeIndex + delta);
  }

  function focusables() {
    return Array.prototype.slice
      .call(dialog.querySelectorAll('input, button, a[href]'))
      .filter(function (el) {
        return !el.hidden && el.offsetParent !== null;
      });
  }

  function trapTab(e) {
    var list = focusables();
    if (!list.length) {
      return;
    }
    var first = list[0];
    var last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  // ----------------------------------------------------------------
  // Wiring
  // ----------------------------------------------------------------
  triggers.forEach(function (el) {
    el.addEventListener('click', function () {
      openModal();
    });
  });

  overlay.querySelectorAll('[data-search-close]').forEach(function (el) {
    el.addEventListener('click', function () {
      closeModal();
    });
  });

  input.addEventListener('input', function () {
    runSearch(input.value.trim());
  });

  overlay.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      closeModal();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      moveActive(1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      moveActive(-1);
    } else if (e.key === 'Enter') {
      var items = navItems();
      if (activeIndex >= 0 && items[activeIndex]) {
        e.preventDefault();
        items[activeIndex].click();
      }
    } else if (e.key === 'Tab') {
      trapTab(e);
    }
  });

  // Global shortcuts to open: "/" (when not typing elsewhere) and Ctrl/Cmd+K.
  function isTypingTarget(el) {
    if (!el) {
      return false;
    }
    var tag = el.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
  }

  document.addEventListener('keydown', function (e) {
    var cmdK = (e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey);
    var slash = e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey && !isTypingTarget(e.target);
    if ((cmdK || slash) && overlay.hidden) {
      e.preventDefault();
      openModal();
    }
  });

  // Open pre-filled when the page is loaded with a ?q= deep link.
  var initialQuery = new URL(window.location.href).searchParams.get('q');
  if (initialQuery) {
    input.value = initialQuery;
    openModal();
  }
})();
