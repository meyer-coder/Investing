// FX Replay (FXR Script) API as documented at custom-indicators.gitbook.io, written as
// TypeScript declarations so scripts can be type-checked the way FX Replay's editor does.
interface FxrPoint { time: number; price: number }
interface RGBAColor { r: number; g: number; b: number; a: number }
declare enum BaseColors { black = 'black', gray = 'gray', silver = 'silver', white = 'white', red = 'red', green = 'green', blue = 'blue', yellow = 'yellow' }
type FxrColor = RGBAColor | BaseColors;
declare const color: {
  black: BaseColors; gray: BaseColors; silver: BaseColors; white: BaseColors; red: BaseColors; green: BaseColors;
  blue: BaseColors; yellow: BaseColors;
  rgba(r: number, g: number, b: number, a: number): RGBAColor;
};
interface FxrLineStyles { linecolor?: FxrColor; linewidth?: number; linestyle?: number; extendRight?: boolean; extendLeft?: boolean; showLabel?: boolean }
declare function trendLine(from: FxrPoint, to: FxrPoint, styles?: FxrLineStyles, text?: string): string;
declare function newPoint(time: number, price: number): FxrPoint;
declare function deleteDrawingById(id: string): void;
declare function high(n: number): number;
declare function low(n: number): number;
declare function openC(n: number): number;
declare function closeC(n: number): number;
declare function time(n: number): number;
declare function indicator(o: { onMainPanel: boolean; format: 'inherit' | 'price' | 'percent' | 'volume'; precision?: number }): object;
declare const input: {
  float(title: string, value: number, id?: string, min?: number, max?: number, step?: number, tooltip?: string, group?: string, inline?: string): { id: string };
  int(title: string, value: number, id?: string, min?: number, max?: number, step?: number, tooltip?: string, group?: string, inline?: string): { id: string };
  bool(title: string, value: boolean, id?: string, group?: string, tooltip?: string, inline?: string): { id: string };
};
declare const plot: {
  shapes(title: string, value: number, text: string, color: string, textColor: string, plottype: string, location: string,
         size: string, offset?: number, transparency?: number, id?: string): { value: number; id: string };
};
declare var index: number;
declare var init: () => void;
declare var onTick: (length: number, _moment: any, _: any, ta: any, inputs: any) => void;
