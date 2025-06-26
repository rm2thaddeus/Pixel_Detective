import {AttrRecognizer} from './attribute';
import {InputDirection, InputEvent} from '../input/input-consts';
import {PanRecognizer} from './pan';
import type {HammerInput} from '../input/types';

export type SwipeRecognizerOptions = {
  /** Name of the event.
   * @default 'swipe'
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
  /** Direction of the panning.
   * @default InputDirection.All
   */
  direction?: InputDirection;
  /** Minimal distance required before recognizing.
   * @default 10
   */
  threshold?: number;
  /** Minimal velocity required before recognizing, in px/ms
   * @default 0.3
   */
  velocity?: number;
};

const EVENT_NAMES = ['', 'up', 'down', 'left', 'right'] as const;

/**
 * Swipe
 * Recognized when the pointer is moving fast (velocity), with enough distance in the allowed direction.
 */
export class SwipeRecognizer extends AttrRecognizer<Required<SwipeRecognizerOptions>> {
  constructor(options: SwipeRecognizerOptions = {}) {
    super({
      enable: true,
      event: 'swipe',
      threshold: 10,
      velocity: 0.3,
      direction: InputDirection.All,
      pointers: 1,
      ...options
    });
  }

  getTouchAction() {
    return PanRecognizer.prototype.getTouchAction.call(this);
  }

  getEventNames(): string[] {
    return EVENT_NAMES.map((suffix) => this.options.event + suffix);
  }

  attrTest(input: HammerInput): boolean {
    const {direction} = this.options;
    let velocity = 0;

    if (direction & InputDirection.All) {
      velocity = input.overallVelocity;
    } else if (direction & InputDirection.Horizontal) {
      velocity = input.overallVelocityX;
    } else if (direction & InputDirection.Vertical) {
      velocity = input.overallVelocityY;
    }

    return (
      super.attrTest(input) &&
      Boolean(direction & input.offsetDirection) &&
      input.distance > this.options.threshold &&
      input.maxPointers === this.options.pointers &&
      Math.abs(velocity) > this.options.velocity &&
      Boolean(input.eventType & InputEvent.End)
    );
  }

  emit(input: HammerInput) {
    const direction = InputDirection[input.offsetDirection].toLowerCase();
    if (direction) {
      this.manager.emit(this.options.event + direction, input);
    }

    this.manager.emit(this.options.event, input);
  }
}
