import "./styles/fields-grid.scss";

import StrikeThrough from "./StrikeThrough.svelte";

/**
 * This is how you can import from Anki:
 */
import * as NoteEditor from "anki/NoteEditor";

/**
 * The import above looks like a normal static ESM import, however it is not.
 * This is the magic of esbuild. During compilation, the expression above will be translated into:

 * ```ts
 * const NoteEditor = require("anki/NoteEditor");
 * ```
 *
 * This means that you also dynamically import packages exported from Anki:
 * TODO
 */

/**
 * You can import types from Anki repo directly, if you prefix them with `@anki'.
 * This can be helpful for typing callbacks (see below).
 *
 * Disclaimers:
 * 1. Do no try to import anything but types in this manner! It will not work.
 * 2. Types have less guarantee to stay unchanged and/or be moved to other files.
 *    This will not break you build however, as esbuild does not depend on Typescript
 *    types for a build to succeed.
 */
import type {NoteEditorAPI} from "@anki/editor/NoteEditor.svelte";

NoteEditor.lifecycle.onMount(({toolbar}: NoteEditorAPI): void => {
    toolbar.templateButtons.append({component: StrikeThrough, id: "strikeThroughButton"});
});
