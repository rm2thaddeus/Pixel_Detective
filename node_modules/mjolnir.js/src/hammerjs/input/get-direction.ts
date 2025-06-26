import {InputDirection} from './input-consts';

/**
 * get the direction between two points
 * @returns direction
 */
export function getDirection(dx: number, dy: number): InputDirection {
  if (dx === dy) {
    return InputDirection.None;
  }

  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx < 0 ? InputDirection.Left : InputDirection.Right;
  }
  return dy < 0 ? InputDirection.Up : InputDirection.Down;
}
