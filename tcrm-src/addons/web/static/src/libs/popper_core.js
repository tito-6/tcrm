/** @tcrm-module alias=@popperjs/core */
const Popper = window.Popper || {};

export const createPopper = Popper.createPopper;
export const createPopperLite = Popper.createPopperLite;
export const popperGenerator = Popper.popperGenerator;
export const detectOverflow = Popper.detectOverflow;
export const offset = Popper.offset;
export const flip = Popper.flip;
export const preventOverflow = Popper.preventOverflow;
export const arrow = Popper.arrow;
export const hide = Popper.hide;
export const auto = Popper.auto;
export const placements = Popper.placements;

export default Popper;
