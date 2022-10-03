<script lang="ts">
    const {
        LabelButton,
        WithState,
        //@ts-ignore
    } = components;

    const key = "generate";
</script>

<WithState
    {key}
    update={() => document.queryCommandState(key)}
    let:updateState
>
    <LabelButton
        tooltip="Generate Note"
        on:click={(event) => {
            pycmd("flash:generate")
            document.execCommand(key);
            updateState(event);
        }}
    >
        Generate
    </LabelButton>
</WithState>
