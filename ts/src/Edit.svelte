<!--<script lang="ts">-->
<!--    const {-->
<!--        LabelButton,-->
<!--        WithState,-->
<!--        //@ts-ignore-->
<!--    } = components;-->

<!--    const key = "edit";-->
<!--</script>-->

<!--<WithState-->
<!--    {key}-->
<!--    update={() => document.queryCommandState(key)}-->
<!--    let:updateState-->
<!--&gt;-->
<!--    <LabelButton-->
<!--        tooltip="Generate Note"-->
<!--        on:click={(event) => {-->
<!--            pycmd("myankiplugin:edit")-->
<!--            document.execCommand(key);-->
<!--            updateState(event);-->
<!--        }}-->
<!--    >-->
<!--        Generate-->
<!--    </LabelButton>-->
<!--</WithState>-->

<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import { bridgeCommand } from "../lib/bridgecommand";
    import { registerShortcut } from "../lib/shortcuts";
    import type { NoteEditorAPI } from "./NoteEditor.svelte";
    import NoteEditor from "./NoteEditor.svelte";
    import StickyBadge from "./StickyBadge.svelte";
    const api: Partial<NoteEditorAPI> = {};
    let noteEditor: NoteEditor;
    export let uiResolve: (api: NoteEditorAPI) => void;
    $: if (noteEditor) {
        uiResolve(api as NoteEditorAPI);
    }
    let stickies: boolean[] = [];
    function setSticky(stckies: boolean[]): void {
        stickies = stckies;
    }
    function toggleStickyAll(): void {
        bridgeCommand("toggleStickyAll", (values: boolean[]) => (stickies = values));
    }
    let deregisterSticky: () => void;
    export function activateStickyShortcuts() {
        deregisterSticky = registerShortcut(toggleStickyAll, "Shift+F9");
    }
    onMount(() => {
        Object.assign(globalThis, {
            setSticky,
        });
    });
    onDestroy(() => deregisterSticky);
</script>

<NoteEditor bind:this={noteEditor} {api}>
    <svelte:fragment slot="field-state" let:index>
        <StickyBadge active={stickies[index]} {index} />
    </svelte:fragment>
</NoteEditor>
