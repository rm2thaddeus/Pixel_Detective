import {getEventAngle} from './get-angle';
import {PointerEventLike} from './types';

/**
 * calculate the rotation degrees between two pointer sets
 * @returns rotation in degrees
 */
export function getRotation(start: PointerEventLike[], end: PointerEventLike[]): number {
  return getEventAngle(end[1], end[0]) - getEventAngle(start[1], start[0]);
}
