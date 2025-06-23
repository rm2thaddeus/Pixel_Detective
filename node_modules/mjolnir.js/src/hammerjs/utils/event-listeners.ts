import {splitStr} from './split-str';

/**
 * addEventListener with multiple events at once
 */
export function addEventListeners(
  target: EventTarget | null,
  types: string,
  handler: EventListener
) {
  if (!target) {
    return;
  }
  for (const type of splitStr(types)) {
    target.addEventListener(type, handler, false);
  }
}

/**
 * removeEventListener with multiple events at once
 */
export function removeEventListeners(
  target: EventTarget | null,
  types: string,
  handler: EventListener
) {
  if (!target) {
    return;
  }
  for (const type of splitStr(types)) {
    target.removeEventListener(type, handler, false);
  }
}
