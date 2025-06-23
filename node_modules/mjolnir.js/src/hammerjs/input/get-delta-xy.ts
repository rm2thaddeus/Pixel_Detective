import {InputEvent} from './input-consts';
import type {RawInput, Session} from './types';

/** Populates input.deltaX, input.deltaY */
export function computeDeltaXY(
  session: Session,
  input: RawInput
): {
  deltaX: number;
  deltaY: number;
} {
  // getCenter is called before computeDeltaXY
  const center = input.center!;
  let offset = session.offsetDelta;
  let prevDelta = session.prevDelta;
  const prevInput = session.prevInput;

  if (input.eventType === InputEvent.Start || prevInput?.eventType === InputEvent.End) {
    prevDelta = session.prevDelta = {
      x: prevInput?.deltaX || 0,
      y: prevInput?.deltaY || 0
    };

    offset = session.offsetDelta = {
      x: center.x,
      y: center.y
    };
  }

  return {
    deltaX: prevDelta!.x + (center.x - offset!.x),
    deltaY: prevDelta!.y + (center.y - offset!.y)
  };
}
