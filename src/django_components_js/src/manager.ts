/** The actual code of the JS dependency manager */
import { callWithAsyncErrorHandling } from "./errorHandling";
import { observeScriptTag } from "./mutationObserver";

type MaybePromise<T> = Promise<T> | T;

export interface ComponentContext<TEl extends HTMLElement = HTMLElement> {
  name: string;
  id: string;
  els: TEl[];
}

export type ComponentFn<
  TData extends object = object,
  TEl extends HTMLElement = HTMLElement,
> = (data: TData, ctx: ComponentContext<TEl>) => MaybePromise<any>;

export type DataFn = () => object;

export type ScriptType = "js" | "css";

/** Queue for component calls that are waiting for dependencies to be registered */
export interface PendingCall {
  compClsId: string;
  compId: string;
  jsVarsHash: string | null;
  queuedAt: number; // timestamp for warning purposes
  waitForPromise?: Promise<any>; // promise that must resolve before this call can execute (for script loading)
  resolve?: (value: any) => void; // resolve function for the promise returned by callComponent
  reject?: (error: any) => void; // reject function for the promise returned by callComponent
}

export interface TagJson {
  tag: string;
  attrs: Record<string, string | boolean>;
  content: string;
}

/**
 * Usage:
 *
 * ```js
 * DjangoComponents.registerComponent("table", async (data, { id, name, els }) => {
 *   ...
 * });
 * ```
 *
 * Multiple callbacks can be registered for the same component:
 *
 * ```js
 * DjangoComponents.registerComponent("table", async (data, { id, name, els }) => {
 *   // First callback
 * });
 * DjangoComponents.registerComponent("table", async (data, { id, name, els }) => {
 *   // Second callback - will be called after the first
 * });
 * ```
 *
 * ```js
 * DjangoComponents.registerComponentData("table", "3d09cf", () => {
 *   return JSON.parse('{ "abc": 123 }');
 * });
 * ```
 *
 * ```js
 * DjangoComponents.callComponent("table", 12345, "3d09cf");
 * ```
 *
 * ```js
 * DjangoComponents.loadJs({ tag: 'script', attrs: { src: '/abc/def' }, content: 'console.log("Hello, world!");' });
 * ```
 *
 * ```js
 * DjangoComponents.loadCss({ tag: 'link', attrs: { href: '/abc/def', rel: 'stylesheet' }, content: '' });
 * ```
 *
 * ```js
 * DjangoComponents.markScriptLoaded("js", '/abc/def');
 * ```
 */
