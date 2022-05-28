<script lang="ts">
    import * as NoteEditor from "anki/NoteEditor";

    const {
        LabelButton,
        WithState,
        //@ts-ignore
    } = components;

    const { focusedInput } = NoteEditor.context.get();
    const key = "strikeThrough";

    // $: disabled = $focusedInput?.name !== "rich-text";
</script>

<WithState
    {key}
    update={() => document.queryCommandState(key)}
    let:updateState
>
    <LabelButton
        tooltip="Generate Note"
        on:click={(event) => {
            pycmd("myankiplugin:generate")
            document.execCommand(key);
            updateState(event);
        }}
    >
        Generate
    </LabelButton>
</WithState>
