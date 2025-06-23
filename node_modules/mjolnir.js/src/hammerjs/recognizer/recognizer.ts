import {RecognizerState} from './recognizer-state';
import {uniqueId} from '../utils/unique-id';
import {stateStr} from './state-str';

import type {Manager} from '../manager';
import type {HammerInput} from '../input/types';

export type RecognizerOptions = {
  /** Name of the event */
  event: string;
  /** Enable this recognizer */
  enable: boolean;
};

/**
 * Recognizer flow explained; *
 * All recognizers have the initial state of POSSIBLE when a input session starts.
 * The definition of a input session is from the first input until the last input, with all it's movement in it. *
 * Example session for mouse-input: mousedown -> mousemove -> mouseup
 *
 * On each recognizing cycle (see Manager.recognize) the .recognize() method is executed
 * which determines with state it should be.
 *
 * If the recognizer has the state FAILED, CANCELLED or RECOGNIZED (equals ENDED), it is reset to
 * POSSIBLE to give it another change on the next cycle.
 *
 *               Possible
 *                  |
 *            +-----+---------------+
 *            |                     |
 *      +-----+-----+               |
 *      |           |               |
 *   Failed      Cancelled          |
 *                          +-------+------+
 *                          |              |
 *                      Recognized       Began
 *                                         |
 *                                      Changed
 *                                         |
 *                                  Ended/Recognized
 */

/**
 * Recognizer
 * Every recognizer needs to extend from this class.
 */
export abstract class Recognizer<OptionsT extends RecognizerOptions = any> {
  id: number;
  state: RecognizerState;
  manager!: Manager;

  readonly options: OptionsT;

  protected simultaneous: {[id: string]: Recognizer};
  protected requireFail: Recognizer[];

  constructor(options: OptionsT) {
    this.options = options;

    this.id = uniqueId();

    this.state = RecognizerState.Possible;
    this.simultaneous = {};
    this.requireFail = [];
  }

  /**
   * set options
   */
  set(options: Partial<OptionsT>) {
    Object.assign(this.options, options);

    // also update the touchAction, in case something changed about the directions/enabled state
    this.manager.touchAction.update();
    return this;
  }

  /**
   * recognize simultaneous with an other recognizer.
   */
  recognizeWith(recognizerOrName: Recognizer | string | (Recognizer | string)[]) {
    if (Array.isArray(recognizerOrName)) {
      for (const item of recognizerOrName) {
        this.recognizeWith(item);
      }
      return this;
    }

    let otherRecognizer: Recognizer | null;
    if (typeof recognizerOrName === 'string') {
      otherRecognizer = this.manager.get(recognizerOrName);
      if (!otherRecognizer) {
        throw new Error(`Cannot find recognizer ${recognizerOrName}`);
      }
    } else {
      otherRecognizer = recognizerOrName;
    }
    const {simultaneous} = this;
    if (!simultaneous[otherRecognizer.id]) {
      simultaneous[otherRecognizer.id] = otherRecognizer;
      otherRecognizer.recognizeWith(this);
    }
    return this;
  }

  /**
   * drop the simultaneous link. it doesnt remove the link on the other recognizer.
   */
  dropRecognizeWith(recognizerOrName: Recognizer | string | (Recognizer | string)[]) {
    if (Array.isArray(recognizerOrName)) {
      for (const item of recognizerOrName) {
        this.dropRecognizeWith(item);
      }
      return this;
    }

    let otherRecognizer: Recognizer | null;
    if (typeof recognizerOrName === 'string') {
      otherRecognizer = this.manager.get(recognizerOrName);
    } else {
      otherRecognizer = recognizerOrName;
    }
    if (otherRecognizer) {
      delete this.simultaneous[otherRecognizer.id];
    }
    return this;
  }

  /**
   * recognizer can only run when an other is failing
   */
  requireFailure(recognizerOrName: Recognizer | string | (Recognizer | string)[]) {
    if (Array.isArray(recognizerOrName)) {
      for (const item of recognizerOrName) {
        this.requireFailure(item);
      }
      return this;
    }

    let otherRecognizer: Recognizer | null;
    if (typeof recognizerOrName === 'string') {
      otherRecognizer = this.manager.get(recognizerOrName);
      if (!otherRecognizer) {
        throw new Error(`Cannot find recognizer ${recognizerOrName}`);
      }
    } else {
      otherRecognizer = recognizerOrName;
    }
    const {requireFail} = this;
    if (requireFail.indexOf(otherRecognizer) === -1) {
      requireFail.push(otherRecognizer);
      otherRecognizer.requireFailure(this);
    }
    return this;
  }

