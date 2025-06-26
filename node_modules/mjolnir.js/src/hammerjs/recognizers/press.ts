/* global setTimeout, clearTimeout */
import {Recognizer} from '../recognizer/recognizer';
import {RecognizerState} from '../recognizer/recognizer-state';
import {TOUCH_ACTION_AUTO} from '../touchaction/touchaction-Consts';
import {InputEvent} from '../input/input-consts';
import {HammerInput} from '../input/types';

export type PressRecognizerOptions = {
  /** Name of the event.
   * @default 'press'
   */
  event?: string;
  /** Enable this event.
   * @default true
   */
  enable?: boolean;
  /** Required number of pointers.
   * @default 1
   */
  pointers?: number;
  /** Minimal press time in ms.
   * @default 251
   */
  time?: number;
  /** Minimal movement that is allowed while pressing.
   * @default 9
   */
  threshold?: number;
};

const EVENT_NAMES = ['', 'up'] as const;

/**
 * Press
 * Recognized when the pointer is down for x ms without any movement.
 */
export class PressRecognizer extends Recognizer<Required<PressRecognizerOptions>> {
  private _timer: any = null;
  private _input: HammerInput | null = null;

  constructor(options: PressRecognizerOptions = {}) {
    super({
      enable: true,
      event: 'press',
      pointers: 1,
      time: 251,
      threshold: 9,
      ...options
    });
  }

  getTouchAction() {
    return [TOUCH_ACTION_AUTO];
  }

  getEventNames(): string[] {
    return EVENT_NAMES.map((suffix) => this.options.event + suffix);
  }

  process(input: HammerInput) {
    const {options} = this;
    const validPointers = input.pointers.length === options.pointers;
    const validMovement = input.distance < options.threshold;
    const validTime = input.deltaTime > options.time;

    this._input = input;

    // we only allow little movement
    // and we've reached an end event, so a tap is possible
    if (
      !validMovement ||
      !validPointers ||
      (input.eventType & (InputEvent.End | InputEvent.Cancel) && !validTime)
    ) {
      this.reset();
    } else if (input.eventType & InputEvent.Start) {
      this.reset();
      this._timer = setTimeout(() => {
        this.state = RecognizerState.Recognized;
        this.tryEmit();
      }, options.time);
    } else if (input.eventType & InputEvent.End) {
      return RecognizerState.Recognized;
    }
    return RecognizerState.Failed;
  }

  reset() {
    clearTimeout(this._timer);
  }

  emit(input?: HammerInput) {
    if (this.state !== RecognizerState.Recognized) {
      return;
    }

    if (input && input.eventType & InputEvent.End) {
      this.manager.emit(`${this.options.event}up`, input);
    } else {
      this._input!.timeStamp = Date.now();
      this.manager.emit(this.options.event, this._input!);
    }
  }
}
