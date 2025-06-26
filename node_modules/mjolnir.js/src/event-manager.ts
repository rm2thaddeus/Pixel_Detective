// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import {Manager as HammerManager, Recognizer} from './hammerjs/index';
import type {
  MjolnirEventRaw,
  MjolnirEvent,
  MjolnirEventHandler,
  MjolnirEventHandlers
} from './types';

import {WheelInput} from './inputs/wheel-input';
import {MoveInput} from './inputs/move-input';
import {KeyInput} from './inputs/key-input';
import {ContextmenuInput} from './inputs/contextmenu-input';

import {EventRegistrar, HandlerOptions} from './utils/event-registrar';

type RecognizerConstructor = {new (options: any): Recognizer};

type RecognizerTupleNormalized = {
  recognizer: Recognizer;
  /** Allow another gesture to be recognized simultaneously with this one.
   * For example an interaction can trigger pinch and rotate at the same time. */
  recognizeWith?: string[];
  /** Another recognizer is mutually exclusive with this one.
   * For example an interaction could be singletap or doubletap; pan-horizontal or pan-vertical; but never both. */
  requireFailure?: string[];
};

export type RecognizerTuple =
  | Recognizer
  | RecognizerConstructor
  | RecognizerTupleNormalized
  /** hammer.js/mjolnir.js@2 style */
  | [
      recognizer: RecognizerConstructor,
      options?: any,
      /** Allow another gesture to be recognized simultaneously with this one.
       * For example an interaction can trigger pinch and rotate at the same time. */
      recognizeWith?: string | string[],
      /** Another recognizer is mutually exclusive with this one.
       * For example an interaction could be singletap or doubletap; pan-horizontal or pan-vertical; but never both. */
      requireFailure?: string | string[]
    ];

export type EventManagerOptions = {
  /** Event listeners */
  events?: MjolnirEventHandlers;
  /** Gesture recognizers */
  recognizers?: RecognizerTuple[];
  /** Touch action to set on the target element.
   * Use 'compute' to automatically set as the least restrictive value to support the recognizers.
   * https://developer.mozilla.org/en-US/docs/Web/CSS/touch-action
   * @default 'compute'
   */
  touchAction?: 'none' | 'compute' | 'manipulation' | 'pan-x' | 'pan-y' | 'pan-x pan-y';
  /** Tab index of the target element */
  tabIndex?: number;
  /**
   * Optional CSS properties to be applied to the target element.
   */
  cssProps?: Partial<CSSStyleDeclaration>;
};

function normalizeRecognizer(item: RecognizerTuple): RecognizerTupleNormalized {
  if ('recognizer' in item) {
    return item;
  }
  let recognizer: Recognizer;
  const itemArray = Array.isArray(item) ? [...item] : [item];
  if (typeof itemArray[0] === 'function') {
    // Backward compatibility: v2 / hammerjs style
    const RecognizerType = itemArray.shift();
    const options = itemArray.shift() || {};
    recognizer = new RecognizerType(options);
  } else {
    recognizer = itemArray.shift();
  }
  return {
    recognizer,
    recognizeWith: typeof itemArray[0] === 'string' ? [itemArray[0]] : itemArray[0],
    requireFailure: typeof itemArray[1] === 'string' ? [itemArray[1]] : itemArray[1]
  };
}

// Unified API for subscribing to events about both
// basic input events (e.g. 'mousemove', 'touchstart', 'wheel')
// and gestural input (e.g. 'click', 'tap', 'panstart').
// Delegates gesture related event registration and handling to Hammer.js.
export class EventManager {
  private element: HTMLElement | null;
  private manager: HammerManager;
  private options: Required<EventManagerOptions>;
  private events: Map<string, EventRegistrar>;

  // Custom handlers
  private wheelInput: WheelInput;
  private moveInput: MoveInput;
  private contextmenuInput: ContextmenuInput;
  private keyInput: KeyInput;

  constructor(element: HTMLElement | null = null, options: EventManagerOptions = {}) {
    this.options = {
      recognizers: [],
      events: {},
      touchAction: 'compute',
      tabIndex: 0,
      cssProps: {},
      ...options
    };
    this.events = new Map();
    this.element = element;

    if (!element) return;

    this.manager = new HammerManager(element, this.options);
    for (const item of this.options.recognizers) {
      const {recognizer, recognizeWith, requireFailure} = normalizeRecognizer(item);
      this.manager.add(recognizer);
      if (recognizeWith) {
        recognizer.recognizeWith(recognizeWith);
      }
      if (requireFailure) {
        recognizer.requireFailure(requireFailure);
      }
    }

    this.manager.on('hammer.input', this._onBasicInput);

    // Handle events not handled by Hammer.js:
    // - mouse wheel
    // - pointer/touch/mouse move
    this.wheelInput = new WheelInput(element, this._onOtherEvent, {
      enable: false
    });
    this.moveInput = new MoveInput(element, this._onOtherEvent, {
      enable: false
    });
    this.keyInput = new KeyInput(element, this._onOtherEvent, {
      enable: false,
      tabIndex: options.tabIndex
    });
    this.contextmenuInput = new ContextmenuInput(element, this._onOtherEvent, {
      enable: false
    });

    // Register all passed events.
    this.on(this.options.events);
  }

  getElement(): HTMLElement | null {
    return this.element;
  }

  // Tear down internal event management implementations.
  destroy(): void {
    // manager etc. cannot exist if there is no element
    if (!this.element) return;

    this.wheelInput.destroy();
    this.moveInput.destroy();
    this.keyInput.destroy();
    this.contextmenuInput.destroy();
    this.manager.destroy();
  }

