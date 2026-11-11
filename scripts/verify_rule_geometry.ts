/** F3 çizim koordinatlarını doğrudan arayüzün kullandığı kodla doğrular. */

import { normalizePointer, polygonError } from "../frontend/src/rules/geometry.ts";

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(message);
}

const large = { left: 120, top: 80, width: 1600, height: 900 };
const small = { left: 12, top: 8, width: 800, height: 450 };
const largePoint = normalizePointer(520, 305, large);
const smallPoint = normalizePointer(212, 120.5, small);

assert(largePoint.x === 0.25 && largePoint.y === 0.25, "Büyük alanda koordinat yanlış");
assert(smallPoint.x === 0.25 && smallPoint.y === 0.25, "Ölçek değişince koordinat değişti");
assert(normalizePointer(120, 80, large).x === 0, "Sol kenar sıfıra karşılık gelmiyor");
assert(normalizePointer(1720, 980, large).x === 1, "Sağ kenar bire karşılık gelmiyor");
assert(
  polygonError([
    { x: 0.1, y: 0.1 },
    { x: 0.9, y: 0.9 },
    { x: 0.1, y: 0.9 },
    { x: 0.9, y: 0.1 },
  ]) !== null,
  "Kendi kendini kesen çokgen kabul edildi",
);
assert(
  polygonError([
    { x: 0.1, y: 0.1 },
    { x: 0.9, y: 0.1 },
    { x: 0.5, y: 0.9 },
  ]) === null,
  "Geçerli üçgen reddedildi",
);

console.log("F3 çizim geometrisi: 6 kontrol geçti.");
