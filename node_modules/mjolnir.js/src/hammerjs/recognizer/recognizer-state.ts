export enum RecognizerState {
  Possible = 1,
  Began = 2,
  Changed = 4,
  Ended = 8,
  Recognized = 8, // eslint-disable-line
  Cancelled = 16,
  Failed = 32
}