  /**
   * drop the requireFailure link. it does not remove the link on the other recognizer.
   */
  dropRequireFailure(recognizerOrName: Recognizer | string | (Recognizer | string)[]) {
    if (Array.isArray(recognizerOrName)) {
      for (const item of recognizerOrName) {
        this.dropRequireFailure(item);
      }
      return this;
    }

    let otherRecognizer: Recognizer | null;
    if (typeof recognizerOrName === 'string') {
      otherRecognizer = this.manager.get(recognizerOrName);
    } else {
      otherRecognizer = recognizerOrName;
    }
    if (otherRecognizer) {
      const index = this.requireFail.indexOf(otherRecognizer);
      if (index > -1) {
        this.requireFail.splice(index, 1);
      }
    }
    return this;
  }

  /**
   * has require failures boolean
   */
  hasRequireFailures(): boolean {
    return Boolean(this.requireFail.find((recognier) => recognier.options.enable));
  }

  /**
   * if the recognizer can recognize simultaneous with an other recognizer
   */
  canRecognizeWith(otherRecognizer: Recognizer): boolean {
    return Boolean(this.simultaneous[otherRecognizer.id]);
  }

  /**
   * You should use `tryEmit` instead of `emit` directly to check
   * that all the needed recognizers has failed before emitting.
   */
  protected emit(input?: HammerInput) {
    // Some recognizers override emit() with their own logic
    if (!input) return;

    const {state} = this;

    // 'panstart' and 'panmove'
    if (state < RecognizerState.Ended) {
      this.manager.emit(this.options.event + stateStr(state), input);
    }

    // simple 'eventName' events
    this.manager.emit(this.options.event, input);

    // additional event(panleft, panright, pinchin, pinchout...)
    if (input.additionalEvent) {
      this.manager.emit(input.additionalEvent, input);
    }

    // panend and pancancel
    if (state >= RecognizerState.Ended) {
      this.manager.emit(this.options.event + stateStr(state), input);
    }
  }

  /**
   * Check that all the require failure recognizers has failed,
   * if true, it emits a gesture event,
   * otherwise, setup the state to FAILED.
   */
  protected tryEmit(input?: HammerInput) {
    if (this.canEmit()) {
      this.emit(input);
    } else {
      // it's failing anyway
      this.state = RecognizerState.Failed;
    }
  }

  /**
   * can we emit?
   */
  protected canEmit(): boolean {
    let i = 0;
    while (i < this.requireFail.length) {
      if (!(this.requireFail[i].state & (RecognizerState.Failed | RecognizerState.Possible))) {
        return false;
      }
      i++;
    }
    return true;
  }

  /**
   * update the recognizer
   */
  recognize(inputData: HammerInput) {
    // make a new copy of the inputData
    // so we can change the inputData without messing up the other recognizers
    const inputDataClone = {...inputData};

    // is is enabled and allow recognizing?
    if (!this.options.enable) {
      this.reset();
      this.state = RecognizerState.Failed;
      return;
    }

    // reset when we've reached the end
    if (
      this.state &
      (RecognizerState.Recognized | RecognizerState.Cancelled | RecognizerState.Failed)
    ) {
      this.state = RecognizerState.Possible;
    }

    this.state = this.process(inputDataClone);

    // the recognizer has recognized a gesture
    // so trigger an event
    if (
      this.state &
      (RecognizerState.Began |
        RecognizerState.Changed |
        RecognizerState.Ended |
        RecognizerState.Cancelled)
    ) {
      this.tryEmit(inputDataClone);
    }
  }

  /**
   * return the state of the recognizer
   * the actual recognizing happens in this method
   */

  abstract process(inputData: HammerInput): RecognizerState;

  /**
   * return the preferred touch-action
   */
  abstract getTouchAction(): string[];

  /**
   * return the event names that are emitted by this recognizer
   */
  getEventNames(): string[] {
    return [this.options.event];
  }

  /**
   * called when the gesture isn't allowed to recognize
   * like when another is being recognized or it is disabled
   */
  reset(): void {}
}
