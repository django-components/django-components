/** This file defines the API of the JS code. */
import { createComponentsManager } from './manager';
import { unescapeJs } from './utils';

export type * from './manager';

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
