import { Extension } from '../types.js';

export interface IndentGuides extends Extension {
    /** Collection of all the guide lines. */
    readonly lines: HTMLCollectionOf<HTMLDivElement>;
    /** Indentation for each line. Is -1 for lines with only whitespace. */
    readonly indentLevels: number[];
}
/** Extension adding indent guides to an editor. Does not work with word wrap. */
export declare const indentGuides: () => IndentGuides;