  /** Register multiple event handlers */
  on(events: MjolnirEventHandlers, opts?: HandlerOptions): void;
  on<EventT extends MjolnirEvent>(
    event: EventT['type'],
    handler: (ev: EventT) => void,
    opts?: HandlerOptions
  ): void;

  /** Register an event handler function to be called on `event` */
  on(event: any, handler: any, opts?: any) {
    this._addEventHandler(event, handler, opts, false);
  }

  /** Register an event handler function to be called on `event`, then remove it */
  once(events: MjolnirEventHandlers, opts?: HandlerOptions): void;
  once<EventT extends MjolnirEvent>(
    event: EventT['type'],
    handler: (ev: EventT) => void,
    opts?: HandlerOptions
  ): void;

  once(event: any, handler: any, opts?: any) {
    this._addEventHandler(event, handler, opts, true);
  }

  /** Register an event handler function to be called on `event`
   * This handler does not ask the event to be recognized at all times.
   * Instead, it only "intercepts" the event if some other handler is getting it.
   */
  watch(events: MjolnirEventHandlers, opts?: HandlerOptions): void;
  watch<EventT extends MjolnirEvent>(
    event: EventT['type'],
    handler: (ev: EventT) => void,
    opts?: HandlerOptions
  ): void;

  watch(event: any, handler: any, opts?: any) {
    this._addEventHandler(event, handler, opts, false, true);
  }

  /**
   * Deregister a previously-registered event handler.
   */
  off(events: MjolnirEventHandlers): void;
  off<EventT extends MjolnirEvent>(event: EventT['type'], handler: (ev: EventT) => void): void;

  off(event: any, handler?: any) {
    this._removeEventHandler(event, handler);
  }

  /*
   * Enable/disable recognizer for the given event
   */
  private _toggleRecognizer(name: string, enabled: boolean): void {
    const {manager} = this;
    if (!manager) {
      return;
    }
    const recognizer = manager.get(name);
    if (recognizer) {
      recognizer.set({enable: enabled});
      manager.touchAction.update();
    }
    this.wheelInput?.enableEventType(name, enabled);
    this.moveInput?.enableEventType(name, enabled);
    this.keyInput?.enableEventType(name, enabled);
    this.contextmenuInput?.enableEventType(name, enabled);
  }

  /**
   * Process the event registration for a single event + handler.
   */
  private _addEventHandler(
    event: string | MjolnirEventHandlers,
    handler: MjolnirEventHandler,
    opts?: HandlerOptions,
    once?: boolean,
    passive?: boolean
  ) {
    if (typeof event !== 'string') {
      // @ts-ignore
      opts = handler;
      // If `event` is a map, call `on()` for each entry.
      for (const [eventName, eventHandler] of Object.entries(event)) {
        this._addEventHandler(eventName, eventHandler, opts, once, passive);
      }
      return;
    }

    const {manager, events} = this;
    if (!manager) return;

    let eventRegistrar = events.get(event);
    if (!eventRegistrar) {
      // Enable recognizer for this event.
      const recognizerName = this._getRecognizerName(event) || event;

      eventRegistrar = new EventRegistrar(this, recognizerName);
      events.set(event, eventRegistrar);
      // Listen to the event
      if (manager) {
        manager.on(event, eventRegistrar.handleEvent);
      }
    }
    eventRegistrar.add(event, handler, opts, once, passive);
    if (!eventRegistrar.isEmpty()) {
      this._toggleRecognizer(eventRegistrar.recognizerName, true);
    }
  }

  /**
   * Process the event deregistration for a single event + handler.
   */
  private _removeEventHandler(event: string | MjolnirEventHandlers, handler?: MjolnirEventHandler) {
    if (typeof event !== 'string') {
      // If `event` is a map, call `off()` for each entry.
      for (const [eventName, eventHandler] of Object.entries(event)) {
        this._removeEventHandler(eventName, eventHandler);
      }
      return;
    }

    const {events} = this;

    const eventRegistrar = events.get(event);

    if (!eventRegistrar) {
      return;
    }

    eventRegistrar.remove(event, handler!);

    if (eventRegistrar.isEmpty()) {
      const {recognizerName} = eventRegistrar;
      // Disable recognizer if no more handlers are attached to its events
      let isRecognizerUsed = false;
      for (const eh of events.values()) {
        if (eh.recognizerName === recognizerName && !eh.isEmpty()) {
          isRecognizerUsed = true;
          break;
        }
      }
      if (!isRecognizerUsed) {
        this._toggleRecognizer(recognizerName, false);
      }
    }
  }

  private _getRecognizerName(event: string): string | undefined {
    return this.manager.recognizers.find((recognizer) => {
      return recognizer.getEventNames().includes(event);
    })?.options.event;
  }

  /**
   * Handle basic events using the 'hammer.input' Hammer.js API:
   * Before running Recognizers, Hammer emits a 'hammer.input' event
   * with the basic event info. This function emits all basic events
   * aliased to the "class" of event received.
   * See constants.BASIC_EVENT_CLASSES basic event class definitions.
   */
  private _onBasicInput = (event: MjolnirEventRaw) => {
    this.manager.emit(event.srcEvent.type, event as any);
  };

  /**
   * Handle events not supported by Hammer.js,
   * and pipe back out through same (Hammer) channel used by other events.
   */
  private _onOtherEvent = (event: MjolnirEventRaw) => {
    // console.log('onotherevent', event.type, event)
    this.manager.emit(event.type, event as any);
  };
}
