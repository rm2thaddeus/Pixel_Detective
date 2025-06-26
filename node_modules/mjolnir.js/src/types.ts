// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import type {HammerEvent} from './hammerjs/index';

export type Point = {
  x: number;
  y: number;
};

/* mjolnir.js */

export interface MjolnirEventRaw {
  type: string;
  srcEvent: Event;
  target: HTMLElement;
}

export type MjolnirEventWrapper<T extends MjolnirEventRaw> = T & {
  rootElement: HTMLElement;
  offsetCenter: Point;
  leftButton?: boolean;
  rightButton?: boolean;
  middleButton?: boolean;
  handled: boolean;
  stopPropagation: () => void;
  stopImmediatePropagation: () => void;
  preventDefault: () => void;
};

export type MjolnirPointerEventRaw = MjolnirEventRaw & {
  type:
    | 'pointerup'
    | 'pointerdown'
    | 'contextmenu'
    | 'pointermove'
    | 'pointerover'
    | 'pointerout'
    | 'pointerenter'
    | 'pointerleave';
  pointerType: 'mouse' | 'pen' | 'touch';
  center: Point;
  srcEvent: MouseEvent | PointerEvent;
};

export type MjolnirWheelEventRaw = MjolnirEventRaw & {
  type: 'wheel';
  pointerType: 'mouse';
  center: Point;
  srcEvent: WheelEvent;
  delta: number;
};

export type MjolnirKeyEventRaw = MjolnirEventRaw & {
  type: 'keydown' | 'keyup';
  key: string;
  srcEvent: KeyboardEvent;
};

export type MjolnirKeyEvent = MjolnirKeyEventRaw & {
  rootElement: HTMLElement;
  handled: boolean;
  /** Prevents the current event from bubbling up */
  stopPropagation: () => void;
  /** Prevents any remaining handlers from being called */
  stopImmediatePropagation: () => void;
};

export type MjolnirGestureEvent = MjolnirEventWrapper<HammerEvent>;
export type MjolnirPointerEvent = MjolnirEventWrapper<MjolnirPointerEventRaw>;
export type MjolnirWheelEvent = MjolnirEventWrapper<MjolnirWheelEventRaw>;

export type MjolnirEvent =
  | MjolnirGestureEvent
  | MjolnirPointerEvent
  | MjolnirWheelEvent
  | MjolnirKeyEvent;

export type MjolnirEventHandler<EventT extends MjolnirEvent = any> = (event: EventT) => void;

export type MjolnirEventHandlers = {
  [type: string]: MjolnirEventHandler;
};
