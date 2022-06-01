import Edit from "./Edit.svelte";
import Generate from "./Generate.svelte";
import * as NoteEditor from "anki/NoteEditor";
import type {NoteEditorAPI} from "@anki/editor/NoteEditor.svelte";

// TODO To add an extra button next to sticky it's probably something like https://github.com/ankitects/anki/blob/30bbbaf00b2757a0b10666c0428262a4e2a9129a/ts/editor/NoteCreator.svelte
NoteEditor.lifecycle.onMount(({toolbar}: NoteEditorAPI): void => {
    toolbar.templateButtons.append({component: Generate, id: "generateButton"});
});

// TODO Please just submit a PR to Anki to add something like fields.labelButtons.append(). I don't give a shit about
//  the state of things, as it seems to be hecticly put together by Henrik. Don't bother making sense of this too much.
//  Instead, just try and do the bare minimum of features that fleshes out what I want (i.e.,, be able to contribute
//  back to Wikidata/some other datasource by clicking a link to the page to edit). When I make Fanki I can make this
//  all a lot more streamlined, e.g., by having a button to upload to Wikidata without having to click on the link to
//  the page.

// TODO Actually aren't we just assuming that each field maps to some editable entity somewhere? We're completely
//  ignoring the fact that fields could be the result of combining two thing together, in which case, there is no single
//  link. Perhaps I can just hold off on this until I've thought it through some more?
NoteEditor.lifecycle.onMount(({fields}: NoteEditorAPI): void => {
    fields.
});