export const createComponentsManager = () => {
  const loadedJs = new Set<string>();
  const loadedCss = new Set<string>();
  const components: Record<string, ComponentFn[]> = {};
  const componentInputs: Record<string, DataFn> = {};
  const pendingScripts = new Map<
    string,
    { promise: Promise<void>; resolve: () => void }
  >();

  // When a Python component defines a `Component.js` or `Component.js_file`,
  // it can define a `$onComponent()` callback within the JS code.
  // This JS callback is to be called when the component is instantiated in the DOM.
  //
  // But the `Component.js` script may also need to wait for other JS/CSS scripts / dependencies to be loaded.
  // E.g. third party scripts set in `Component.Media.js`, or to wait for JS variables from `Component.get_js_data()`.
  //
  // As a result, the most ergonomic way to call the components' callbacks is to enqueue them,
  // and keep an eye on what conditions are met before we can call the component.
  //
  // We ensure that the component callbacks are called in the order they were enqueued.
  // This is important because the component callbacks may depend on each other.
  // Thus, when a next-in-line component call is blocked, we stop and do not proceed until it is resolved.
  const pendingComponentCalls: PendingCall[] = [];
  let isProcessingPendingCalls = false;
  let warningIntervalId: ReturnType<typeof setInterval> | null = null;

  // In JS you can't inspect Promise easily. The only way is to use `.then()` and `.catch()`.
  //
  // When component calls are enqueued, we may pass in a Promise that needs to resolve before
  // we can call the component. This is because the Promise waits until other JS/CSS scripts are loaded.
  //
  // So to detect if these promises from `PendingCall.waitForPromise` are already resolved,
  // we keep a Map to which we write the results.
  //
  // The key has format `compClsId:compId:jsVarsHash`.
  // The value is for error (if any), otherwise null.
  //
  // - If the key is not present in the Map, then the promise has not ended yet.
  // - If the key is present and the value is null, then the promise has ended successfully.
  // - If the key is present and the value is non-null, then the promise has ended in error.
  //
  // This way, when we are checking if a pending comp call is ready, we can simply check
  // this Map instead of trying to inspect the promise itself.
  const promiseCompletionStatus = new Map<string, Error | null>();

  const createLinkElement = (data: TagJson): HTMLLinkElement => {
    if (data.tag !== "link") {
      throw Error(
        `[DjangoComponents] loadCss received tag '${data.tag}' but expected 'link'`,
      );
    }
    const linkNode = document.createElement("link");
    // Set attributes
    for (const [key, value] of Object.entries(data.attrs)) {
      if (value === true) {
        // Boolean attribute
        linkNode.setAttribute(key, "");
      } else if (value !== false) {
        // Regular attribute
        linkNode.setAttribute(key, String(value));
      }
    }
    return linkNode;
  };

  const createScriptElement = (data: TagJson): HTMLScriptElement => {
    if (data.tag !== "script") {
      throw Error(
        `[DjangoComponents] loadJs received tag '${data.tag}' but expected 'script'`,
      );
    }
    const scriptNode = document.createElement("script");
    // Set attributes
    for (const [key, value] of Object.entries(data.attrs)) {
      if (value === true) {
        // Boolean attribute
        scriptNode.setAttribute(key, "");
      } else if (value !== false) {
        // Regular attribute
        scriptNode.setAttribute(key, String(value));
      }
    }
    // Set content if present
    if (data.content) {
      scriptNode.textContent = data.content;
    }
    return scriptNode;
  };

  const loadJs = (tagData: string | TagJson) => {
    // Support both JSON string (base64 decoded) and JSON object
    // TODO_V1: Support only JSON object
    const data: TagJson =
      typeof tagData === "string" ? JSON.parse(tagData) : tagData;
    const scriptNode = createScriptElement(data);

    // Use URL as it came from the server-side
    const src = data.attrs.src;
    if (!src || typeof src !== "string" || isScriptLoaded("js", src)) {
      return {
        el: scriptNode,
        promise: Promise.resolve(),
      };
    }

    markScriptLoaded("js", src);

    // In case of JS scripts, we return a Promise that resolves when the script is loaded
    // See https://stackoverflow.com/a/57267538/9788634
    const promise = new Promise<void>((resolve, reject) => {
      scriptNode.onload = () => {
        resolve();
      };

      // Insert at the end of `<body>` to follow convention
      //
      // NOTE: Because we are inserting the script into the DOM from within JS,
      // the order of execution of the inserted scripts behaves a bit different:
      // - The `<script>` that were originally in the HTML file will run in the order they appear in the file.
      //   And they will run BEFORE the dynamically inserted scripts.
      // - The order of execution of the dynamically inserted scripts depends on the order of INSERTION,
      //   and NOT on WHERE we insert the script in the DOM.
      globalThis.document.body.append(scriptNode);
    });

    return {
      el: scriptNode,
      promise,
    };
  };

  const loadCss = (tagData: string | TagJson) => {
    // Support both JSON string (base64 decoded) and JSON object
    // TODO_V1: Support only JSON object
    const data: TagJson =
      typeof tagData === "string" ? JSON.parse(tagData) : tagData;
    const linkNode = createLinkElement(data);

    // Use URL as it came from the server-side
    const href = data.attrs.href;
    if (!href || typeof href !== "string" || isScriptLoaded("css", href))
      return;

    // Insert at the end of <head> to follow convention
    globalThis.document.head.append(linkNode);
    markScriptLoaded("css", href);

    // For CSS, we return a dummy Promise, since we don't need to wait for anything
    return {
      el: linkNode,
      promise: Promise.resolve(),
    };
  };

  const markScriptLoaded = (type: ScriptType, url: string): void => {
    if (type !== "js" && type !== "css") {
      throw Error(
        `[DjangoComponents] markScriptLoaded received invalid script type '${type}'. Must be one of 'js', 'css'`,
      );
    }

    const urlsSet = type === "js" ? loadedJs : loadedCss;
    urlsSet.add(url);

    // If there are were any calls to `waitForScriptsToLoad` that are waiting for this script, resolve them
    const entry = pendingScripts.get(`${type}:${url}`);
    if (entry) {
      entry.resolve();
    }
  };

  const isScriptLoaded = (type: ScriptType, url: string): boolean => {
    if (type !== "js" && type !== "css") {
      throw Error(
        `[DjangoComponents] isScriptLoaded received invalid script type '${type}'. Must be one of 'js', 'css'`,
      );
    }

    const urlsSet = type === "js" ? loadedJs : loadedCss;
    return urlsSet.has(url);
  };

  /**
   * Create a Promise that resolves when all scripts, identified by their URLs, are loaded.
   *
   * This does NOT load the scripts, it only waits for them to be loaded.
   *
   * To resolve the Promise, the scripts must have been loaded using `loadJs / loadCss`
   * or `markScriptLoaded`.
   */
  const waitForScriptsToLoad = async (type: ScriptType, urls: string[]) => {
    const promises = urls.map((url) => {
      if (isScriptLoaded(type, url)) return Promise.resolve();

      if (pendingScripts.has(url)) return pendingScripts.get(url)!.promise;

      const entry = {} as any;
      pendingScripts.set(`${type}:${url}`, entry);
      const scriptPromise = new Promise<void>((resolve) => {
        entry.resolve = resolve;
      });
      entry.promise = scriptPromise;

      return scriptPromise;
    });

    await Promise.all(promises);
  };

  /**
   * Generate a unique key for a component call to track promise completion status.
   */
  const _getCallKey = (
    compClsId: string,
    compId: string,
    jsVarsHash: string | null,
  ): string => {
    return `${compClsId}:${compId}:${jsVarsHash ?? "null"}`;
  };

  /**
   * Check if a component call is blocked and cannot be executed.
   *
   * A call is NOT BLOCKED if it meets ALL of the following conditions:
   * - The component callback(s) are registered
   *   (NOTE: If server has set a component call command, then we assume that
   *   the component must've had a `Component.js` or `Component.js_file` defined
   *   AND had `$onComponent()` callback(s) defined in it)
   * - If `jsVarsHash` is provided, the data factory is registered
   * - If `waitForPromise` is provided, it must have completed successfully
   *   (checked via `promiseCompletionStatus` Map)
   */
  const _isCallBlocked = (call: PendingCall): boolean => {
    // Check if component is registered
    const initFns = components[call.compClsId];
    if (!initFns || initFns.length === 0) {
      return true;
    }

    // If JS variables are required, check if they're registered
    if (call.jsVarsHash != null) {
      const dataKey = `${call.compClsId}:${call.jsVarsHash}`;
      if (!componentInputs[dataKey]) {
        return true;
      }
    }

    // If waitForPromise is provided, check its completion status in the Map
    if (call.waitForPromise) {
      const callKey = _getCallKey(call.compClsId, call.compId, call.jsVarsHash);
      const status = promiseCompletionStatus.get(callKey);

      // If key doesn't exist, promise hasn't completed yet
      if (status === undefined) {
        return true;
      }

      // If key exists but value is non-null, promise failed - this will be handled in _processPendingCalls
      if (status !== null) {
        return true; // Will trigger error handling
      }

      // Key exists and value is null, promise succeeded
    }

    return false;
  };

  /**
   * Start the warning interval if not already started.
   *
   * The interval periodically logs warnings for component calls that are still waiting for dependencies.
   *
   * The interval checks for blocked calls every 5 seconds.
   */
  const _startWarningInterval = (): void => {
    if (warningIntervalId != null) {
      return; // Already started
    }

    warningIntervalId = setInterval(() => {
      const now = Date.now();
      const blockedCalls = pendingComponentCalls.filter((call) =>
        _isCallBlocked(call),
      );

      if (blockedCalls.length > 0) {
        const oldestBlocked = blockedCalls[0];
        const waitTime = Math.floor((now - oldestBlocked.queuedAt) / 1000);
        console.warn(
          `[DjangoComponents] ${blockedCalls.length} component call(s) are still waiting for dependencies. ` +
            `Oldest call has been waiting for ${waitTime}s: ` +
            `'${oldestBlocked.compClsId}' (ID: ${oldestBlocked.compId})`,
        );
      }
    }, 5000); // Check every 5 seconds
  };

  /**
   * Process pending component calls in order.
   * Executes all consecutive unblocked calls from the start of the queue,
   * stopping at the first blocked call.
   */
  const _processPendingCalls = async (): Promise<void> => {
    if (isProcessingPendingCalls) {
      return; // Already processing
    }
    isProcessingPendingCalls = true;

    // Process calls in order from the start of the queue
    while (pendingComponentCalls.length > 0) {
      const call = pendingComponentCalls[0];
      const callKey = _getCallKey(call.compClsId, call.compId, call.jsVarsHash);

      // Check if waitForPromise failed
      // NOTE: If has() returns true, then the Promise finished (successfully or failed).
      if (call.waitForPromise != null && promiseCompletionStatus.has(callKey)) {
        const status = promiseCompletionStatus.get(callKey);
        if (status != null) {
          // Promise failed - clear the queue and throw error
          pendingComponentCalls.length = 0;
          promiseCompletionStatus.clear();
          isProcessingPendingCalls = false;
          throw new Error(
            `[DjangoComponents] Script loading failed for component call '${call.compClsId}' (ID: ${call.compId}): ${status.message}`,
          );
        }
      }

      // Check if this call is blocked
      if (_isCallBlocked(call)) {
        // Stop at the first blocked call to preserve order
        break;
      }

      // We know this cal is NOT blocked, we can proceed to execute it
      // Remove the call from the queue before executing
      pendingComponentCalls.shift();
      if (call.waitForPromise) {
        promiseCompletionStatus.delete(callKey);
      }

      // Execute the call
      try {
        const result = await callUnblockedComponent(
          call.compClsId,
          call.compId,
          call.jsVarsHash,
        );
        // Resolve the promise if one was stored
        if (call.resolve) {
          call.resolve(result);
        }
      } catch (error) {
        // Reject the promise if one was stored
        if (call.reject) {
          call.reject(error);
        } else {
          // Log errors but continue processing if no promise to reject
          console.error(
            `[DjangoComponents] Error executing component call for '${call.compClsId}' (ID: ${call.compId}):`,
            error,
          );
        }
      }
    }

    // Clean up warning interval if all calls are processed
    if (!pendingComponentCalls.length && warningIntervalId != null) {
      clearInterval(warningIntervalId);
      warningIntervalId = null;
    }

    isProcessingPendingCalls = false;
  };

  /**
   * Register a component callback function.
   *
   * The callback function is called when a django-components component is instantiated
   * in the DOM. It is called for each instance of the component.
   *
   * The callback function is called with the following arguments:
   * - `data`: The data passed to the component.
   * - `ctx`: The component context.
   *
   * The component context contains the following properties:
   * - `id`: The ID of the component.
   * - `name`: The name of the component.
   * - `els`: The elements of the component.
   *
   * @param compClsId - The class ID of the component.
   * @param compFn - The callback function to call when the component is instantiated.
   *
   * @example
   * DjangoComponents.registerComponent("table", async (data, { id, name, els }) => {
   *   ...
   * });
   */
  const registerComponent = (compClsId: string, compFn: ComponentFn) => {
    // Allow multiple callbacks to be registered for the same component
    // This can be useful for extensions, which then can define their own `$onComponent()` callbacks
    // without interfering with user-defined callbacks.
    if (!components[compClsId]) {
      components[compClsId] = [];
    }
    components[compClsId].push(compFn);

    // Check if any pending calls are now unblocked
    _processPendingCalls();
  };

  /**
   * @example
   * DjangoComponents.registerComponentData("table", "a1b2c3", () => {{
   *   return JSON.parse('{ "a": 2 }');
   * }});
   */
  const registerComponentData = (
    compClsId: string,
    jsVarsHash: string,
    dataFactory: DataFn,
  ) => {
    const key = `${compClsId}:${jsVarsHash}`;
    componentInputs[key] = dataFactory;

    // Check if any pending calls are now unblocked
    _processPendingCalls();
  };

  const queueComponentCall = (
    compClsId: string,
    compId: string,
    jsVarsHash: string | null,
    waitForPromise: Promise<any> | undefined = undefined,
  ) => {
    const callKey = _getCallKey(compClsId, compId, jsVarsHash);

    // If `waitForPromise` is provided, set up handlers to track its completion
    if (waitForPromise) {
      waitForPromise
        .then(() => {
          // Promise succeeded - mark as completed with null (success)
          promiseCompletionStatus.set(callKey, null);
          // Check if any pending calls are now unblocked
          _processPendingCalls();
        })
        .catch((error) => {
          // Promise failed - mark as completed with error
          promiseCompletionStatus.set(callKey, error);
          // Check if any pending calls are now unblocked (will trigger error handling)
          _processPendingCalls();
        });
    }

    // Return a promise that will resolve when the call is eventually executed
    const callPromise = new Promise((resolve, reject) => {
      pendingComponentCalls.push({
        compClsId,
        compId,
        jsVarsHash,
        queuedAt: Date.now(),
        waitForPromise,
        resolve,
        reject,
      });
    });

    // Start warning interval if we have queued calls
    if (pendingComponentCalls.length > 0) {
      _startWarningInterval();
    }

    return callPromise;
  };

  const callUnblockedComponent = async (
    compClsId: string,
    compId: string,
    jsVarsHash: string | null,
  ): Promise<any> => {
    const initFns = components[compClsId];
    if (!initFns || initFns.length === 0) {
      throw Error(
        `[DjangoComponents] '${compClsId}': No component registered for that name`,
      );
    }

    const elems = Array.from(
      document.querySelectorAll<HTMLElement>(`[data-djc-id-${compId}]`),
    );
    if (!elems.length) {
      throw Error(
        `[DjangoComponents] '${compClsId}': No elements with component ID '${compId}' found`,
      );
    }

    // If the component has JS variables, find the data's factory function based on the hash
    let data = {};
    if (jsVarsHash != null) {
      const dataKey = `${compClsId}:${jsVarsHash}`;
      const dataFactory = componentInputs[dataKey];
      if (!dataFactory) {
        throw Error(
          `[DjangoComponents] '${compClsId}': Cannot find JS variables for hash '${jsVarsHash}'`,
        );
      }

      data = dataFactory();
    }

    const ctx = {
      name: compClsId,
      id: compId,
      els: elems,
    } satisfies ComponentContext;

    // Call all registered callbacks in sequence
    let lastResult: any;
    for (const initFn of initFns) {
      const [result] = callWithAsyncErrorHandling(initFn, [
        data,
        ctx,
      ] satisfies Parameters<ComponentFn>);
      lastResult = await result;
    }
    return lastResult;
  };

  /** Internal API - We call this when we want to load / register all JS & CSS files rendered by component(s) */
  const _loadComponentScripts = (inputs: {
    cssUrls__markAsLoaded: string[];
    jsUrls__markAsLoaded: string[];
    cssTags__toFetch: string[];
    jsTags__toFetch: string[];
    componentJsVars: [string, string, string][];
    componentJsCalls: [string, string, string | null][];
  }) => {
    // Convert Base64-encoded strings back to their original values
    const cssUrls__markAsLoaded = inputs.cssUrls__markAsLoaded.map((s) => atob(s));
    const jsUrls__markAsLoaded = inputs.jsUrls__markAsLoaded.map((s) => atob(s));
    const cssTags__toFetch = inputs.cssTags__toFetch.map((s) => JSON.parse(atob(s)) as TagJson);
    const jsTags__toFetch = inputs.jsTags__toFetch.map((s) => JSON.parse(atob(s)) as TagJson);
    const componentJsVars = inputs.componentJsVars.map((dataArr) => dataArr.map(atob) as [string, string, string]);
    const componentJsCalls = inputs.componentJsCalls.map(([compClsId, compId, jsVarsHash]) => {
      return [atob(compClsId), atob(compId), jsVarsHash == null ? jsVarsHash : atob(jsVarsHash)] as [string, string, string | null];
    });

    // Part of passing Python vars to JS - Prepare data that will be made available
    // to the components inside `$onComponent`.
    componentJsVars.forEach(([compClsId, jsVarsHash, jsonData]) => {
      // Basically what this says is: "when we call `callComponent()` with THIS component class ID `compClsId`
      // and JS variables hash `jsVarsHash`, then run THIS callback to generate
      // a fresh copy of the JSON data `jsonData` that we've been sent from Python from `get_js_data()`.
      registerComponentData(compClsId, jsVarsHash, () => {
        return JSON.parse(jsonData);
      });
    });

    // Mark as loaded the CSS that WAS inlined into the HTML.
    cssUrls__markAsLoaded.forEach((s) => markScriptLoaded("css", s));
    jsUrls__markAsLoaded.forEach((s) => markScriptLoaded("js", s));

    // Load CSS that was not inlined into the HTML
    // NOTE: We don't need to wait for CSS to load
    Promise.all(cssTags__toFetch.map((s) => loadCss(s))).catch(console.error);

    // Load JS that was not inlined into the HTML
    // This promise waits until all `<script>` tags have been loaded
    // by waiting for the `HTMLScriptElement.onload()` callback to be called.
    // See https://developer.mozilla.org/en-US/docs/Web/API/HTMLScriptElement
    const jsScriptsPromise = Promise
      // NOTE: Interestingly enough, when we insert scripts into the DOM programmatically,
      // the order of execution is the same as the order of insertion.
      .all(jsTags__toFetch.map((s) => loadJs(s).promise))
      .catch(console.error);

    // Wait for all required JS that should be either 1. loaded already, 2. loaded by the above
    // call to `loadJs()`.
    const jsScriptsPromise2 = waitForScriptsToLoad("js", jsUrls__markAsLoaded);

    // Create a combined promise that must resolve before component calls can execute.
    // This prevents race conditions where a later script tag (with no dependencies) could
    // queue its calls before an earlier script tag's dependencies finish loading.
    const scriptsLoadPromise = Promise.all([
      jsScriptsPromise,
      jsScriptsPromise2,
    ]);

    // Queue component calls instead of executing immediately.
    //
    // Especially when dealing with fragments with JS variables, all the relevant JS scripts
    // may be defined across multiple `<script data-djc>` tags.
    // In the past we just awaited for the scripts-to-fetch defined in this `<script data-djc>` tag.
    // But this doesn't work for fragments with JS variables.
    // So instead, we keep a queue of unprocessed component calls.
    //
    // The queue ensures the component calls will be processed in original order
    // once all their dependencies (component registration and JS vars) are available.
    for (const [compClsId, compId, jsVarsHash] of componentJsCalls) {
      queueComponentCall(compClsId, compId, jsVarsHash, scriptsLoadPromise);
    }
    // Process any calls that are already unblocked
    // NOTE: Not really necessary to return this promise, just good practice
    return _processPendingCalls();
  };

  const onDjcScript = (script: HTMLScriptElement) => {
    const data = JSON.parse(script.text);
    _loadComponentScripts(data);
  };

  // Initialise the MutationObserver that watches for newly-inserted `<script>` tags
  // with `data-djc` attribute and processes them.
  observeScriptTag(onDjcScript);

  // Also search for any already-embedded scripts at the moment the file is loaded.
  const existingScripts = document.querySelectorAll<HTMLScriptElement>("script[data-djc]");
  existingScripts.forEach(onDjcScript);

  return {
    callComponent: queueComponentCall,
    registerComponent,
    registerComponentData,
    loadJs,
    loadCss,
    markScriptLoaded,
    waitForScriptsToLoad,
    _loadComponentScripts,
  };
};
