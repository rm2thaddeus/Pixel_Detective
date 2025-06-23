import {InputEvent, COMPUTE_INTERVAL} from './input-consts';
import {getVelocity} from './get-velocity';
import {getDirection} from './get-direction';

import type {Session, HammerInput} from './types';

/**
 * velocity is calculated every x ms
 */
export function computeIntervalInputData(session: Session, input: HammerInput) {
  const last = session.lastInterval || input;
  const deltaTime = input.timeStamp - last.timeStamp;
  let velocity;
  let velocityX;
  let velocityY;
  let direction;

  if (
    input.eventType !== InputEvent.Cancel &&
    (deltaTime > COMPUTE_INTERVAL || last.velocity === undefined)
  ) {
    const deltaX = input.deltaX - last.deltaX;
    const deltaY = input.deltaY - last.deltaY;

    const v = getVelocity(deltaTime, deltaX, deltaY);
    velocityX = v.x;
    velocityY = v.y;
    velocity = Math.abs(v.x) > Math.abs(v.y) ? v.x : v.y;
    direction = getDirection(deltaX, deltaY);

    session.lastInterval = input;
  } else {
    // use latest velocity info if it doesn't overtake a minimum period
    velocity = last.velocity;
    velocityX = last.velocityX;
    velocityY = last.velocityY;
    direction = last.direction;
  }

  input.velocity = velocity;
  input.velocityX = velocityX;
  input.velocityY = velocityY;
  input.direction = direction;
}
