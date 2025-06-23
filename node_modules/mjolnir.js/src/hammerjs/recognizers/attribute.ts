import {Recognizer, RecognizerOptions} from '../recognizer/recognizer';
import {RecognizerState} from '../recognizer/recognizer-state';
import {InputEvent} from '../input/input-consts';
import type {HammerInput} from '../input/types';

type AttrRecognizerOptions = RecognizerOptions & {
  pointers: number;
};

/**
 * This recognizer is just used as a base for the simple attribute recognizers.
 */
export abstract class AttrRecognizer<
  OptionsT extends AttrRecognizerOptions
> extends Recognizer<OptionsT> {
  /**
   * Used to check if it the recognizer receives valid input, like input.distance > 10.
   */
  attrTest(input: HammerInput): boolean {
    const optionPointers = this.options.pointers;
    return optionPointers === 0 || input.pointers.length === optionPointers;
  }

  /**
   * Process the input and return the state for the recognizer
   */
  process(input: HammerInput) {
    const {state} = this;
    const {eventType} = input;

    const isRecognized = state & (RecognizerState.Began | RecognizerState.Changed);
    const isValid = this.attrTest(input);

    // on cancel input and we've recognized before, return STATE_CANCELLED
    if (isRecognized && (eventType & InputEvent.Cancel || !isValid)) {
      return state | RecognizerState.Cancelled;
    } else if (isRecognized || isValid) {
      if (eventType & InputEvent.End) {
        return state | RecognizerState.Ended;
      } else if (!(state & RecognizerState.Began)) {
        return RecognizerState.Began;
      }
      return state | RecognizerState.Changed;
    }
    return RecognizerState.Failed;
  }
}
