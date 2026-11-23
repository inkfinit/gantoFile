<script setup lang="ts">
import { useConverter } from '~/composables/useConverter'

const {
  status,
  progress,
  statusMessage,
  warnings,
  errorMessage,
  resultMeta,
  convert,
  openOutputFile,
  revealOutputFolder,
  reset,
} = useConverter()
</script>

<template>
  <section v-if="status !== 'idle' && status !== 'ready'" class="w-full space-y-3">
    <!-- Active Progress -->
    <div
      v-if="status === 'converting'"
      class="bg-[#FFFFFF] border border-[#202734]/20 rounded-[4px] p-4 space-y-2.5"
    >
      <div class="flex items-center justify-between text-xs font-medium text-[#202734]">
        <span>{{ statusMessage || 'Converting document...' }}</span>
        <span class="font-semibold tabular-nums">{{ progress }}%</span>
      </div>
      <div class="w-full h-2.5 bg-[#F1F3F5] border border-[#202734]/20 rounded-[4px] overflow-hidden">
        <div
          class="h-full bg-[#B7D894] transition-all duration-200"
          :style="{ width: `${Math.max(progress, 4)}%` }"
        />
      </div>
    </div>

    <!-- Warnings (e.g., Scanned PDF notice) -->
    <div
      v-for="(warn, idx) in warnings"
      :key="`${warn.code}-${idx}`"
      class="bg-[#FAF9F6] border border-[#DC2626] rounded-[4px] px-3.5 py-2.5 text-xs text-[#202734]"
    >
      <span class="font-bold text-[#DC2626] uppercase tracking-wide mr-1.5">Notice:</span>
      <span>{{ warn.message }}</span>
    </div>

    <!-- Success State -->
    <div
      v-if="status === 'success' && resultMeta"
      class="bg-[#B7D894]/25 border border-[#202734] rounded-[4px] p-4 space-y-3"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <h3 class="text-sm font-bold tracking-[-0.01em] text-[#202734]">
            DOCX Ready
          </h3>
          <p class="text-xs text-[#202734]/80 mt-0.5">
            Converted {{ resultMeta.pages }} page(s) cleanly.
          </p>
        </div>
        <span class="px-2 py-0.5 text-[11px] font-semibold bg-[#B7D894] text-[#202734] border border-[#202734] rounded-[4px]">
          Completed
        </span>
      </div>

      <!-- Cleanup Telemetry Strip -->
      <div class="grid grid-cols-4 gap-2 text-center">
        <div class="bg-[#FFFFFF] border border-[#202734]/15 rounded-[4px] px-2 py-1.5">
          <p class="text-xs font-bold text-[#202734]">{{ resultMeta.stats.fonts_normalized }}</p>
          <p class="text-[10px] text-[#202734]/65">Fonts Fixed</p>
        </div>
        <div class="bg-[#FFFFFF] border border-[#202734]/15 rounded-[4px] px-2 py-1.5">
          <p class="text-xs font-bold text-[#202734]">{{ resultMeta.stats.tables_processed }}</p>
          <p class="text-[10px] text-[#202734]/65">Layout Tables</p>
        </div>
        <div class="bg-[#FFFFFF] border border-[#202734]/15 rounded-[4px] px-2 py-1.5">
          <p class="text-xs font-bold text-[#202734]">{{ resultMeta.stats.empty_paragraphs_removed }}</p>
          <p class="text-[10px] text-[#202734]/65">Blanks Trimmed</p>
        </div>
        <div class="bg-[#FFFFFF] border border-[#202734]/15 rounded-[4px] px-2 py-1.5">
          <p class="text-xs font-bold text-[#202734]">{{ resultMeta.stats.artifacts_stripped }}</p>
          <p class="text-[10px] text-[#202734]/65">Artifacts Clean</p>
        </div>
      </div>

      <div class="flex items-center justify-between gap-2 pt-1">
        <button
          type="button"
          class="px-3 py-1.5 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/25 rounded-[4px] hover:bg-[#F1F3F5] cursor-pointer"
          @click="reset"
        >
          Convert Another
        </button>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="px-3 py-1.5 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/25 rounded-[4px] hover:bg-[#F1F3F5] cursor-pointer"
            @click="revealOutputFolder"
          >
            Show in Folder
          </button>
          <button
            type="button"
            class="px-3.5 py-1.5 text-xs font-semibold text-[#FAF9F6] bg-[#202734] border border-[#202734] rounded-[4px] hover:bg-[#202734]/90 cursor-pointer"
            @click="openOutputFile"
          >
            Open DOCX
          </button>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div
      v-if="status === 'error'"
      class="bg-[#DC2626]/10 border border-[#DC2626] rounded-[4px] p-4 space-y-3"
    >
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wide text-[#DC2626]">
          Conversion Error
        </h3>
        <p class="text-xs text-[#202734] mt-1 leading-relaxed">
          {{ errorMessage || 'Unable to process the selected PDF document.' }}
        </p>
      </div>

      <div class="flex items-center justify-end gap-2">
        <button
          type="button"
          class="px-3 py-1.5 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/25 rounded-[4px] hover:bg-[#F1F3F5] cursor-pointer"
          @click="reset"
        >
          Dismiss
        </button>
        <button
          type="button"
          class="px-3.5 py-1.5 text-xs font-semibold text-[#FAF9F6] bg-[#202734] border border-[#202734] rounded-[4px] hover:bg-[#202734]/90 cursor-pointer"
          @click="convert"
        >
          Try Again
        </button>
      </div>
    </div>
  </section>
</template>
