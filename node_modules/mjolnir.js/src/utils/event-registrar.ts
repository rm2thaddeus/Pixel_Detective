// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import type {EventManager} from '../event-manager';
import {whichButtons, getOffsetPosition} from './event-utils';
import type {
  MjolnirEventRaw,
  MjolnirEventWrapper,
  MjolnirEvent,
  MjolnirEventHandler
} from '../types';

export type HandlerOptions = {
  /** Optional element from which the event is originated from.
   * @default 'root'
   */
  srcElement?: 'root' | HTMLElement;
  /** Handler with higher priority will be called first.
   * Handler with the same priority will be called in the order of registration.
   * @default 0
   */
  priority?: number;
};

type EventHandler = {
  type: string;
  handler: (event: MjolnirEvent) => void;
  once?: boolean;
  passive?: boolean;
  srcElement: 'root' | HTMLElement;
  priority: number;
};

const DEFAULT_OPTIONS: Required<HandlerOptions> = {
  srcElement: 'root',
  priority: 0
};

export class EventRegistrar {
  eventManager: EventManager;
  recognizerName: string;
  handlers: EventHandler[];
  handlersByElement: Map<'root' | HTMLElement, EventHandler[]>;
  _active: boolean;

  constructor(eventManager: EventManager, recognizerName: string) {
    this.eventManager = eventManager;
    this.recognizerName = recognizerName;
    this.handlers = [];
    // Element -> handler map
    this.handlersByElement = new Map();

    this._active = false;
  }

  // Returns true if there are no non-passive handlers
  isEmpty(): boolean {
    return !this._active;
  }

  add(
    type: string,
    handler: MjolnirEventHandler,
    options?: HandlerOptions,
    once: boolean = false,
    passive: boolean = false
  ) {
    const {handlers, handlersByElement} = this;
    const opts: Required<HandlerOptions> = {...DEFAULT_OPTIONS, ...options};

    let entries = handlersByElement.get(opts.srcElement);
    if (!entries) {
      entries = [];
      handlersByElement.set(opts.srcElement, entries);
    }
    const entry: EventHandler = {
      type,
      handler,
      srcElement: opts.srcElement,
      priority: opts.priority
    };
    if (once) {
      entry.once = true;
    }
    if (passive) {
      entry.passive = true;
    }
    handlers.push(entry);
    this._active = this._active || !entry.passive;

    // Sort handlers by descending priority
    // Handlers with the same priority are excuted in the order of registration
    let insertPosition = entries.length - 1;
    while (insertPosition >= 0) {
      if (entries[insertPosition].priority >= entry.priority) {
        break;
      }
      insertPosition--;
    }
    entries.splice(insertPosition + 1, 0, entry);
  }

  remove(type: string, handler: MjolnirEventHandler) {
    const {handlers, handlersByElement} = this;

    for (let i = handlers.length - 1; i >= 0; i--) {
      const entry = handlers[i];

      if (entry.type === type && entry.handler === handler) {
        handlers.splice(i, 1);
        const entries = handlersByElement.get(entry.srcElement)!;
        entries.splice(entries.indexOf(entry), 1);
        if (entries.length === 0) {
          handlersByElement.delete(entry.srcElement);
        }
      }
    }
    this._active = handlers.some((entry) => !entry.passive);
  }

  /**
   * Handles hammerjs event
   */
  handleEvent = (event: MjolnirEventRaw) => {
    if (this.isEmpty()) {
      return;
    }

    const mjolnirEvent = this._normalizeEvent(event);
    let target = event.srcEvent.target as HTMLElement;

    while (target && target !== mjolnirEvent.rootElement) {
      this._emit(mjolnirEvent, target);
      if (mjolnirEvent.handled) {
        return;
      }
      target = target.parentNode as HTMLElement;
    }
    this._emit(mjolnirEvent, 'root');
  };

  /**
   * Invoke handlers on a particular element
   */
  _emit<T extends MjolnirEventRaw>(
    event: MjolnirEventWrapper<T>,
    srcElement: 'root' | HTMLElement
  ) {
    const entries = this.handlersByElement.get(srcElement);

    if (entries) {
      let immediatePropagationStopped = false;

      // Prevents the current event from bubbling up
      const stopPropagation = () => {
        event.handled = true;
      };
      // Prevent any remaining listeners from being called
      const stopImmediatePropagation = () => {
        event.handled = true;
        immediatePropagationStopped = true;
      };
      const entriesToRemove: EventHandler[] = [];

      for (let i = 0; i < entries.length; i++) {
        const {type, handler, once} = entries[i];
        // @ts-ignore
        handler({
          ...event,
          type,
          stopPropagation,
          stopImmediatePropagation
        });
        if (once) {
          entriesToRemove.push(entries[i]);
        }
        if (immediatePropagationStopped) {
          break;
        }
      }

      for (let i = 0; i < entriesToRemove.length; i++) {
        const {type, handler} = entriesToRemove[i];
        this.remove(type, handler);
      }
    }
  }

  /**
   * Normalizes hammerjs and custom events to have predictable fields.
   */
  _normalizeEvent<T extends MjolnirEventRaw>(event: T): MjolnirEventWrapper<T> {
    const rootElement = this.eventManager.getElement();

    // @ts-ignore
    return {
      ...event,
      ...whichButtons(event),
      ...getOffsetPosition(event, rootElement!),
      preventDefault: () => {
        event.srcEvent.preventDefault();
      },
      stopImmediatePropagation: null,
      stopPropagation: null,
      handled: false,
      rootElement
    };
  }
}
