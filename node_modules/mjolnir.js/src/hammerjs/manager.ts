import {TouchAction} from './touchaction/touchaction';
import {PointerEventInput} from './inputs/pointerevent';
import {splitStr} from './utils/split-str';
import {prefixed} from './utils/prefixed';
import {RecognizerState} from './recognizer/recognizer-state';

import type {Input} from './input/input';
import type {Recognizer} from './recognizer/recognizer';
import type {Session, HammerInput} from './input/types';

const STOP = 1;
const FORCED_STOP = 2;

export type ManagerOptions = {
  /**
   * The value for the touchAction property/fallback.
   * When set to `compute` it will magically set the correct value based on the added recognizers.
   * @default compute
   */
  touchAction?: string;

  /**
   * @default true
   */
  enable?: boolean;

  /**
   * EXPERIMENTAL FEATURE -- can be removed/changed
   * Change the parent input target element.
   * If Null, then it is being set the to main element.
   * @default null
   */
  inputTarget?: null | EventTarget;

  /**
   * Some CSS properties can be used to improve the working of Hammer.
   * Add them to this method and they will be set when creating a new Manager.
   */
  cssProps?: Partial<CSSStyleDeclaration>;
};

export type HammerEvent = HammerInput & {
  type: string;
  preventDefault: () => void;
};
export type EventHandler = (event: HammerEvent) => void;

const defaultOptions: Required<ManagerOptions> = {
  touchAction: 'compute',
  enable: true,
  inputTarget: null,
  cssProps: {
    /**
     * Disables text selection to improve the dragging gesture. Mainly for desktop browsers.
     */
    userSelect: 'none',
    /**
     * (Webkit) Disable default dragging behavior
     */
    // @ts-ignore
    userDrag: 'none',
    /**
     * (iOS only) Disables the default callout shown when you touch and hold a touch target.
     * When you touch and hold a touch target such as a link, Safari displays
     * a callout containing information about the link. This property allows you to disable that callout.
     */
    // @ts-ignore
    touchCallout: 'none',
    /**
     * (iOS only) Sets the color of the highlight that appears over a link while it's being tapped.
     */
    // @ts-ignore
    tapHighlightColor: 'rgba(0,0,0,0)'
  }
};

/**
 * Manager
 */
export class Manager {
  options: Required<ManagerOptions>;

  element: HTMLElement | null;
  touchAction: TouchAction;
  oldCssProps: {[prop: string]: any};
  session: Session;
  recognizers: Recognizer[];
  input: Input;
  handlers: {[event: string]: EventHandler[]};

  constructor(element: HTMLElement, options: ManagerOptions) {
    this.options = {
      ...defaultOptions,
      ...options,
      cssProps: {...defaultOptions.cssProps, ...options.cssProps},
      inputTarget: options.inputTarget || element
    };

    this.handlers = {};
    this.session = {};
    this.recognizers = [];
    this.oldCssProps = {};

    this.element = element;
    this.input = new PointerEventInput(this);
    this.touchAction = new TouchAction(this, this.options.touchAction);

    this.toggleCssProps(true);
  }

  /**
   * set options
   */
  set(options: Partial<ManagerOptions>) {
    Object.assign(this.options, options);

    // Options that need a little more setup
    if (options.touchAction) {
      this.touchAction.update();
    }
    if (options.inputTarget) {
      // Clean up existing event listeners and reinitialize
      this.input.destroy();
      this.input.target = options.inputTarget;
      this.input.init();
    }
    return this;
  }

  /**
   * stop recognizing for this session.
   * This session will be discarded, when a new [input]start event is fired.
   * When forced, the recognizer cycle is stopped immediately.
   */
  stop(force?: boolean) {
    this.session.stopped = force ? FORCED_STOP : STOP;
  }

