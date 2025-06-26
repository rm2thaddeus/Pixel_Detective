import type {Vector} from './types';

/**
 * calculate the velocity between two points. unit is in px per ms.
 */
export function getVelocity(deltaTime: number, x: number, y: number): Vector {
  return {
    x: x / deltaTime || 0,
    y: y / deltaTime || 0
  };
}
