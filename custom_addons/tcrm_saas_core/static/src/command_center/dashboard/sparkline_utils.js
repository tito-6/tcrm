/** @odoo-module **/

/**
 * Build an SVG path for a compact sparkline (normalized min/max).
 * @param {number[]} values
 * @param {number} width
 * @param {number} height
 */
export function buildSparklinePath(values, width, height) {
    const vals = (values || []).map((v) => Number(v) || 0);
    if (!vals.length) {
        return "";
    }
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const padX = 2;
    const padY = 3;
    const span = Math.max(max - min, 1e-9);
    const w = width - 2 * padX;
    const h = height - 2 * padY;
    return vals
        .map((v, i) => {
            const x = padX + (vals.length === 1 ? w / 2 : (i / (vals.length - 1)) * w);
            const y = padY + h - ((v - min) / span) * h;
            return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" ");
}
