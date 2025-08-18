declare module 'verovio' {
  export interface VerovioToolkit {
    setOptions(options: any): void;
    loadData(data: string): boolean;
    renderToSVG(pageNumber?: number): string;
    getElementsAtTime(time: number): string[];
    getTimeForElement(elementId: string): number;
  }

  export class toolkit implements VerovioToolkit {
    setOptions(options: any): void;
    loadData(data: string): boolean;
    renderToSVG(pageNumber?: number): string;
    getElementsAtTime(time: number): string[];
    getTimeForElement(elementId: string): number;
  }
}
