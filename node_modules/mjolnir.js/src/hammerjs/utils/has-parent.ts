/**
 * find if a node is in the given parent
 */
export default function hasParent(node: HTMLElement, parent: HTMLElement): boolean {
  let ancestor: Node | null = node;
  while (ancestor) {
    if (ancestor === parent) {
      return true;
    }
    ancestor = ancestor.parentNode;
  }
  return false;
}
