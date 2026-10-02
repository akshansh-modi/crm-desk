<template>
  <img
    v-if="config.brandLogo"
    :src="config.brandLogo"
    alt="Brand Logo"
    class="h-8 w-auto shrink-0 object-contain"
  />
  <HDLogo v-else class="h-8 w-8 shrink-0 rounded" />
</template>

<script setup lang="ts">
// crm-desk patch, see PATCHES.md: the logo was "h-8 w-8 object-cover", which cropped wide logos
// to a square. Now full height, natural width, never cropped; UserMenu caps the width.
import HDLogo from "@/assets/logos/HDLogo.vue";

import { useConfigStore } from "@/stores/config";
const config = useConfigStore();
</script>

<style scoped></style>
