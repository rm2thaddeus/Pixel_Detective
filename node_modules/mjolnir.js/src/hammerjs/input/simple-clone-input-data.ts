import {getCenter} from './get-center';
import type {RawInput, PointerEventLike, SimpleInput} from './types';

/**
 * create a simple clone from the input used for storage of firstInput and firstMultiple
 */
export function simpleCloneInputData(input: RawInput): SimpleInput {
  // make a simple copy of the pointers because we will get a reference if we don't
  const pointers: PointerEventLike[] = [];
  let i = 0;
  while (i < input.pointers.length) {
    pointers[i] = {
      clientX: Math.round(input.pointers[i].clientX),
      clientY: Math.round(input.pointers[i].clientY)
    };
    i++;
  }

  return {
    timeStamp: Date.now(),
    pointers,
    center: getCenter(pointers),
    deltaX: input.deltaX,
    deltaY: input.deltaY
  };
}
