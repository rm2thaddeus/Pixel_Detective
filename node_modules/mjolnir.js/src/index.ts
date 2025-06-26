// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

export {EventManager} from './event-manager';
export {
  Recognizer,
  Pan,
  Rotate,
  Pinch,
  Swipe,
  Press,
  Tap,
  InputDirection,
  InputEvent
} from './hammerjs/index';

// types
export type {EventManagerOptions, RecognizerTuple} from './event-manager';
export type {
  MjolnirEvent,
  MjolnirGestureEvent,
  MjolnirKeyEvent,
  MjolnirWheelEvent,
  MjolnirPointerEvent
} from './types';

export type {
  PanRecognizerOptions,
  RotateRecognizerOptions,
  PinchRecognizerOptions,
  SwipeRecognizerOptions,
  PressRecognizerOptions,
  TapRecognizerOptions
} from './hammerjs/index';
