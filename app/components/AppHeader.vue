<script setup lang="ts">
defineEmits<{
  (e: 'open-settings'): void
}>()
</script>

<template>
  <header class="flex items-center justify-between px-5 py-3.5 border-b border-[#202734]/15 bg-[#FAF9F6] shrink-0">
    <div class="flex items-center gap-2.5">
      <div class="w-6 h-6 bg-[#202734] rounded-[4px] flex items-center justify-center shrink-0">
        <span class="text-[#B7D894] font-bold text-xs leading-none">G</span>
      </div>
      <div class="flex items-baseline gap-2">
        <h1 class="text-lg font-bold tracking-[-0.01em] text-[#202734] leading-none">
          Ganto
        </h1>
        <span class="text-[11px] font-medium text-[#202734]/70">
          PDF → DOCX
        </span>
      </div>
      <span class="ml-1 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-[#B7D894] text-[#202734] border border-[#202734]/20 rounded-[4px]">
        Offline
      </span>
    </div>

    <button
      type="button"
      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/25 rounded-[4px] hover:bg-[#F1F3F5] cursor-pointer transition-colors"
      @click="$emit('open-settings')"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="13"
        height="13"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="square"
        stroke-linejoin="miter"
        aria-hidden="true"
      >
        <line x1="4" y1="6" x2="20" y2="6" />
        <line x1="4" y1="12" x2="20" y2="12" />
        <line x1="4" y1="18" x2="20" y2="18" />
        <circle cx="9" cy="6" r="2" fill="#FAF9F6" />
        <circle cx="15" cy="12" r="2" fill="#FAF9F6" />
        <circle cx="10" cy="18" r="2" fill="#FAF9F6" />
      </svg>
      <span>Options</span>
    </button>
  </header>
</template>
