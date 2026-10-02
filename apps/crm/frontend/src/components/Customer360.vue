<!--
  crm-desk patch, see PATCHES.md
  Customer 360: a summary card for a sidebar plus a full "360 view" dialog.
  Data: insurance.api.get_customer_360 (apps/insurance). The same file lives in
  apps/helpdesk/desk/src/components/ and apps/crm/frontend/src/components/: keep them identical.
-->
<template>
  <div v-if="(contact || email) && !unavailable" :class="$attrs.class">
    <!-- Loading: same shape as the card, so the sidebar doesn't jump -->
    <div v-if="c360.loading && !data" class="space-y-3" aria-busy="true" aria-label="Loading customer 360">
      <div class="h-4 w-28 animate-pulse rounded bg-surface-gray-2" />
      <div class="grid grid-cols-2 gap-3 rounded-lg border border-outline-gray-2 p-3">
        <div v-for="i in 4" :key="i" class="space-y-1.5">
          <div class="h-3 w-16 animate-pulse rounded bg-surface-gray-2" />
          <div class="h-4 w-20 animate-pulse rounded bg-surface-gray-2" />
        </div>
      </div>
      <div class="h-7 animate-pulse rounded bg-surface-gray-2" />
    </div>

    <!-- Error: say so and offer a retry instead of an empty space -->
    <div
      v-else-if="c360.error && !data"
      class="flex items-center justify-between gap-2 rounded-md px-2.5 py-2 text-p-sm"
      :class="toneClasses.red"
    >
      <span>Couldn't load customer 360</span>
      <Button size="sm" variant="ghost" @click="c360.reload()">Retry</Button>
    </div>

    <!-- Not an insurance customer: say so quietly, so agents don't go looking -->
    <div
      v-else-if="data && !data.customer"
      class="flex items-center gap-2 text-p-sm text-ink-gray-5"
    >
      <span class="lucide-user-x size-4 shrink-0" aria-hidden="true" />
      Not an insurance customer
    </div>

    <!-- Summary card -->
    <div v-else-if="data?.customer" class="space-y-3">
      <div class="flex items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="flex items-center gap-1.5 text-xs text-ink-gray-5">
            <span class="lucide-shield-check size-3.5" aria-hidden="true" />
            Customer 360
          </div>
          <p class="truncate text-sm font-medium text-ink-gray-9">
            {{ data.customer.customer_name }}
            <span class="font-normal text-ink-gray-5">· {{ data.customer.name }}</span>
          </p>
        </div>
        <Pill :tone="kycTone">KYC {{ data.customer.kyc_status }}</Pill>
      </div>

      <button
        v-for="alert in alerts"
        :key="alert.text"
        class="flex w-full items-start gap-2 rounded-md px-2.5 py-1.5 text-left text-p-sm hover:opacity-80"
        :class="toneClasses[alert.tone]"
        @click="openAt(alert.tab)"
      >
        <span :class="alert.icon" class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        <span>{{ alert.text }}</span>
      </button>

      <dl class="grid grid-cols-2 gap-x-3 gap-y-2.5 rounded-lg border border-outline-gray-2 p-3">
        <div class="col-span-2 min-w-0">
          <dt class="text-xs text-ink-gray-5">Current policy</dt>
          <dd class="flex items-center gap-1.5 text-sm font-medium text-ink-gray-9">
            <span class="truncate">{{ current ? current.product_name : "No policy" }}</span>
            <Pill v-if="current" :tone="statusTone(current.status)">{{ current.status }}</Pill>
          </dd>
          <dd v-if="current" class="mt-0.5 flex items-center gap-1 text-xs text-ink-gray-5">
            <span>{{ current.plan_type }} ·</span>
            <button
              class="inline-flex items-center gap-1 font-mono hover:text-ink-gray-9"
              :aria-label="'Copy policy number ' + current.name"
              @click="copy(current.name)"
            >
              {{ current.name }}<span class="lucide-copy size-3" aria-hidden="true" />
            </button>
          </dd>
        </div>
        <div>
          <dt class="text-xs text-ink-gray-5">Sum insured</dt>
          <dd class="text-sm font-medium text-ink-gray-9">{{ inr(summary.sum_insured) }}</dd>
        </div>
        <div>
          <dt class="text-xs text-ink-gray-5">Next premium</dt>
          <dd class="text-sm font-medium text-ink-gray-9">
            <template v-if="summary.next_due">
              {{ inr(summary.next_due.amount) }}
              <span class="block text-xs font-normal text-ink-gray-5">{{ date(summary.next_due.due_date) }}</span>
            </template>
            <span v-else class="text-ink-gray-5">—</span>
          </dd>
        </div>
        <div>
          <dt class="text-xs text-ink-gray-5">Claims</dt>
          <dd class="text-sm font-medium text-ink-gray-9">
            {{ summary.total_claims }}
            <span class="font-normal text-ink-gray-5">· {{ summary.open_claims }} open</span>
          </dd>
        </div>
        <div>
          <dt class="text-xs text-ink-gray-5">Members</dt>
          <dd class="text-sm font-medium text-ink-gray-9">{{ data.members.length }}</dd>
        </div>
      </dl>

      <Button class="w-full" variant="subtle" @click="openAt('overview')">
        <template #prefix>
          <span class="lucide-maximize-2 size-4" aria-hidden="true" />
        </template>
        Open 360 view
      </Button>
    </div>

    <!-- Full 360 view -->
    <Dialog v-if="data?.customer" v-model:open="open" size="7xl" bare>
      <div class="flex h-[85vh] flex-col overflow-hidden rounded-xl bg-surface-modal">
        <!-- Header -->
        <header class="flex flex-wrap items-start gap-4 border-b border-outline-gray-2 px-6 py-4">
          <div
            class="flex size-12 shrink-0 items-center justify-center rounded-full bg-surface-gray-3 text-lg font-semibold text-ink-gray-8"
            aria-hidden="true"
          >
            {{ initials }}
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-xl font-semibold text-ink-gray-9">{{ data.customer.customer_name || data.contact.full_name }}</h2>
              <Pill v-if="current" :tone="statusTone(current.status)">Policy {{ current.status.toLowerCase() }}</Pill>
              <Pill v-if="summary.open_claims" tone="blue">{{ summary.open_claims }} open claim{{ summary.open_claims > 1 ? "s" : "" }}</Pill>
              <Pill :tone="kycTone">KYC {{ data.customer.kyc_status }}</Pill>
              <Pill tone="gray">{{ data.customer.segment }}</Pill>
            </div>
            <div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-gray-6">
              <a class="hover:text-ink-gray-9" :href="`/app/insurance-customer/${data.customer.name}`" target="_blank">
                {{ data.customer.name }}
              </a>
              <button
                v-if="data.contact.email_id"
                class="inline-flex items-center gap-1 hover:text-ink-gray-9"
                :title="'Copy ' + data.contact.email_id"
                @click="copy(data.contact.email_id)"
              >
                <span class="lucide-mail size-3.5" aria-hidden="true" />{{ data.contact.email_id }}
              </button>
              <button
                v-if="data.contact.mobile_no"
                class="inline-flex items-center gap-1 hover:text-ink-gray-9"
                :title="'Copy ' + data.contact.mobile_no"
                @click="copy(data.contact.mobile_no)"
              >
                <span class="lucide-phone size-3.5" aria-hidden="true" />{{ data.contact.mobile_no }}
              </button>
              <span v-if="data.customer.city" class="inline-flex items-center gap-1">
                <span class="lucide-map-pin size-3.5" aria-hidden="true" />{{ data.customer.city }}, {{ data.customer.state }}
              </span>
              <span v-if="data.customer.customer_since">Customer since {{ year(data.customer.customer_since) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <Button variant="ghost" title="Refresh" aria-label="Refresh" @click="c360.reload()">
              <span class="lucide-refresh-cw size-4" :class="{ 'animate-spin': c360.loading }" aria-hidden="true" />
            </Button>
            <Button variant="ghost" title="Close" aria-label="Close" @click="open = false">
              <span class="lucide-x size-4" aria-hidden="true" />
            </Button>
          </div>
        </header>

        <!-- Tabs -->
        <nav
          class="flex gap-1 overflow-x-auto border-b border-outline-gray-2 px-4"
          role="tablist"
          aria-label="Customer 360 sections"
          @keydown.right.prevent="moveTab(1)"
          @keydown.left.prevent="moveTab(-1)"
        >
          <button
            v-for="t in tabs"
            :key="t.key"
            :ref="(el) => (tabEls[t.key] = el)"
            :id="`c360-tab-${t.key}`"
            role="tab"
            :aria-selected="tab === t.key"
            :aria-controls="`c360-panel`"
            :tabindex="tab === t.key ? 0 : -1"
            class="-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm transition-colors"
            :class="tab === t.key ? 'border-ink-gray-9 font-medium text-ink-gray-9' : 'border-transparent text-ink-gray-5 hover:text-ink-gray-8'"
            @click="tab = t.key"
          >
            <span :class="t.icon" class="size-4" aria-hidden="true" />
            {{ t.label }}
            <span v-if="t.count !== undefined" class="rounded bg-surface-gray-2 px-1.5 text-xs text-ink-gray-6">{{ t.count }}</span>
          </button>
        </nav>

        <!-- Body -->
        <div
          id="c360-panel"
          role="tabpanel"
          :aria-labelledby="`c360-tab-${tab}`"
          class="min-h-0 flex-1 overflow-y-auto bg-surface-gray-1 px-6 py-5"
        >
          <!-- Overview -->
          <div v-if="tab === 'overview'" class="space-y-5">
            <button
              v-for="alert in alerts"
              :key="alert.text"
              class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:opacity-80"
              :class="toneClasses[alert.tone]"
              @click="tab = alert.tab"
            >
              <span :class="alert.icon" class="size-4 shrink-0" aria-hidden="true" />
              <span class="flex-1">{{ alert.text }}</span>
              <span class="lucide-arrow-right size-4 shrink-0" aria-hidden="true" />
            </button>

            <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Active cover" :value="inr(summary.sum_insured)" :hint="`${summary.active_policies} of ${summary.total_policies} policies active`" />
              <Stat label="Premium" :value="current ? inr(current.premium_amount) : '—'" :hint="current ? `per year · paid ${current.payment_frequency.toLowerCase()}` : ''" />
              <Stat label="Next due" :value="summary.next_due ? inr(summary.next_due.amount) : '—'" :hint="summary.next_due ? date(summary.next_due.due_date) : 'Nothing due'" />
              <Stat
                label="Open claims"
                :value="String(summary.open_claims || 0)"
                :hint="summary.open_claims ? `${inr(summary.open_claimed_amount)} under process` : `${inr(summary.total_settled)} settled to date`"
              />
            </div>

            <div class="grid gap-5 lg:grid-cols-5">
              <Panel title="Current policy" class="lg:col-span-3">
                <template v-if="current">
                  <PolicySummary :policy="current" :member-info="memberInfo" />
                </template>
                <Empty v-else text="No policy on record" />
              </Panel>
              <Panel title="Recent activity" class="lg:col-span-2">
                <ul v-if="activity.length" class="divide-y divide-outline-gray-1">
                  <li v-for="a in activity" :key="a.key">
                    <a :href="a.href" target="_blank" class="-mx-2 flex items-start gap-3 rounded px-2 py-2.5 hover:bg-surface-gray-2">
                      <span :class="a.icon" class="mt-0.5 size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
                      <span class="min-w-0 flex-1">
                        <span class="block truncate text-sm text-ink-gray-9">{{ a.title }}</span>
                        <span class="block text-xs text-ink-gray-5">{{ a.meta }}</span>
                      </span>
                      <Pill :tone="statusTone(a.status)">{{ a.status }}</Pill>
                    </a>
                  </li>
                </ul>
                <Empty v-else text="No claims or tickets yet" />
              </Panel>
            </div>
          </div>

          <!-- Policies -->
          <div v-else-if="tab === 'policies'" class="space-y-4">
            <Panel v-for="p in data.policies" :key="p.name" :title="p.product_name">
              <template #actions>
                <Pill :tone="statusTone(p.status)">{{ p.status }}</Pill>
              </template>
              <PolicySummary :policy="p" :member-info="memberInfo" />
            </Panel>
            <Empty v-if="!data.policies.length" text="No policies" />
          </div>

          <!-- Members -->
          <div v-else-if="tab === 'members'">
            <DataTable
              :columns="['Name', 'Health ID (current policy)', 'Relationship', 'Age', 'Gender', 'Pre-existing conditions', 'Claims']"
              :empty="!data.members.length"
            >
              <tr v-for="m in data.members" :key="m.name" class="hover:bg-surface-gray-1">
                <td class="font-medium text-ink-gray-9">
                  <a :href="`/app/insured-member/${m.name}`" target="_blank" class="hover:underline">{{ m.member_name }}</a>
                </td>
                <td class="font-mono text-xs">{{ currentHealthIds[m.name] || "Not covered" }}</td>
                <td>{{ m.relationship }}</td>
                <td>{{ age(m.date_of_birth) }}</td>
                <td>{{ m.gender || "—" }}</td>
                <td>
                  <Pill v-if="m.pre_existing_conditions" tone="amber">{{ m.pre_existing_conditions }}</Pill>
                  <span v-else class="text-ink-gray-4">None</span>
                </td>
                <td>{{ claimsByMember[m.name] || 0 }}</td>
              </tr>
            </DataTable>
          </div>

          <!-- Claims -->
          <div v-else-if="tab === 'claims'" class="space-y-3">
            <Empty v-if="!data.claims.length" text="No claims filed. That's normal: most customers never claim." />
            <div
              v-for="cl in data.claims"
              :key="cl.name"
              class="rounded-lg border border-outline-gray-2 bg-surface-white p-4"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div class="flex items-center gap-2">
                    <a :href="`/app/insurance-claim/${cl.name}`" target="_blank" class="text-base font-medium text-ink-gray-9 hover:underline">{{ cl.diagnosis || "Claim" }}</a>
                    <Pill :tone="statusTone(cl.status)">{{ cl.status }}</Pill>
                  </div>
                  <p class="mt-0.5 text-sm text-ink-gray-5">
                    {{ cl.name }} · {{ cl.member_name }}<template v-if="cl.health_id"> ({{ cl.health_id }})</template> · {{ cl.claim_type }} · {{ cl.hospital_name || cl.hospital || "No hospital" }}
                  </p>
                </div>
                <p class="text-sm text-ink-gray-6">
                  {{ date(cl.admission_date) }} → {{ date(cl.discharge_date) }}
                </p>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-3 border-t border-outline-gray-1 pt-3 text-sm">
                <div><p class="text-xs text-ink-gray-5">Claimed</p><p class="font-medium text-ink-gray-9">{{ inr(cl.claimed_amount) }}</p></div>
                <div><p class="text-xs text-ink-gray-5">Approved</p><p class="font-medium text-ink-gray-9">{{ cl.approved_amount ? inr(cl.approved_amount) : "—" }}</p></div>
                <div>
                  <p class="text-xs text-ink-gray-5">Settled</p>
                  <p class="font-medium text-ink-gray-9">
                    {{ cl.settled_amount ? inr(cl.settled_amount) : "—" }}
                    <span v-if="cl.settled_on" class="font-normal text-ink-gray-5">on {{ date(cl.settled_on) }}</span>
                  </p>
                </div>
              </div>
              <p v-if="cl.rejection_reason" class="mt-3 rounded-md px-3 py-2 text-sm" :class="toneClasses.red">
                Rejected: {{ cl.rejection_reason }}
              </p>
            </div>
          </div>

          <!-- Premiums -->
          <div v-else-if="tab === 'premiums'" class="space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <button
                v-for="p in data.policies"
                :key="p.name"
                class="rounded-full border px-3 py-1 text-sm transition-colors"
                :class="emiPolicy === p.name ? 'border-outline-gray-4 bg-surface-gray-3 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2'"
                :aria-pressed="emiPolicy === p.name"
                @click="emiPolicy = p.name"
              >
                {{ p.product_name }} · {{ year(p.start_date) }}–{{ year(p.end_date) }}
                <Pill class="ms-1" :tone="statusTone(p.status)">{{ p.status }}</Pill>
              </button>
              <span v-if="emisShown.length" class="ms-auto text-sm text-ink-gray-5">
                {{ emisShown.filter((e) => e.status === "Paid").length }} of {{ emisShown.length }} paid
              </span>
            </div>
            <DataTable :columns="['#', 'Due date', 'Amount', 'Status', 'Paid on', 'Mode', 'Reference']" :empty="!emisShown.length">
              <tr v-for="e in emisShown" :key="e.name" class="hover:bg-surface-gray-1">
                <td class="text-ink-gray-5">{{ e.installment_no }}</td>
                <td>{{ date(e.due_date) }}</td>
                <td class="font-medium text-ink-gray-9">{{ inr(e.amount, 2) }}</td>
                <td><Pill :tone="statusTone(e.status)">{{ e.status }}</Pill></td>
                <td>{{ e.paid_on ? date(e.paid_on) : "—" }}</td>
                <td>{{ e.payment_mode || "—" }}</td>
                <td class="font-mono text-xs">{{ e.transaction_ref || "—" }}</td>
              </tr>
            </DataTable>
          </div>

          <!-- Interactions -->
          <div v-else-if="tab === 'interactions'" class="grid gap-5 lg:grid-cols-2">
            <Panel title="Support tickets">
              <ul v-if="data.tickets.length" class="divide-y divide-outline-gray-1">
                <li v-for="t in data.tickets" :key="t.name">
                  <a :href="`/helpdesk/tickets/${t.name}`" target="_blank" class="-mx-2 flex items-center gap-3 rounded px-2 py-2.5 hover:bg-surface-gray-2">
                    <span class="min-w-0 flex-1">
                      <span class="block truncate text-sm text-ink-gray-9">{{ t.subject }}</span>
                      <span class="block text-xs text-ink-gray-5">#{{ t.name }} · {{ date(t.creation) }} · {{ t.priority }}</span>
                    </span>
                    <Pill :tone="statusTone(t.status)">{{ t.status }}</Pill>
                  </a>
                </li>
              </ul>
              <Empty v-else text="No tickets you can see" />
            </Panel>
            <Panel title="Sales deals">
              <ul v-if="data.deals.length" class="divide-y divide-outline-gray-1">
                <li v-for="d in data.deals" :key="d.name">
                  <a :href="`/crm/deals/${d.name}`" target="_blank" class="-mx-2 flex items-center gap-3 rounded px-2 py-2.5 hover:bg-surface-gray-2">
                    <span class="min-w-0 flex-1">
                      <span class="block truncate text-sm text-ink-gray-9">{{ d.organization || d.name }}</span>
                      <span class="block text-xs text-ink-gray-5">{{ d.name }} · updated {{ date(d.modified) }}</span>
                    </span>
                    <span class="text-sm font-medium text-ink-gray-9">{{ d.deal_value ? inr(d.deal_value) : "" }}</span>
                    <Pill tone="blue">{{ d.status }}</Pill>
                  </a>
                </li>
              </ul>
              <Empty v-else text="No deals you can see" />
            </Panel>
          </div>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, createResource, Dialog, toast } from "frappe-ui"
import { computed, defineComponent, h, ref, watch } from "vue"

defineOptions({ inheritAttrs: false })

const props = defineProps({
  contact: { type: String, default: "" },
  email: { type: String, default: "" },
})

const open = ref(false)
const tab = ref("overview")
const tabEls = {}
function openAt(key) {
  tab.value = key || "overview"
  open.value = true
}
function moveTab(step) {
  const keys = tabs.value.map((t) => t.key)
  tab.value = keys[(keys.indexOf(tab.value) + step + keys.length) % keys.length]
  tabEls[tab.value]?.focus()
}
const emiPolicy = ref("")

// On a site where the insurance app isn't installed yet, hide the card entirely instead of
// erroring on every ticket/deal. Defining onError also keeps the app's global error toast quiet.
const unavailable = ref(false)
const c360 = createResource({
  url: "insurance.api.get_customer_360",
  makeParams: () => ({ contact: props.contact || undefined, email: props.email || undefined }),
  onError(error) {
    if (/not installed/i.test(JSON.stringify(error?.messages || error?.message || ""))) unavailable.value = true
  },
})
watch(
  () => [props.contact, props.email],
  ([contact, email]) => (contact || email) && c360.reload(),
  { immediate: true },
)

const data = computed(() => c360.data)
const summary = computed(() => data.value?.summary || {})
const current = computed(() => summary.value.current_policy)
watch(data, (d) => (emiPolicy.value = d?.policies?.[0]?.name || ""))

const initials = computed(() =>
  (data.value?.customer?.customer_name || data.value?.contact?.full_name || "?")
    .split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase(),
)
const kycTone = computed(() => ({ Verified: "green", Pending: "amber", Rejected: "red" })[data.value?.customer?.kyc_status] || "gray")
const memberInfo = computed(() => Object.fromEntries((data.value?.members || []).map((m) => [m.name, m])))
const currentHealthIds = computed(() => Object.fromEntries((current.value?.members || []).map((m) => [m.member, m.health_id])))
const claimsByMember = computed(() =>
  (data.value?.claims || []).reduce((acc, c) => ((acc[c.member] = (acc[c.member] || 0) + 1), acc), {}),
)
const emisShown = computed(() => (data.value?.emis || []).filter((e) => e.policy === emiPolicy.value).sort((a, b) => a.installment_no - b.installment_no))

const alerts = computed(() => {
  const d = data.value
  if (!d?.customer) return []
  const out = []
  const s = summary.value
  if (s.overdue_count) out.push({ tone: "red", icon: "lucide-alert-circle", tab: "premiums", text: `${s.overdue_count} premium${s.overdue_count > 1 ? "s" : ""} overdue · ${inr(s.overdue_amount)}` })
  for (const p of d.policies.filter((p) => ["Grace Period", "Lapsed"].includes(p.status)))
    out.push({ tone: p.status === "Lapsed" ? "red" : "amber", icon: "lucide-clock", tab: "premiums", text: `${p.product_name} is ${p.status === "Lapsed" ? "lapsed" : "in grace period"}` })
  for (const c of d.claims.filter((c) => c.status === "Query Raised"))
    out.push({ tone: "amber", icon: "lucide-message-circle-question", tab: "claims", text: `Claim ${c.name} has a query pending (${c.member_name})` })
  if (d.customer.kyc_status !== "Verified") out.push({ tone: "amber", icon: "lucide-id-card", tab: "overview", text: `KYC ${d.customer.kyc_status.toLowerCase()}` })
  return out
})

const activity = computed(() => {
  const d = data.value
  if (!d) return []
  const claims = d.claims.map((c) => ({
    key: "c" + c.name, icon: "lucide-hospital", title: `${c.diagnosis} · ${c.member_name}`,
    meta: `Claim · ${date(c.admission_date)} · ${inr(c.claimed_amount)}`, status: c.status, when: c.admission_date,
    href: `/app/insurance-claim/${c.name}`,
  }))
  const tickets = d.tickets.map((t) => ({
    key: "t" + t.name, icon: "lucide-ticket", title: t.subject, meta: `Ticket #${t.name} · ${date(t.creation)}`,
    status: t.status, when: t.creation, href: `/helpdesk/tickets/${t.name}`,
  }))
  return [...claims, ...tickets].sort((a, b) => String(b.when).localeCompare(String(a.when))).slice(0, 6)
})

const tabs = computed(() => [
  { key: "overview", label: "Overview", icon: "lucide-layout-dashboard" },
  { key: "policies", label: "Policies", icon: "lucide-file-text", count: data.value?.policies?.length },
  { key: "members", label: "Members", icon: "lucide-users", count: data.value?.members?.length },
  { key: "claims", label: "Claims", icon: "lucide-hospital", count: data.value?.claims?.length },
  { key: "premiums", label: "Premiums", icon: "lucide-wallet", count: data.value?.emis?.length },
  { key: "interactions", label: "Interactions", icon: "lucide-messages-square", count: (data.value?.tickets?.length || 0) + (data.value?.deals?.length || 0) },
])

// ---------- formatting
function inr(v, digits = 0) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(v || 0)
}
function date(v) {
  return v ? new Date(String(v).replace(" ", "T")).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—"
}
function year(v) {
  return v ? String(v).slice(0, 4) : ""
}
function age(dob) {
  if (!dob) return "—"
  const d = new Date(dob), n = new Date()
  return n.getFullYear() - d.getFullYear() - (n < new Date(n.getFullYear(), d.getMonth(), d.getDate()) ? 1 : 0)
}
function copy(text) {
  navigator.clipboard?.writeText(text)
  toast.success("Copied")
}

