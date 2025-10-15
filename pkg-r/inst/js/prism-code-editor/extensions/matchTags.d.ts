import { PrismEditor, BasicExtension } from '../index.js';
import { Token } from '../prism/index.js';

/**
 * Tuple containing in the following order:
 * - The tag's `Token`
 * - Its starting position
 * - Its ending position
 * - Its tag name
 * - Whether it's a closing tag
 * - Whether it's not self-closing
 */
export type Tag = [Token, number, number, string, boolean, boolean];
export interface TagMatcher {
    /**
     * Array of tuples containing in the following order:
     * - The tag's `Token`
     * - Its starting position
     * - Its ending position
     * - Its tag name
     * - Whether it's a closing tag
     * - Whether it's not self-closing
     *
     * The tags are sorted by their ending position
     */
    readonly tags: Tag[];
    /** Array mapping the index of a tag to the index of its matching tag. */
    readonly pairs: (number | undefined)[];
}
/**
 * Function that adds tag matching to the editor.
 * @returns An object containing all tags and pairs.
 */
export declare const createTagMatcher: (editor: PrismEditor) => TagMatcher;
/**
 * Extension that adds an `active-tagname` class to matching HTML/XML/JSX tags when the
 * cursor is on either tag. If the editor doesn't have a {@link TagMatcher}, one is
 * created. Use the CSS selector `.active-tagname` to style the elements. Obviously don't
 * add this if the languages used don't have tags.
 */
export declare const matchTags: () => BasicExtension;
/**
 * Extension that highlights `<` and `>` punctuation in XML tags.
 * @param className Class added to the active punctuation you can use to style them with CSS.
 * @param alwaysHighlight If true, the punctuation will always be highlighted when the cursor
 * is inside a tag. If not it will only be highlighted when the cursor is on the punctuation.
 */
export declare const highlightTagPunctuation: (className: string, alwaysHighlight?: boolean) => BasicExtension;
