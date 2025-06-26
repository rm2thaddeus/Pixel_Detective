import {AttrRecognizer} from './attribute';
import {TOUCH_ACTION_NONE} from '../touchaction/touchaction-Consts';
import {RecognizerState} from '../recognizer/recognizer-state';
import type {HammerInput} from '../input/types';

export type PinchRecognizerOptions = {
  /** Name of the event.
   * @default 'pinch'
   */
  event?: string;
  /** Enable this event.
   * @default true
   */
  enable?: boolean;
  /** Required number of pointers, with a minimum of 2.
   * @default 2
   */
  pointers?: number;
  /** Minimal scale before recognizing.
   * @default 0
   */
  threshold?: number;
};

const EVENT_NAMES = ['', 'start', 'move', 'end', 'cancel', 'in', 'out'] as const;

/**
 * Pinch
 * Recognized when two or more pointers are moving toward (zoom-in) or away from each other (zoom-out).
 */
export class PinchRecognizer extends AttrRecognizer<Required<PinchRecognizerOptions>> {
  constructor(options: PinchRecognizerOptions = {}) {
    super({
      enable: true,
      event: 'pinch',
      threshold: 0,
      pointers: 2,
      ...options
    });
  }

  getTouchAction() {
    return [TOUCH_ACTION_NONE];
  }

  getEventNames(): string[] {
    return EVENT_NAMES.map((suffix) => this.options.event + suffix);
  }

  attrTest(input: HammerInput): boolean {
    return (
      super.attrTest(input) &&
      (Math.abs(input.scale - 1) > this.options.threshold ||
        Boolean(this.state & RecognizerState.Began))
    );
  }

  emit(input: HammerInput) {
    if (input.scale !== 1) {
      const inOut = input.scale < 1 ? 'in' : 'out';
      input.additionalEvent = this.options.event + inOut;
    }
    super.emit(input);
  }
}
