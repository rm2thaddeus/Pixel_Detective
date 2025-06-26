const VENDOR_PREFIXES = ['', 'webkit', 'Moz', 'MS', 'ms', 'o'];

/**
 * get the prefixed property
 * @returns prefixed property name
 */
export function prefixed(obj: Record<string, any>, property: string): string | undefined {
  const camelProp = property[0].toUpperCase() + property.slice(1);

  for (const prefix of VENDOR_PREFIXES) {
    const prop = prefix ? prefix + camelProp : property;

    if (prop in obj) {
      return prop;
    }
  }
  return undefined;
}
