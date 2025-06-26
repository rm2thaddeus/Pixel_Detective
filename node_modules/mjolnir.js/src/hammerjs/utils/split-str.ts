/**
 * split string on whitespace
 * @returns {Array} words
 */
export function splitStr(str: string): string[] {
  return str.trim().split(/\s+/g);
}
