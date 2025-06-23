// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import type {MjolnirEventRaw} from '../types';

export interface InputOptions {
  enable?: boolean;
}

export class Input<EventType extends MjolnirEventRaw, Options extends InputOptions> {
  element: HTMLElement;
  options: Options;
  callback: (e: EventType) => void;

  constructor(element: HTMLElement, callback: (e: EventType) => void, options: Options) {
    this.element = element;
    this.callback = callback;
    this.options = options;
  }
}
