import type { NormalizedPoint } from "../api/rules";

const EPSILON = 1e-9;

export interface DrawingRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export function normalizePointer(clientX: number, clientY: number, rect: DrawingRect): NormalizedPoint {
  if (rect.width <= 0 || rect.height <= 0) throw new Error("Çizim alanının boyutu geçersiz.");
  const clamp = (value: number) => Math.min(1, Math.max(0, value));
  return {
    x: Number(clamp((clientX - rect.left) / rect.width).toFixed(6)),
    y: Number(clamp((clientY - rect.top) / rect.height).toFixed(6)),
  };
}

function orientation(a: NormalizedPoint, b: NormalizedPoint, c: NormalizedPoint): number {
  return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

function pointOnSegment(a: NormalizedPoint, b: NormalizedPoint, point: NormalizedPoint): boolean {
  return (
    point.x >= Math.min(a.x, b.x) - EPSILON &&
    point.x <= Math.max(a.x, b.x) + EPSILON &&
    point.y >= Math.min(a.y, b.y) - EPSILON &&
    point.y <= Math.max(a.y, b.y) + EPSILON &&
    Math.abs(orientation(a, b, point)) <= EPSILON
  );
}

function segmentsIntersect(
  a: NormalizedPoint,
  b: NormalizedPoint,
  c: NormalizedPoint,
  d: NormalizedPoint,
): boolean {
  const o1 = orientation(a, b, c);
  const o2 = orientation(a, b, d);
  const o3 = orientation(c, d, a);
  const o4 = orientation(c, d, b);
  if ((o1 > EPSILON) !== (o2 > EPSILON) && (o3 > EPSILON) !== (o4 > EPSILON)) return true;
  return (
    (Math.abs(o1) <= EPSILON && pointOnSegment(a, b, c)) ||
    (Math.abs(o2) <= EPSILON && pointOnSegment(a, b, d)) ||
    (Math.abs(o3) <= EPSILON && pointOnSegment(c, d, a)) ||
    (Math.abs(o4) <= EPSILON && pointOnSegment(c, d, b))
  );
}

export function polygonError(points: NormalizedPoint[]): string | null {
  if (points.length < 3) return "Bölgeyi tamamlamak için en az 3 nokta seçin.";
  if (points.length > 50) return "Bir bölgede en fazla 50 nokta olabilir.";
  const unique = new Set(points.map((point) => `${point.x}:${point.y}`));
  if (unique.size !== points.length) return "Aynı nokta birden fazla kez kullanılamaz.";
  const area =
    Math.abs(
      points.reduce((sum, point, index) => {
        const next = points[(index + 1) % points.length];
        return sum + point.x * next.y - next.x * point.y;
      }, 0),
    ) / 2;
  if (area <= EPSILON) return "Seçilen noktalar kapalı bir alan oluşturmuyor.";
  for (let first = 0; first < points.length; first += 1) {
    const firstNext = (first + 1) % points.length;
    for (let second = first + 1; second < points.length; second += 1) {
      const secondNext = (second + 1) % points.length;
      if (firstNext === second || secondNext === first) continue;
      if (segmentsIntersect(points[first], points[firstNext], points[second], points[secondNext])) {
        return "Bölge çizgileri birbiriyle kesişemez.";
      }
    }
  }
  return null;
}
