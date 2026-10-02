<!--
  crm-desk patch, see PATCHES.md
  Attach picker for the reply composer: lists the ticket customer's policy documents
  (insurance.api.get_ticket_documents) next to "Upload from computer".
  `available` is false when the insurance app isn't installed, the sender isn't a
  customer, or they have no documents; the paperclip then keeps its old behaviour.
-->
<template>
  <Dialog v-model:open="open" size="xl" bare>
    <div class="flex max-h-[80vh] flex-col rounded-xl bg-surface-modal">
      <header class="flex items-start justify-between gap-3 border-b border-outline-gray-2 px-5 py-4">
        <div>
          <h2 class="text-lg font-semibold text-ink-gray-9">Attach files</h2>
          <p class="text-sm text-ink-gray-5">Customer documents, or upload from your computer</p>
        </div>
        <Button variant="ghost" aria-label="Close" @click="open = false">
          <span class="lucide-x size-4" aria-hidden="true" />
        </Button>
      </header>

      <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
        <!-- Health documents going to someone who isn't on the customer's contact -->
        <div
          v-if="outsiders.length"
          class="flex items-start gap-2 rounded-md bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
          role="alert"
        >
          <span class="lucide-triangle-alert mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>
            {{ outsiders.join(", ") }} {{ outsiders.length > 1 ? "aren't" : "isn't" }} one of the customer's
            registered emails. Policy documents contain health details: check before sending.
          </span>
        </div>

        <section v-for="group in groups" :key="group.policy">
          <div class="mb-1.5 flex items-center gap-2">
            <h3 class="text-sm font-medium text-ink-gray-9">{{ group.product_name }}</h3>
            <span class="text-xs text-ink-gray-5">{{ group.policy }} · {{ year(group.start_date) }}–{{ year(group.end_date) }}</span>
            <span
              class="rounded px-1.5 py-0.5 text-xs font-medium"
              :class="group.policy_status === 'Active' ? 'bg-surface-green-2 text-ink-green-8' : 'bg-surface-gray-2 text-ink-gray-7'"
            >
              {{ group.policy_status }}
            </span>
          </div>
          <ul class="divide-y divide-outline-gray-1 rounded-lg border border-outline-gray-2">
            <li v-for="d in group.documents" :key="d.name">
              <label
                class="flex cursor-pointer items-center gap-3 px-3 py-2.5 hover:bg-surface-gray-1"
                :class="{ 'cursor-default opacity-60': isAttached(d) }"
              >
                <input
                  v-model="selected"
                  type="checkbox"
                  class="rounded border-outline-gray-3"
                  :value="d.name"
                  :disabled="isAttached(d)"
                />
                <span class="lucide-file-text size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
                <span class="min-w-0 flex-1">
                  <span class="block text-sm text-ink-gray-9">{{ d.document_type }}</span>
                  <span class="block truncate text-xs text-ink-gray-5">{{ d.file_name }}</span>
                </span>
                <span v-if="isAttached(d)" class="text-xs text-ink-gray-5">Attached</span>
                <a
                  v-else
                  :href="d.file_url"
                  target="_blank"
                  class="text-xs text-ink-gray-5 hover:text-ink-gray-9 hover:underline"
                  @click.stop
                >
                  Preview
                </a>
              </label>
            </li>
          </ul>
        </section>
      </div>

      <footer class="flex items-center justify-between gap-2 border-t border-outline-gray-2 px-5 py-3">
        <Button variant="subtle" @click="uploadFromComputer">
          <template #prefix><span class="lucide-upload size-4" aria-hidden="true" /></template>
          Upload from computer
        </Button>
        <Button variant="solid" :disabled="!selected.length" :loading="attaching" @click="attachSelected">
          {{ selected.length ? `Attach ${selected.length} document${selected.length > 1 ? "s" : ""}` : "Attach" }}
        </Button>
      </footer>
    </div>
  </Dialog>
</template>

<script setup>
import { Button, call, createResource, Dialog, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

const props = defineProps({
  ticketId: { type: String, required: true },
  recipients: { type: Array, default: () => [] },
  attachedNames: { type: Array, default: () => [] },
})
const emit = defineEmits(["attach", "upload"])
const open = defineModel("open", { type: Boolean, default: false })

const selected = ref([])
const attaching = ref(false)

const docs = createResource({
  url: "insurance.api.get_ticket_documents",
  makeParams: () => ({ ticket: props.ticketId }),
  auto: true,
  // No insurance app / not a customer: stay unavailable, and keep the global error toast quiet.
  onError() {},
})
watch(() => props.ticketId, () => docs.reload())
watch(open, (v) => v && (selected.value = []))

const available = computed(() => Boolean(docs.data?.documents?.length))
defineExpose({ available })

const groups = computed(() => {
  const out = []
  for (const d of docs.data?.documents || []) {
    let g = out.find((x) => x.policy === d.policy)
    if (!g) out.push((g = { ...d, documents: [] }))
    g.documents.push(d)
  }
  return out
})

const address = (s) => (String(s).match(/<([^>]+)>/)?.[1] || String(s)).trim().toLowerCase()
const outsiders = computed(() => {
  const own = new Set((docs.data?.emails || []).map(address))
  return [...new Set(props.recipients.filter(Boolean).map(address))].filter((e) => !own.has(e))
})
const isAttached = (d) => props.attachedNames.includes(d.file_name)

async function attachSelected() {
  attaching.value = true
  try {
    for (const document of selected.value) {
      emit("attach", await call("insurance.api.attach_ticket_document", { ticket: props.ticketId, document }))
    }
    open.value = false
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || "Couldn't attach the document")
  } finally {
    attaching.value = false
  }
}

function uploadFromComputer() {
  open.value = false
  emit("upload")
}

function year(v) {
  return v ? String(v).slice(0, 4) : ""
}
</script>
