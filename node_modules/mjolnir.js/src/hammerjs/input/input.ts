import {addEventListeners, removeEventListeners} from '../utils/event-listeners';
import {getWindowForElement} from '../utils/get-window-for-element';
import {inputHandler} from './input-handler';

import {InputEvent} from './input-consts';
import type {RawInput} from './types';
import type {Manager} from '../manager';

/**
 * create new input type manager
 */
export abstract class Input {
  manager: Manager;
  element: HTMLElement;
  target: EventTarget;

  evEl: string = '';
  evWin: string = '';
  evTarget: string = '';

  constructor(manager: Manager) {
    this.manager = manager;
    this.element = manager.element!;
    this.target = manager.options.inputTarget || manager.element!;
  }

  /** smaller wrapper around the handler, for the scope and the enabled state of the manager,
   * so when disabled the input events are completely bypassed.
   */
  protected domHandler = (ev: Event) => {
    if (this.manager.options.enable) {
      this.handler(ev);
    }
  };

  protected callback(eventType: InputEvent, input: RawInput) {
    inputHandler(this.manager, eventType, input);
  }

  /**
   * should handle the inputEvent data and trigger the callback
   */
  abstract handler(ev: Event): void;

  // eslint-disable @typescript-eslint/unbound-method
  /**
   * bind the events
   */
  init() {
    addEventListeners(this.element, this.evEl, this.domHandler);
    addEventListeners(this.target, this.evTarget, this.domHandler);
    addEventListeners(getWindowForElement(this.element), this.evWin, this.domHandler);
  }

  /**
   * unbind the events
   */
  destroy() {
    removeEventListeners(this.element, this.evEl, this.domHandler);
    removeEventListeners(this.target, this.evTarget, this.domHandler);
    removeEventListeners(getWindowForElement(this.element), this.evWin, this.domHandler);
  }
  // eslint-enable @typescript-eslint/unbound-method
}
