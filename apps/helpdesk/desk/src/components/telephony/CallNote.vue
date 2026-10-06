<!--
  crm-desk patch, see PATCHES.md
  Notes for a call placed from a ticket. Opens when the call starts and stays open after
  it ends (the call popup closes on hang-up, and agents often write notes afterwards).
  Saving adds an internal HD Ticket Comment, never emailed to the customer.
-->
<template>
  <div
    class="fixed bottom-4 start-4 z-20 w-80 rounded-lg border border-outline-gray-2 bg-surface-modal shadow-xl"
    role="dialog"
    :aria-label="`Call note for ticket ${target.ticket}`"
  >
    <div class="flex items-start justify-between gap-2 border-b border-outline-gray-1 px-3 py-2.5">
      <div class="min-w-0">
        <p class="flex items-center gap-1.5 text-sm font-medium text-ink-gray-9">
          <span class="lucide-notebook-pen size-4" aria-hidden="true" />
          Call note · #{{ target.ticket }}
        </p>
        <p class="truncate text-xs text-ink-gray-5">
          {{ target.number }} · started {{ startedAt }}
        </p>
      </div>
      <Button variant="ghost" size="sm" aria-label="Discard note" @click="discard">
        <span class="lucide-x size-4" aria-hidden="true" />
      </Button>
    </div>
    <div class="p-3">
      <textarea
        ref="textarea"
        v-model="text"
        rows="5"
        class="w-full resize-none rounded-md border-outline-gray-2 bg-surface-gray-1 text-sm text-ink-gray-8 placeholder:text-ink-gray-4 focus:border-outline-gray-4 focus:ring-0"
        placeholder="What did the customer ask? What did you agree? Next steps…"
        @keydown.meta.enter.prevent="save"
        @keydown.ctrl.enter.prevent="save"
      />
      <div v-if="confirmDiscard" class="mt-2 flex items-center justify-between gap-2 rounded-md bg-surface-amber-2 px-2 py-1.5 text-xs text-ink-amber-8">
        <span>Discard this note?</span>
        <span class="flex gap-1">
          <Button size="sm" variant="ghost" @click="confirmDiscard = false">Keep</Button>
          <Button size="sm" theme="red" variant="subtle" @click="emit('close')">Discard</Button>
        </span>
      </div>
      <div v-else class="mt-2 flex items-center justify-between gap-2">
        <span class="text-xs text-ink-gray-4">Internal · not sent to the customer</span>
        <Button variant="solid" size="sm" :loading="saving" :disabled="!text.trim()" @click="save">
          Save note
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, call, toast } from "frappe-ui"
import { computed, nextTick, onMounted, ref } from "vue"

// target: { ticket, number, medium, startedAt (ms) }
const props = defineProps({ target: { type: Object, required: true } })
const emit = defineEmits(["close"])

const text = ref("")
const saving = ref(false)
const confirmDiscard = ref(false)
const textarea = ref()

const startedAt = computed(() =>
  new Date(props.target.startedAt).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
)

onMounted(() => nextTick(() => textarea.value?.focus()))

// The comment is rendered as HTML for other agents: escape what the agent typed.
const escapeHtml = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;")

async function save() {
  if (!text.value.trim() || saving.value) return
  saving.value = true
  const when = new Date(props.target.startedAt).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })
  const header = `<p><strong>📞 Call note</strong> · outgoing ${escapeHtml(props.target.medium || "")} call to ${escapeHtml(props.target.number || "")} · ${when}</p>`
  const body = escapeHtml(text.value.trim()).split(/\n{2,}/).map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("")
  try {
    await call("run_doc_method", {
      dt: "HD Ticket",
      dn: props.target.ticket,
      method: "new_comment",
      args: { content: header + body, attachments: [] },
    })
    toast.success(`Note added to ticket #${props.target.ticket}`)
    emit("close")
  } catch (e) {
    toast.error(e?.messages?.[0] || "Couldn't save the note. Your text is still here.")
  } finally {
    saving.value = false
  }
}

function discard() {
  if (text.value.trim()) confirmDiscard.value = true
  else emit("close")
}
</script>
