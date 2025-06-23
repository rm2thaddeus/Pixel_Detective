import {InputEvent} from '../input/input-consts';
import {Input} from '../input/input';
import type {Manager} from '../manager';

const POINTER_INPUT_MAP = {
  pointerdown: InputEvent.Start,
  pointermove: InputEvent.Move,
  pointerup: InputEvent.End,
  pointercancel: InputEvent.Cancel,
  pointerout: InputEvent.Cancel
} as const;

const POINTER_ELEMENT_EVENTS = 'pointerdown';
const POINTER_WINDOW_EVENTS = 'pointermove pointerup pointercancel';

/**
 * Pointer events input
 */
export class PointerEventInput extends Input {
  store: PointerEvent[];

  constructor(manager: Manager) {
    super(manager);
    this.evEl = POINTER_ELEMENT_EVENTS;
    this.evWin = POINTER_WINDOW_EVENTS;

    this.store = this.manager.session.pointerEvents = [];
    this.init();
  }

  /**
   * handle mouse events
   */
  handler(ev: PointerEvent) {
    const {store} = this;
    let removePointer = false;

    // @ts-ignore
    const eventType = POINTER_INPUT_MAP[ev.type];
    const pointerType = ev.pointerType;

    const isTouch = pointerType === 'touch';

    // get index of the event in the store
    let storeIndex = store.findIndex((e) => e.pointerId === ev.pointerId);

    // start and mouse must be down
    if (eventType & InputEvent.Start && (ev.buttons || isTouch)) {
      if (storeIndex < 0) {
        store.push(ev);
        storeIndex = store.length - 1;
      }
    } else if (eventType & (InputEvent.End | InputEvent.Cancel)) {
      removePointer = true;
    }

    // it not found, so the pointer hasn't been down (so it's probably a hover)
    if (storeIndex < 0) {
      return;
    }

    // update the event in the store
    store[storeIndex] = ev;

    this.callback(eventType, {
      pointers: store,
      changedPointers: [ev],
      eventType,
      pointerType,
      srcEvent: ev
    });

    if (removePointer) {
      // remove from the store
      store.splice(storeIndex, 1);
    }
  }
}
