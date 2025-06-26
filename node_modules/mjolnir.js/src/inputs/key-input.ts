// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import type {MjolnirKeyEventRaw} from '../types';
import {Input, InputOptions} from './input';

const KEY_EVENTS = ['keydown', 'keyup'] as const;

type KeyInputOptions = InputOptions & {
  tabIndex?: number;
};

export class KeyInput extends Input<MjolnirKeyEventRaw, Required<KeyInputOptions>> {
  enableDownEvent: boolean;
  enableUpEvent: boolean;

  constructor(
    element: HTMLElement,
    callback: (event: MjolnirKeyEventRaw) => void,
    options: KeyInputOptions
  ) {
    super(element, callback, {enable: true, tabIndex: 0, ...options});

    this.enableDownEvent = this.options.enable;
    this.enableUpEvent = this.options.enable;

    element.tabIndex = this.options.tabIndex;
    element.style.outline = 'none';
    KEY_EVENTS.forEach((event) => element.addEventListener(event, this.handleEvent));
  }

  destroy() {
    KEY_EVENTS.forEach((event) => this.element.removeEventListener(event, this.handleEvent));
  }

  /**
   * Enable this input (begin processing events)
   * if the specified event type is among those handled by this input.
   */
  enableEventType(eventType: string, enabled: boolean) {
    if (eventType === 'keydown') {
      this.enableDownEvent = enabled;
    }
    if (eventType === 'keyup') {
      this.enableUpEvent = enabled;
    }
  }

  handleEvent = (event: KeyboardEvent) => {
    // Ignore if focused on text input
    const targetElement = (event.target || event.srcElement) as HTMLElement;
    if (
      (targetElement.tagName === 'INPUT' && (targetElement as HTMLInputElement).type === 'text') ||
      targetElement.tagName === 'TEXTAREA'
    ) {
      return;
    }

    if (this.enableDownEvent && event.type === 'keydown') {
      this.callback({
        type: 'keydown',
        srcEvent: event,
        key: event.key,
        target: event.target as HTMLElement
      });
    }

    if (this.enableUpEvent && event.type === 'keyup') {
      this.callback({
        type: 'keyup',
        srcEvent: event,
        key: event.key,
        target: event.target as HTMLElement
      });
    }
  };
}
