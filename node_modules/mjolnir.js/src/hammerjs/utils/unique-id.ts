/**
 * get a unique id
 */
let _uniqueId = 1;
export function uniqueId(): number {
  return _uniqueId++;
}
