import {
  TOUCH_ACTION_NONE,
  TOUCH_ACTION_PAN_X,
  TOUCH_ACTION_PAN_Y,
  TOUCH_ACTION_MANIPULATION,
  TOUCH_ACTION_AUTO
} from './touchaction-Consts';

/**
 * when the touchActions are collected they are not a valid value, so we need to clean things up. *
 * @returns valid touchAction
 */
export default function cleanTouchActions(actions: string): string {
  // none
  if (actions.includes(TOUCH_ACTION_NONE)) {
    return TOUCH_ACTION_NONE;
  }

  const hasPanX = actions.includes(TOUCH_ACTION_PAN_X);
  const hasPanY = actions.includes(TOUCH_ACTION_PAN_Y);

  // if both pan-x and pan-y are set (different recognizers
  // for different directions, e.g. horizontal pan but vertical swipe?)
  // we need none (as otherwise with pan-x pan-y combined none of these
  // recognizers will work, since the browser would handle all panning
  if (hasPanX && hasPanY) {
    return TOUCH_ACTION_NONE;
  }

  // pan-x OR pan-y
  if (hasPanX || hasPanY) {
    return hasPanX ? TOUCH_ACTION_PAN_X : TOUCH_ACTION_PAN_Y;
  }

  // manipulation
  if (actions.includes(TOUCH_ACTION_MANIPULATION)) {
    return TOUCH_ACTION_MANIPULATION;
  }

  return TOUCH_ACTION_AUTO;
}