const toneClasses = {
  // Same pairs as frappe-ui's subtle Badge, so contrast matches the rest of the app.
  green: "bg-surface-green-2 text-ink-green-8",
  red: "bg-surface-red-2 text-ink-red-8",
  amber: "bg-surface-amber-2 text-ink-amber-8",
  blue: "bg-surface-blue-2 text-ink-blue-8",
  gray: "bg-surface-gray-2 text-ink-gray-7",
}
function statusTone(s) {
  if (["Active", "Paid", "Settled", "Approved", "Verified", "Resolved", "Closed", "Won"].includes(s)) return "green"
  if (["Overdue", "Failed", "Rejected", "Lapsed", "Lost"].includes(s)) return "red"
  if (["Grace Period", "Query Raised", "Pending", "Paused"].includes(s)) return "amber"
  if (["Due", "Intimated", "Under Review", "Open", "Replied"].includes(s)) return "blue"
  return "gray"
}

// ---------- small local building blocks (kept in this file so the copy in each app stays self-contained)
const Pill = defineComponent({
  props: { tone: { type: String, default: "gray" } },
  setup: (p, { slots }) => () =>
    h("span", { class: ["inline-flex shrink-0 items-center whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium", toneClasses[p.tone] || toneClasses.gray] }, slots.default?.()),
})
const Stat = defineComponent({
  props: { label: String, value: String, hint: String },
  setup: (p) => () =>
    h("div", { class: "rounded-lg border border-outline-gray-2 bg-surface-white p-4" }, [
      h("p", { class: "text-xs text-ink-gray-5" }, p.label),
      h("p", { class: "mt-1 text-xl font-semibold text-ink-gray-9" }, p.value),
      p.hint && h("p", { class: "mt-0.5 text-xs text-ink-gray-5" }, p.hint),
    ]),
})
const Panel = defineComponent({
  props: { title: String },
  setup: (p, { slots }) => () =>
    h("section", { class: "rounded-lg border border-outline-gray-2 bg-surface-white" }, [
      h("div", { class: "flex items-center justify-between gap-2 border-b border-outline-gray-1 px-4 py-2.5" }, [
        h("h3", { class: "text-sm font-medium text-ink-gray-9" }, p.title),
        slots.actions?.(),
      ]),
      h("div", { class: "p-4" }, slots.default?.()),
    ]),
})
const Empty = defineComponent({
  props: { text: String },
  setup: (p) => () => h("p", { class: "py-6 text-center text-sm text-ink-gray-5" }, p.text),
})
const DataTable = defineComponent({
  props: { columns: Array, empty: Boolean },
  setup: (p, { slots }) => () =>
    p.empty
      ? h(Empty, { text: "Nothing here yet" })
      : h("div", { class: "overflow-x-auto rounded-lg border border-outline-gray-2 bg-surface-white" }, [
          h("table", { class: "w-full text-left text-sm text-ink-gray-7 [&_td]:px-4 [&_td]:py-2.5 [&_th]:px-4 [&_th]:py-2" }, [
            h("thead", { class: "border-b border-outline-gray-2 bg-surface-gray-1 text-xs text-ink-gray-5" }, [
              h("tr", p.columns.map((c) => h("th", { class: "font-medium" }, c))),
            ]),
            h("tbody", { class: "divide-y divide-outline-gray-1" }, slots.default?.()),
          ]),
        ]),
})
const PolicySummary = defineComponent({
  props: { policy: Object, memberInfo: Object },
  setup: (p) => () => {
    const pol = p.policy
    const total = new Date(pol.end_date) - new Date(pol.start_date)
    const done = Math.min(100, Math.max(0, ((Date.now() - new Date(pol.start_date)) / total) * 100))
    const field = (label, value) => h("div", [h("p", { class: "text-xs text-ink-gray-5" }, label), h("p", { class: "text-sm font-medium text-ink-gray-9" }, value)])
    return h("div", { class: "space-y-4" }, [
      h("div", { class: "grid grid-cols-2 gap-3 sm:grid-cols-4" }, [
        field("Policy number", pol.name),
        field("Plan", pol.plan_type),
        field("Sum insured", inr(pol.sum_insured)),
        field("Premium", `${inr(pol.premium_amount)} · ${pol.payment_frequency}`),
      ]),
      h("div", [
        h("div", { class: "mb-1 flex justify-between text-xs text-ink-gray-5" }, [h("span", date(pol.start_date)), h("span", date(pol.end_date))]),
        h("div", { class: "h-1.5 overflow-hidden rounded-full bg-surface-gray-3", role: "progressbar", "aria-label": "Policy year elapsed", "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": Math.round(done) }, [h("div", { class: "h-full rounded-full bg-surface-gray-7", style: { width: done + "%" } })]),
      ]),
      pol.members?.length &&
        h("div", [
          h("p", { class: "mb-1.5 text-xs text-ink-gray-5" }, "Members covered"),
          h("div", { class: "flex flex-wrap gap-1.5" }, pol.members.map((m) => {
            const info = p.memberInfo?.[m.member] || {}
            return h("span", { class: "inline-flex items-center gap-1 rounded-full border border-outline-gray-2 px-2.5 py-0.5 text-xs text-ink-gray-7" }, [
              `${m.member_name} · ${m.relationship}${info.date_of_birth ? " · " + age(info.date_of_birth) + "y" : ""}`,
              m.health_id && h("span", { class: "font-mono text-ink-gray-5" }, m.health_id),
              info.pre_existing_conditions && h("span", { class: ["rounded px-1", toneClasses.amber], title: "Pre-existing conditions" }, info.pre_existing_conditions),
            ])
          })),
        ]),
      pol.documents?.length &&
        h("div", [
          h("p", { class: "mb-1.5 text-xs text-ink-gray-5" }, "Documents"),
          h("div", { class: "flex flex-wrap gap-2" }, pol.documents.map((d) =>
            h("a", { href: d.file, target: "_blank", class: "inline-flex items-center gap-1.5 rounded-md border border-outline-gray-2 px-2.5 py-1 text-xs text-ink-gray-7 hover:bg-surface-gray-2" }, [
              h("span", { class: "lucide-file-text size-3.5", "aria-hidden": "true" }),
              d.document_type,
            ]),
          )),
        ]),
      h("a", { href: `/app/insurance-policy/${pol.name}`, target: "_blank", class: "inline-block text-xs text-ink-gray-5 hover:text-ink-gray-9 hover:underline" }, "Open policy record ↗"),
    ])
  },
})
</script>
