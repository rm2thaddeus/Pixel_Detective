import {Point, PointerEventLike} from './types';

/**
 * calculate the angle between two coordinates
 * @returns angle in degrees
 */
export function getPointAngle(p1: Point, p2: Point) {
  const x: number = p2.x - p1.x;
  const y: number = p2.y - p1.y;
  return (Math.atan2(y, x) * 180) / Math.PI;
}

/**
 * calculate the angle between two pointer events
 * @returns angle in degrees
 */
export function getEventAngle(p1: PointerEventLike, p2: PointerEventLike) {
  const x: number = p2.clientX - p1.clientX;
  const y: number = p2.clientY - p1.clientY;
  return (Math.atan2(y, x) * 180) / Math.PI;
}
