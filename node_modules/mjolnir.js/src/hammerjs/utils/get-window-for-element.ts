/**
 * get the window object of an element
 */
export function getWindowForElement(element: HTMLElement): Window | null {
  const doc = element.ownerDocument || (element as unknown as Document);
  return doc.defaultView;
}
