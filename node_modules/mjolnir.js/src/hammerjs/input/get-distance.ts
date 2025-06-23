import type {Point, PointerEventLike} from './types';

/**
 * calculate the absolute distance between two points
 * @returns distance
 */
export function getPointDistance(p1: Point, p2: Point): number {
  const x = p2.x - p1.x;
  const y = p2.y - p1.y;
  return Math.sqrt(x * x + y * y);
}

/**
 * calculate the absolute distance between two pointer events
 * @returns distance
 */
export function getEventDistance(p1: PointerEventLike, p2: PointerEventLike): number {
  const x = p2.clientX - p1.clientX;
  const y = p2.clientY - p1.clientY;
  return Math.sqrt(x * x + y * y);
}
