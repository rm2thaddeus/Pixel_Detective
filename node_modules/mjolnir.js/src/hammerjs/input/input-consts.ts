export const MOBILE_REGEX = /mobile|tablet|ip(ad|hone|od)|android/i;

export const COMPUTE_INTERVAL = 25;

export enum InputEvent {
  Start = 1,
  Move = 2,
  End = 4,
  Cancel = 8
}

export enum InputDirection {
  None = 0,
  Left = 1,
  Right = 2,
  Up = 4,
  Down = 8,
  Horizontal = 3,
  Vertical = 12,
  All = 15
}
