/**
 * This file contains code for safe calling of functions, as seen in Vue and Alpine.
 * It ensures that when we run JS code for individual components, that the process continues
 * even if the user-provided JS raises an error.
 */
import { isArray, isFunction, isPromise } from "./utils";

type Fn = (...args: any[]) => any;

export function callWithErrorHandling(fn: Fn, args?: any[]) {
  try {
    return args ? fn.apply(null, args) : fn();
  } catch (err) {
    logError(err);
    throw err;
  }
}

export function callWithAsyncErrorHandling(fn: Fn | Fn[], args?: any[]): any {
  if (isFunction(fn)) {
    const res = callWithErrorHandling(fn, args);
    if (res && isPromise(res)) {
      res.catch((err) => {
        logError(err);
        throw err;
      });
    }
    return [res];
  }

  if (isArray(fn)) {
    const values: any[] = [];
    for (let i = 0; i < fn.length; i++) {
      values.push(callWithAsyncErrorHandling(fn[i], args));
    }
    return values;
  } else {
    console.warn(
      `[DjangoComponents] Invalid value type passed to callWithAsyncErrorHandling(): ${typeof fn}`,
    );
  }
}

function logError(err: unknown) {
  // recover in prod to reduce the impact on end-user
  console.error(err);
}