  /**
   * run the recognizers!
   * called by the inputHandler function on every movement of the pointers (touches)
   * it walks through all the recognizers and tries to detect the gesture that is being made
   */
  recognize(inputData: HammerInput) {
    const {session} = this;
    if (session.stopped) {
      return;
    }

    // run the touch-action polyfill
    if (this.session.prevented) {
      inputData.srcEvent.preventDefault();
    }

    let recognizer;
    const {recognizers} = this;

    // this holds the recognizer that is being recognized.
    // so the recognizer's state needs to be BEGAN, CHANGED, ENDED or RECOGNIZED
    // if no recognizer is detecting a thing, it is set to `null`
    let {curRecognizer} = session;

    // reset when the last recognizer is recognized
    // or when we're in a new session
    if (!curRecognizer || (curRecognizer && curRecognizer.state & RecognizerState.Recognized)) {
      curRecognizer = session.curRecognizer = null;
    }

    let i = 0;
    while (i < recognizers.length) {
      recognizer = recognizers[i];

      // find out if we are allowed try to recognize the input for this one.
      // 1.   allow if the session is NOT forced stopped (see the .stop() method)
      // 2.   allow if we still haven't recognized a gesture in this session, or the this recognizer is the one
      //      that is being recognized.
      // 3.   allow if the recognizer is allowed to run simultaneous with the current recognized recognizer.
      //      this can be setup with the `recognizeWith()` method on the recognizer.
      if (
        session.stopped !== FORCED_STOP && // 1
        (!curRecognizer ||
          recognizer === curRecognizer || // 2
          recognizer.canRecognizeWith(curRecognizer))
      ) {
        // 3
        recognizer.recognize(inputData);
      } else {
        recognizer.reset();
      }

      // if the recognizer has been recognizing the input as a valid gesture, we want to store this one as the
      // current active recognizer. but only if we don't already have an active recognizer
      if (
        !curRecognizer &&
        recognizer.state & (RecognizerState.Began | RecognizerState.Changed | RecognizerState.Ended)
      ) {
        curRecognizer = session.curRecognizer = recognizer;
      }
      i++;
    }
  }

  /**
   * get a recognizer by its event name.
   */
  get(recognizerName: string): Recognizer | null {
    const {recognizers} = this;
    for (let i = 0; i < recognizers.length; i++) {
      if (recognizers[i].options.event === recognizerName) {
        return recognizers[i];
      }
    }
    return null;
  }

  /**
   * add a recognizer to the manager
   * existing recognizers with the same event name will be removed
   */
  add(recognizer: Recognizer | Recognizer[]) {
    if (Array.isArray(recognizer)) {
      for (const item of recognizer) {
        this.add(item);
      }
      return this;
    }

    // remove existing
    const existing = this.get(recognizer.options.event);
    if (existing) {
      this.remove(existing);
    }

    this.recognizers.push(recognizer);
    recognizer.manager = this;

    this.touchAction.update();
    return recognizer;
  }

  /**
   * remove a recognizer by name or instance
   */
  remove(recognizerOrName: Recognizer | string | (Recognizer | string)[]) {
    if (Array.isArray(recognizerOrName)) {
      for (const item of recognizerOrName) {
        this.remove(item);
      }
      return this;
    }

    const recognizer =
      typeof recognizerOrName === 'string' ? this.get(recognizerOrName) : recognizerOrName;

    // let's make sure this recognizer exists
    if (recognizer) {
      const {recognizers} = this;
      const index = recognizers.indexOf(recognizer);

      if (index !== -1) {
        recognizers.splice(index, 1);
        this.touchAction.update();
      }
    }

    return this;
  }

  /**
   * bind event
   */
  on(events: string, handler: EventHandler) {
    if (!events || !handler) {
      return;
    }
    const {handlers} = this;
    for (const event of splitStr(events)) {
      handlers[event] = handlers[event] || [];
      handlers[event].push(handler);
    }
  }

  /**
   * unbind event, leave hander blank to remove all handlers
   */
  off(events: string, handler?: EventHandler) {
    if (!events) {
      return;
    }

    const {handlers} = this;
    for (const event of splitStr(events)) {
      if (!handler) {
        delete handlers[event];
      } else if (handlers[event]) {
        handlers[event].splice(handlers[event].indexOf(handler), 1);
      }
    }
  }

  /**
   * emit event to the listeners
   */
  emit(event: string, data: HammerInput) {
    // no handlers, so skip it all
    const handlers = this.handlers[event] && this.handlers[event].slice();
    if (!handlers || !handlers.length) {
      return;
    }

    const evt = data as HammerEvent;
    evt.type = event;
    evt.preventDefault = function () {
      data.srcEvent.preventDefault();
    };

    let i = 0;
    while (i < handlers.length) {
      handlers[i](evt);
      i++;
    }
  }

  /**
   * destroy the manager and unbinds all events
   * it doesn't unbind dom events, that is the user own responsibility
   */
  destroy() {
    this.toggleCssProps(false);

    this.handlers = {};
    this.session = {};
    this.input.destroy();
    this.element = null;
  }

  /**
   * add/remove the css properties as defined in manager.options.cssProps
   */
  private toggleCssProps(add: boolean) {
    const {element} = this;
    if (!element) {
      return;
    }
    for (const [name, value] of Object.entries(this.options.cssProps)) {
      const prop = prefixed(element.style, name) as any;
      if (add) {
        this.oldCssProps[prop] = element.style[prop];
        element.style[prop] = value as any;
      } else {
        element.style[prop] = this.oldCssProps[prop] || '';
      }
    }
    if (!add) {
      this.oldCssProps = {};
    }
  }
}
