import {AttrRecognizer} from './attribute';
import {InputDirection} from '../input/input-consts';
import {RecognizerState} from '../recognizer/recognizer-state';
import {TOUCH_ACTION_PAN_X, TOUCH_ACTION_PAN_Y} from '../touchaction/touchaction-Consts';
import type {HammerInput} from '../input/types';

export type PanRecognizerOptions = {
  /** Name of the event.
   * @default 'pan'
   */
  event?: string;
  /** Enable this event.
   * @default true
   */
  enable?: boolean;
  /** Required number of pointers. 0 for all pointers.
   * @default 1
   */
  pointers?: number;
  /** Required direction of panning.
   * @default InputDirection.All
   */
  direction?: InputDirection;
  /** Minimal pan distance required before recognizing.
   * @default 10
   */
  threshold?: number;
};

const EVENT_NAMES = ['', 'start', 'move', 'end', 'cancel', 'up', 'down', 'left', 'right'] as const;

/**
 * Pan
 * Recognized when the pointer is down and moved in the allowed direction.
 */
export class PanRecognizer extends AttrRecognizer<Required<PanRecognizerOptions>> {
  pX: number | null;
  pY: number | null;

  constructor(options: PanRecognizerOptions = {}) {
    super({
      enable: true,
      pointers: 1,
      event: 'pan',
      threshold: 10,
      direction: InputDirection.All,
      ...options
    });
    this.pX = null;
    this.pY = null;
  }

  getTouchAction(): string[] {
    const {
      options: {direction}
    } = this;
    const actions: string[] = [];
    if (direction & InputDirection.Horizontal) {
      actions.push(TOUCH_ACTION_PAN_Y);
    }
    if (direction & InputDirection.Vertical) {
      actions.push(TOUCH_ACTION_PAN_X);
    }
    return actions;
  }

  getEventNames(): string[] {
    return EVENT_NAMES.map((suffix) => this.options.event + suffix);
  }

  directionTest(input: HammerInput): boolean {
    const {options} = this;
    let hasMoved = true;
    let {distance} = input;
    let {direction} = input;
    const x = input.deltaX;
    const y = input.deltaY;

    // lock to axis?
    if (!(direction & options.direction)) {
      if (options.direction & InputDirection.Horizontal) {
        direction =
          x === 0 ? InputDirection.None : x < 0 ? InputDirection.Left : InputDirection.Right;
        hasMoved = x !== this.pX;
        distance = Math.abs(input.deltaX);
      } else {
        direction = y === 0 ? InputDirection.None : y < 0 ? InputDirection.Up : InputDirection.Down;
        hasMoved = y !== this.pY;
        distance = Math.abs(input.deltaY);
      }
    }
    input.direction = direction;
    return hasMoved && distance > options.threshold && Boolean(direction & options.direction);
  }

  attrTest(input: HammerInput): boolean {
    return (
      super.attrTest(input) &&
      (Boolean(this.state & RecognizerState.Began) ||
        (!(this.state & RecognizerState.Began) && this.directionTest(input)))
    );
  }

  emit(input: HammerInput) {
    this.pX = input.deltaX;
    this.pY = input.deltaY;

    const direction = InputDirection[input.direction].toLowerCase();

    if (direction) {
      input.additionalEvent = this.options.event + direction;
    }
    super.emit(input);
  }
}
