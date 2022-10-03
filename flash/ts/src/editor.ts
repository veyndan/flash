import Generate from "./Generate.svelte";
import * as NoteEditor from "anki/NoteEditor";
import type {NoteEditorAPI} from "@anki/editor/NoteEditor.svelte";

NoteEditor.lifecycle.onMount(({toolbar}: NoteEditorAPI): void => {
    toolbar.templateButtons.append({component: Generate, id: "generateButton"});
});
