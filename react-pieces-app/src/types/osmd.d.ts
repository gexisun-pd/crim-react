// Type definitions for OpenSheetMusicDisplay
declare module 'opensheetmusicdisplay' {
  export class OpenSheetMusicDisplay {
    constructor(container: HTMLElement, options?: OSMDOptions);
    
    // Properties
    Sheet: MusicSheet | null;
    GraphicSheet: GraphicMusicSheet | null;
    
    // Methods
    load(musicXML: string): Promise<void>;
    render(): Promise<void>;
    clear(): void;
    
    // Static methods
    static createFromMusicXML(musicXML: string, container: HTMLElement): Promise<OpenSheetMusicDisplay>;
  }

  export interface OSMDOptions {
    autoResize?: boolean;
    backend?: 'svg' | 'canvas';
    drawTitle?: boolean;
    drawSubtitle?: boolean;
    drawComposer?: boolean;
    drawLyricist?: boolean;
    drawCredits?: boolean;
    drawPartNames?: boolean;
    drawPartAbbreviations?: boolean;
    drawMeasureNumbers?: boolean;
    drawMeasureNumbersOnlyAtSystemStart?: boolean;
    measureNumberInterval?: number;
    drawTimeSignatures?: boolean;
    drawKeySignatures?: boolean;
    coloringMode?: number;
    colorStemsLikeNoteheads?: boolean;
    defaultColorNotehead?: string;
    defaultColorStem?: string;
    defaultFontFamily?: string;
    defaultFontSize?: number;
    pageFormat?: string;
    pageBackgroundColor?: string;
    renderSingleHorizontalStaffline?: boolean;
    setWantedStemDirectionByXml?: boolean;
    tupletsBracketed?: boolean;
    tupletsRatioed?: boolean;
    followCursor?: boolean;
  }

  export interface MusicSheet {
    Title?: string;
    Composer?: string;
    Instruments?: Instrument[];
    SourceMeasures: SourceMeasure[];
  }

  export interface Instrument {
    Name?: string;
    Voices?: Voice[];
  }

  export interface Voice {
    // Voice properties
  }

  export interface SourceMeasure {
    MeasureNumber: number;
    ActiveTimeSignature?: TimeSignature;
    ActiveKeyInstruction?: KeyInstruction;
  }

  export interface TimeSignature {
    ToString(): string;
  }

  export interface KeyInstruction {
    Key: string;
  }

  export interface GraphicMusicSheet {
    MusicPages?: GraphicMusicPage[];
  }

  export interface GraphicMusicPage {
    MusicSystems: MusicSystem[];
  }

  export interface MusicSystem {
    StaffLines: StaffLine[];
  }

  export interface StaffLine {
    Measures: GraphicMeasure[];
  }

  export interface GraphicMeasure {
    MeasureNumber: number;
    staffEntries: StaffEntry[];
  }

  export interface StaffEntry {
    VoiceEntries: VoiceEntry[];
  }

  export interface VoiceEntry {
    Timestamp: Timestamp;
    notes?: Note[];
  }

  export interface Timestamp {
    RealValue: number;
  }

  export interface Note {
    Pitch?: Pitch;
    GraphicalNoteReference?: GraphicalNote;
  }

  export interface Pitch {
    ToString(): string;
  }

  export interface GraphicalNote {
    SVGElement?: Element;
  }
}
