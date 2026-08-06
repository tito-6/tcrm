/** @tcrm-module alias=@tcrm/hoot-mock default=false */

import * as _hootDom from "@tcrm/hoot-dom";
import * as _animation from "./mock/animation";
import * as _date from "./mock/date";
import * as _math from "./mock/math";
import * as _navigator from "./mock/navigator";
import * as _network from "./mock/network";
import * as _notification from "./mock/notification";
import * as _window from "./mock/window";

/** @deprecated use `import { advanceFrame } from "@tcrm/hoot";` */
export const advanceFrame = _hootDom.advanceFrame;
/** @deprecated use `import { advanceTime } from "@tcrm/hoot";` */
export const advanceTime = _hootDom.advanceTime;
/** @deprecated use `import { animationFrame } from "@tcrm/hoot";` */
export const animationFrame = _hootDom.animationFrame;
/** @deprecated use `import { cancelAllTimers } from "@tcrm/hoot";` */
export const cancelAllTimers = _hootDom.cancelAllTimers;
/** @deprecated use `import { Deferred } from "@tcrm/hoot";` */
export const Deferred = _hootDom.Deferred;
/** @deprecated use `import { delay } from "@tcrm/hoot";` */
export const delay = _hootDom.delay;
/** @deprecated use `import { freezeTime } from "@tcrm/hoot";` */
export const freezeTime = _hootDom.freezeTime;
/** @deprecated use `import { microTick } from "@tcrm/hoot";` */
export const microTick = _hootDom.microTick;
/** @deprecated use `import { runAllTimers } from "@tcrm/hoot";` */
export const runAllTimers = _hootDom.runAllTimers;
/** @deprecated use `import { setFrameRate } from "@tcrm/hoot";` */
export const setFrameRate = _hootDom.setFrameRate;
/** @deprecated use `import { tick } from "@tcrm/hoot";` */
export const tick = _hootDom.tick;
/** @deprecated use `import { unfreezeTime } from "@tcrm/hoot";` */
export const unfreezeTime = _hootDom.unfreezeTime;

/** @deprecated use `import { disableAnimations } from "@tcrm/hoot";` */
export const disableAnimations = _animation.disableAnimations;
/** @deprecated use `import { enableTransitions } from "@tcrm/hoot";` */
export const enableTransitions = _animation.enableTransitions;

/** @deprecated use `import { mockDate } from "@tcrm/hoot";` */
export const mockDate = _date.mockDate;
/** @deprecated use `import { mockLocale } from "@tcrm/hoot";` */
export const mockLocale = _date.mockLocale;
/** @deprecated use `import { mockTimeZone } from "@tcrm/hoot";` */
export const mockTimeZone = _date.mockTimeZone;
/** @deprecated use `import { onTimeZoneChange } from "@tcrm/hoot";` */
export const onTimeZoneChange = _date.onTimeZoneChange;

/** @deprecated use `import { makeSeededRandom } from "@tcrm/hoot";` */
export const makeSeededRandom = _math.makeSeededRandom;

/** @deprecated use `import { mockPermission } from "@tcrm/hoot";` */
export const mockPermission = _navigator.mockPermission;
/** @deprecated use `import { mockSendBeacon } from "@tcrm/hoot";` */
export const mockSendBeacon = _navigator.mockSendBeacon;
/** @deprecated use `import { mockUserAgent } from "@tcrm/hoot";` */
export const mockUserAgent = _navigator.mockUserAgent;
/** @deprecated use `import { mockVibrate } from "@tcrm/hoot";` */
export const mockVibrate = _navigator.mockVibrate;

/** @deprecated use `import { mockFetch } from "@tcrm/hoot";` */
export const mockFetch = _network.mockFetch;
/** @deprecated use `import { mockLocation } from "@tcrm/hoot";` */
export const mockLocation = _network.mockLocation;
/** @deprecated use `import { mockWebSocket } from "@tcrm/hoot";` */
export const mockWebSocket = _network.mockWebSocket;
/** @deprecated use `import { mockWorker } from "@tcrm/hoot";` */
export const mockWorker = _network.mockWorker;

/** @deprecated use `import { flushNotifications } from "@tcrm/hoot";` */
export const flushNotifications = _notification.flushNotifications;

/** @deprecated use `import { mockMatchMedia } from "@tcrm/hoot";` */
export const mockMatchMedia = _window.mockMatchMedia;
/** @deprecated use `import { mockTouch } from "@tcrm/hoot";` */
export const mockTouch = _window.mockTouch;
/** @deprecated use `import { watchAddedNodes } from "@tcrm/hoot";` */
export const watchAddedNodes = _window.watchAddedNodes;
/** @deprecated use `import { watchKeys } from "@tcrm/hoot";` */
export const watchKeys = _window.watchKeys;
/** @deprecated use `import { watchListeners } from "@tcrm/hoot";` */
export const watchListeners = _window.watchListeners;
