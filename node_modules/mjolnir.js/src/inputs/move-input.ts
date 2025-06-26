// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import type {MjolnirPointerEventRaw} from '../types';
import {Input, InputOptions} from './input';

const MOUSE_EVENTS = [
  'mousedown',
  'mousemove',
  'mouseup',
  'mouseover',
  'mouseout',
  'mouseleave'
] as const;

type MoveEventType = 'pointermove' | 'pointerover' | 'pointerout' | 'pointerenter' | 'pointerleave';

/**
 * Hammer.js swallows 'move' events (for pointer/touch/mouse)
 * when the pointer is not down. This class sets up a handler
 * specifically for these events to work around this limitation.
 * Note that this could be extended to more intelligently handle
 * move events across input types, e.g. storing multiple simultaneous
 * pointer/touch events, calculating speed/direction, etc.
 */
export class MoveInput extends Input<MjolnirPointerEventRaw, Required<InputOptions>> {
  pressed: boolean;
  enableMoveEvent: boolean;
  enableEnterEvent: boolean;
  enableLeaveEvent: boolean;
  enableOutEvent: boolean;
  enableOverEvent: boolean;

  constructor(
    element: HTMLElement,
    callback: (event: MjolnirPointerEventRaw) => void,
    options: InputOptions
  ) {
    super(element, callback, {enable: true, ...options});

    this.pressed = false;
    const {enable} = this.options;

    this.enableMoveEvent = enable;
    this.enableLeaveEvent = enable;
    this.enableEnterEvent = enable;
    this.enableOutEvent = enable;
    this.enableOverEvent = enable;

    MOUSE_EVENTS.forEach((event) => element.addEventListener(event, this.handleEvent));
  }

  destroy() {
    MOUSE_EVENTS.forEach((event) => this.element.removeEventListener(event, this.handleEvent));
  }

  /**
   * Enable this input (begin processing events)
   * if the specified event type is among those handled by this input.
   */
  enableEventType(eventType: string, enabled: boolean) {
    switch (eventType) {
      case 'pointermove':
        this.enableMoveEvent = enabled;
        break;
      case 'pointerover':
        this.enableOverEvent = enabled;
        break;
      case 'pointerout':
        this.enableOutEvent = enabled;
        break;
      case 'pointerenter':
        this.enableEnterEvent = enabled;
        break;
      case 'pointerleave':
        this.enableLeaveEvent = enabled;
        break;
      default:
      // ignore
    }
  }

  handleEvent = (event: MouseEvent) => {
    this.handleOverEvent(event);
    this.handleOutEvent(event);
    this.handleEnterEvent(event);
    this.handleLeaveEvent(event);
    this.handleMoveEvent(event);
  };

  handleOverEvent(event: MouseEvent) {
    if (this.enableOverEvent && event.type === 'mouseover') {
      this._emit('pointerover', event);
    }
  }

  handleOutEvent(event: MouseEvent) {
    if (this.enableOutEvent && event.type === 'mouseout') {
      this._emit('pointerout', event);
    }
  }

  handleEnterEvent(event: MouseEvent) {
    if (this.enableEnterEvent && event.type === 'mouseenter') {
      this._emit('pointerenter', event);
    }
  }

  handleLeaveEvent(event: MouseEvent) {
    if (this.enableLeaveEvent && event.type === 'mouseleave') {
      this._emit('pointerleave', event);
    }
  }

  handleMoveEvent(event: MouseEvent) {
    if (this.enableMoveEvent) {
      switch (event.type) {
        case 'mousedown':
          if (event.button >= 0) {
            // Button is down
            this.pressed = true;
          }
          break;
        case 'mousemove':
          // Move events use `bottons` to track the button being pressed
          if (event.buttons === 0) {
            // Button is not down
            this.pressed = false;
          }
          if (!this.pressed) {
            // Drag events are emitted by hammer already
            // we just need to emit the move event on hover
            this._emit('pointermove', event);
          }
          break;
        case 'mouseup':
          this.pressed = false;
          break;
        default:
      }
    }
  }

  _emit(type: MoveEventType, event: MouseEvent) {
    this.callback({
      type,
      center: {
        x: event.clientX,
        y: event.clientY
      },
      srcEvent: event,
      pointerType: 'mouse',
      target: event.target as HTMLElement
    });
  }
}
