import {TOUCH_ACTION_COMPUTE} from './touchaction-Consts';
import cleanTouchActions from './clean-touch-actions';

import type {Manager} from '../manager';

/**
 * Touch Action
 * sets the touchAction property or uses the js alternative
 */
export class TouchAction {
  manager: Manager;
  actions: string = '';

  constructor(manager: Manager, value: string) {
    this.manager = manager;
    this.set(value);
  }

  /**
   * set the touchAction value on the element or enable the polyfill
   */
  set(value: string) {
    // find out the touch-action by the event handlers
    if (value === TOUCH_ACTION_COMPUTE) {
      value = this.compute();
    }

    if (this.manager.element) {
      this.manager.element.style.touchAction = value;
      this.actions = value;
    }
  }

  /**
   * just re-set the touchAction value
   */
  update() {
    this.set(this.manager.options.touchAction);
  }

  /**
   * compute the value for the touchAction property based on the recognizer's settings
   */
  compute(): string {
    let actions: string[] = [];
    for (const recognizer of this.manager.recognizers) {
      if (recognizer.options.enable) {
        actions = actions.concat(recognizer.getTouchAction());
      }
    }
    return cleanTouchActions(actions.join(' '));
  }
}
