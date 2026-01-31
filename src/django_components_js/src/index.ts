/** This file defines the API of the JS code. */
import { createComponentsManager } from './manager';
import { unescapeJs } from './utils';

export type * from './manager';

// TODO_v1: Make `DjangoComponents` THE manager object
//          - keep `createComponentsManager` as one of manager's methods (used in tests)
//          - remove `unescapeJs` (unused)
export const DjangoComponents = {
  manager: createComponentsManager(),
  createComponentsManager,
  unescapeJs,
};

// In browser, this is accessed as `DjangoComponents.manager`, etc
globalThis.DjangoComponents = DjangoComponents;

// TODO_v1: Delete this in v1, kept for backwards compatibility
if (globalThis.Components === undefined) {
  globalThis.Components = DjangoComponents;
}
