import { BasicExtension } from '../index.js';

/** Postion of the cursor relative to the editors overlays. */
export type CursorPosition = {
    top: number;
    bottom: number;
    left: number;
    right: number;
    height: number;
};
export interface Cursor extends BasicExtension {
    /** Gets the cursor position relative to the editor overlays. */
    getPosition(): CursorPosition;
    /** Scrolls the cursor into view. */
    scrollIntoView(): void;
    /** The empty span element representing the cursor. */
    element: HTMLSpanElement;
}
/**
 * Extension which can be used to calculate the position of the cursor and scroll it into view.
 * This is used by the {@link defaultCommands} extension to keep the cursor in view while typing.
 *
 * The extension can also be accessed from `editor.extensions.cursor` when added.
 */
export declare const cursorPosition: () => Cursor;
