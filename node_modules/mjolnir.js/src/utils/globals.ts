// mjolnir.js
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

// Purpose: include this in your module to avoids adding dependencies on
// micro modules like 'global'

/* global window, global, document, navigator */
export const userAgent =
  typeof navigator !== 'undefined' && navigator.userAgent ? navigator.userAgent.toLowerCase() : '';

const window_ = typeof window !== 'undefined' ? window : global;
const global_ = typeof global !== 'undefined' ? global : window;
const document_ = typeof document !== 'undefined' ? document : {};

export {window_ as window, global_ as global, document_ as document};
