import type {Point, PointerEventLike} from './types';

/**
 * get the center of all the pointers
 */
export function getCenter(pointers: PointerEventLike[]): Point {
  const pointersLength = pointers.length;

  // no need to loop when only one touch
  if (pointersLength === 1) {
    return {
      x: Math.round(pointers[0].clientX),
      y: Math.round(pointers[0].clientY)
    };
  }

  let x = 0;
  let y = 0;
  let i = 0;
  while (i < pointersLength) {
    x += pointers[i].clientX;
    y += pointers[i].clientY;
    i++;
  }

  return {
    x: Math.round(x / pointersLength),
    y: Math.round(y / pointersLength)
  };
}
