import { BasicExtension } from '../index.js';

declare let ignoreTab: boolean;
/**
 * Sets whether editors should ignore tab or use it for indentation.
 * Users can always toggle this using Ctrl+M / Ctrl+Shift+M (Mac).
 */
declare const setIgnoreTab: (newState: boolean) => boolean;
/**
 * Extension that will add automatic indentation, closing of brackets,
 * quotes and tags along with the following commands:
 *
 * - Alt+ArrowUp/Down: Move line up/down
 * - Ctrl+ArrowUp/Down (Not on MacOS): Scroll up/down 1 line
 * - Shift+Alt+ArrowUp/Down: Copy line up/down
 * - Ctrl+Enter (Cmd+Enter on MacOS): Insert blank line
 * - Ctrl+[ (Cmd+[ on MacOS): Outdent line
 * - Ctrl+] (Cmd+] on MacOS): Indent line
 * - Shift+Ctrl+K (Shift+Cmd + K on MacOS): Delete line
 * - Ctrl+/ (Cmd+/ on MacOS): Toggle comment
 * - Shift+Alt+A: Toggle block comment
 * - Ctrl+M (Ctrl+Shift+M on MacOS): Toggle Tab capturing
 *
 * The shortcuts for the commands are not easily customizable. If you want to customize
 * them, you can copy the {@link https://github.com/FIameCaster/prism-code-editor/blob/main/package/src/extensions/commands.ts|source}
 * and change the conditions.
 *
 * @param selfClosePairs Pairs of self-closing brackets and quotes.
 * Must be an array of strings with 2 characters each.
 * Defaults to `['""', "''", '``', '()', '[]', '{}']`.
 * @param selfCloseRegex Regex controlling whether or not a bracket/quote should
 * automatically close based on the character before and after the cursor.
 * Defaults to ``/([^$\w'"`]["'`]|.[[({])[.,:;\])}>\s]|.[[({]`/s``.
 */
declare const defaultCommands: (selfClosePairs?: string[], selfCloseRegex?: RegExp) => BasicExtension;
export interface EditHistory extends BasicExtension {
    /** Clears the history stack. Probably necessary after changing the value of the editor. */
    clear(): void;
    /**
     * Sets the active entry relative to the current entry.
     *
     * @param offset The position you want to move to relative to the current entry.
     *
     * `EditHistory.go(-1)` would be equivalent to an undo while `EditHistory.go(1)` would
     * be equivalent to a redo.
     *
     * If there's no entry at the specified offset, the call does nothing.
     */
    go(offset: number): void;
    /**
     * Returns whether or not there exists a history entry at the specified offset relative
     * to the current entry.
     *
     * This method can be used to determine whether a call to {@link EditHistory.go} with the
     * same offset will succeed or do nothing.
     */
    has(offset: number): boolean;
}
/**
 * History extension that overrides the undo/redo behavior of the browser.
 *
 * Without this extension, the browser's native undo/redo is used, which can be sufficient
 * in some cases.
 *
 * It should be noted that the history stack is not automatically cleared when the editors
 * value is changed programmatically using `editor.setOptions` Instead you can clear the
 * stack any time using {@link EditHistory.clear}.
 *
 * Once added to an editor, this extension can be accessed from `editor.extensions.history`.
 *
 * If you want to create a new editor with different extensions while keeping the undo/redo
 * history of an old editor, you can! Just add the old editor's history extension instance
 * to the new editor. Keep in mind that this will fully break the undo/redo behavior of the
 * old editor.
 *
 * @param historyLimit The maximum size of the history stack. Defaults to 999.
 */
declare const editHistory: (historyLimit?: number) => EditHistory;
export { defaultCommands, setIgnoreTab, ignoreTab, editHistory };
