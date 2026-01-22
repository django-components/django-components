/** The actual code of the JS dependency manager */
import { callWithAsyncErrorHandling } from './errorHandling';
import { observeScriptTag } from './mutationObserver';
import { unescapeJs } from './utils';

type MaybePromise<T> = Promise<T> | T;

export interface ComponentContext<
  TEl extends HTMLElement = HTMLElement,
> {
  name: string;
  id: string;
  els: TEl[];
}

export type ComponentFn<
  TData extends object = object,
  TEl extends HTMLElement = HTMLElement
> = (
  data: TData,
  ctx: ComponentContext<TEl>
) => MaybePromise<any>;

export type DataFn = () => object;

export type ScriptType = 'js' | 'css';

/**
 * Usage:
 *
 * ```js
 * DjangoComponents.registerComponent("table", async (data, { id, name, els }) => {
 *   ...
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
 * DjangoComponents.loadJs('<script src="/abc/def"></script>');
 * ```
 *
 * ```js
 * DjangoComponents.loadCss('<link href="/abc/def" />');
 * ```
 *
 * ```js
 * DjangoComponents.markScriptLoaded("js", '/abc/def');
 * ```
 */
export const createComponentsManager = () => {
  const loadedJs = new Set<string>();
  const loadedCss = new Set<string>();
  const components: Record<string, ComponentFn> = {};
  const componentInputs: Record<string, DataFn> = {};

  const parseScriptTag = (tag: string) => {
    const scriptNode = new DOMParser().parseFromString(tag, 'text/html').querySelector('script');
    if (!scriptNode) {
      throw Error(
        '[DjangoComponents] Failed to extract <script> tag. Make sure that the string contains' +
          ' <script></script> and is a valid HTML'
      );
    }
    return scriptNode;
  };

  const parseLinkTag = (tag: string) => {
    const linkNode = new DOMParser().parseFromString(tag, 'text/html').querySelector('link');
    if (!linkNode) {
      throw Error(
        '[DjangoComponents] Failed to extract <link> tag. Make sure that the string contains' +
          ' <link></link> and is a valid HTML'
      );
    }
    return linkNode;
  };

  // NOTE: The way we turn the string into an HTMLElement, if we then try to
  // insert the node into the Document, it will NOT load. So instead we create
  // a <script> that that WILL load once inserted, and copy all attributes from
  // one to the other.
  // Might be related to https://security.stackexchange.com/a/240362/302733
  // See https://stackoverflow.com/questions/13121948
  const cloneNode = <T extends HTMLElement>(srcNode: T): T => {
    const targetNode = document.createElement(srcNode.tagName) as T;
    targetNode.innerHTML = srcNode.innerHTML;
    for (const attr of srcNode.attributes) {
      targetNode.setAttributeNode(attr.cloneNode() as Attr);
    }
    return targetNode;
  };

  const loadJs = (tag: string) => {
    const srcScriptNode = parseScriptTag(tag);

    // Use `.getAttribute()` instead of `.src` so we get the value as is,
    // without the host name prepended if URL is just a path.
    const src = srcScriptNode.getAttribute('src');
    if (!src || isScriptLoaded('js', src)) return;

    markScriptLoaded('js', src);

    const targetScriptNode = cloneNode(srcScriptNode);

    const isAsync = (
      // NOTE: `async` and `defer` are boolean attributes, so their value can be
      // an empty string, hence the `!= null` check.
      // Read more on https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script
      srcScriptNode.getAttribute('async') != null
      || srcScriptNode.getAttribute('defer') != null
      || srcScriptNode.getAttribute('type') === 'module'
    );

    // Setting this to `false` ensures that the loading and execution of the script is "blocking",
    // meaning that the next script in line will wait until this one is done.
    // See https://stackoverflow.com/a/21550322/9788634
    targetScriptNode.async = isAsync;

    // In case of JS scripts, we return a Promise that resolves when the script is loaded
    // See https://stackoverflow.com/a/57267538/9788634
    const promise = new Promise<void>((resolve, reject) => {
      targetScriptNode.onload = () => {
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
      globalThis.document.body.append(targetScriptNode);
    });

    return {
      el: targetScriptNode,
      promise,
    };
  };

  const loadCss = (tag: string) => {
    const linkNode = parseLinkTag(tag);
    // NOTE: Use `.getAttribute()` instead of `.href` so we get the value as is,
    // without the host name prepended if URL is just a path.
    const href = linkNode.getAttribute('href');
    if (!href || isScriptLoaded('css', href)) return;

    // Insert at the end of <head> to follow convention
    const targetLinkNode = cloneNode(linkNode);
    globalThis.document.head.append(targetLinkNode);
    markScriptLoaded('css', href);

    // For CSS, we return a dummy Promise, since we don't need to wait for anything
    return {
      el: targetLinkNode,
      promise: Promise.resolve(),
    };
  };

  const markScriptLoaded = (type: ScriptType, url: string): void => {
    if (type !== 'js' && type !== 'css') {
      throw Error(
        `[DjangoComponents] markScriptLoaded received invalid script type '${type}'. Must be one of 'js', 'css'`
      );
    }

    const urlsSet = type === 'js' ? loadedJs : loadedCss;
    urlsSet.add(url);
  };

  const isScriptLoaded = (type: ScriptType, url: string): boolean => {
    if (type !== 'js' && type !== 'css') {
      throw Error(
        `[DjangoComponents] isScriptLoaded received invalid script type '${type}'. Must be one of 'js', 'css'`
      );
    }

    const urlsSet = type === 'js' ? loadedJs : loadedCss;
    return urlsSet.has(url);
  };

  const registerComponent = (name: string, compFn: ComponentFn) => {
    components[name] = compFn;
  };

  /**
   * @example
   * DjangoComponents.registerComponentData("table", "a1b2c3", () => {{
   *   return JSON.parse('{ "a": 2 }');
   * }});
   */
  const registerComponentData = (name: string, inputHash: string, dataFactory: DataFn) => {
    const key = `${name}:${inputHash}`;
    componentInputs[key] = dataFactory;
  };

  const callComponent = (name: string, compId: string, inputHash: string): MaybePromise<any> => {
    const initFn = components[name];
    if (!initFn) throw Error(`[DjangoComponents] '${name}': No component registered for that name`);

    const elems = Array.from(document.querySelectorAll<HTMLElement>(`[data-djc-id-${compId}]`));
    if (!elems.length) throw Error(`[DjangoComponents] '${name}': No elements with component ID '${compId}' found`);

    const dataKey = `${name}:${inputHash}`;
    const dataFactory = componentInputs[dataKey];
    if (!dataFactory) throw Error(`[DjangoComponents] '${name}': Cannot find input for hash '${inputHash}'`);

    const data = dataFactory();

    const ctx = {
      name,
      id: compId,
      els: elems,
    } satisfies ComponentContext;

    const [result] = callWithAsyncErrorHandling(initFn, [data, ctx] satisfies Parameters<ComponentFn>);
    return result;
  };

  /** Internal API - We call this when we want to load / register all JS & CSS files rendered by component(s) */
  const _loadComponentScripts = async (inputs: {
    loadedCssUrls: string[];
    loadedJsUrls: string[];
    toLoadCssTags: string[];
    toLoadJsTags: string[];
  }) => {
    const loadedCssUrls = inputs.loadedCssUrls.map((s) => atob(s));
    const loadedJsUrls = inputs.loadedJsUrls.map((s) => atob(s));
    const toLoadCssTags = inputs.toLoadCssTags.map((s) => atob(s));
    const toLoadJsTags = inputs.toLoadJsTags.map((s) => atob(s));

    // Mark as loaded the CSS that WAS inlined into the HTML.
    loadedCssUrls.forEach((s) => markScriptLoaded("css", s));
    loadedJsUrls.forEach((s) => markScriptLoaded("js", s));

    // Load CSS that was not inlined into the HTML
    // NOTE: We don't need to wait for CSS to load
    Promise
        .all(toLoadCssTags.map((s) => loadCss(s)))
        .catch(console.error);

    // Load JS that was not inlined into the HTML
    const jsScriptsPromise = Promise
        // NOTE: Interestingly enough, when we insert scripts into the DOM programmatically,
        // the order of execution is the same as the order of insertion.
        .all(toLoadJsTags.map((s) => loadJs(s)))
        .catch(console.error);
  };

  const onDjcScript = (script: HTMLScriptElement) => {
    const data = JSON.parse(script.text);
    _loadComponentScripts(data);
  };
  
  // Initialise the MutationObserver that watches for `<script>` tags with `data-djc` attribute
  observeScriptTag(onDjcScript);

  // Also consider any embedded scripts at the moment the file is loaded.
  const existingScripts = document.querySelectorAll<HTMLScriptElement>('script[data-djc]');
  existingScripts.forEach(onDjcScript);

  return {
    callComponent,
    registerComponent,
    registerComponentData,
    loadJs,
    loadCss,
    markScriptLoaded,
  };
};
