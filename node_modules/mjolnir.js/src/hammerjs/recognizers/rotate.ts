import {AttrRecognizer} from './attribute';
import {TOUCH_ACTION_NONE} from '../touchaction/touchaction-Consts';
import {RecognizerState} from '../recognizer/recognizer-state';
import type {HammerInput} from '../input/types';

export type RotateRecognizerOptions = {
  /** Name of the event.
   * @default 'rotate'
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
  /** Minimal rotation before recognizing.
   * @default 0
   */
  threshold?: number;
};

const EVENT_NAMES = ['', 'start', 'move', 'end', 'cancel'] as const;

/**
 * Rotate
 * Recognized when two or more pointer are moving in a circular motion.
 */
export class RotateRecognizer extends AttrRecognizer<Required<RotateRecognizerOptions>> {
  constructor(options: RotateRecognizerOptions = {}) {
    super({
      enable: true,
      event: 'rotate',
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
      (Math.abs(input.rotation) > this.options.threshold ||
        Boolean(this.state & RecognizerState.Began))
    );
  }
}
