<script setup lang="ts">
import { formatBytes, useConverter } from '~/composables/useConverter'

const {
  selectedFile,
  outputPath,
  status,
  isDragging,
  browsePdf,
  chooseOutputPath,
  convert,
  reset,
} = useConverter()
</script>

<template>
  <section class="w-full">
    <!-- Empty / Idle Dropzone -->
    <div
      v-if="!selectedFile"
      class="w-full border rounded-[4px] p-7 flex flex-col items-center justify-center text-center transition-colors"
      :class="
        isDragging
          ? 'bg-[#B7D894]/25 border-solid border-[#202734]'
          : 'bg-[#FFFFFF] border-dashed border-[#202734]/30 hover:border-[#202734]/60'
      "
    >
      <div class="w-10 h-10 rounded-[4px] bg-[#F1F3F5] border border-[#202734]/20 flex items-center justify-center mb-3.5">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#202734"
          stroke-width="1.75"
          stroke-linecap="square"
          stroke-linejoin="miter"
          aria-hidden="true"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <polyline points="9 15 12 12 15 15" />
        </svg>
      </div>

      <h2 class="text-base font-semibold tracking-[-0.01em] text-[#202734]">
        {{ isDragging ? 'Drop PDF to prepare conversion' : 'Drop a structured PDF here' }}
      </h2>
      <p class="mt-1 text-xs text-[#202734]/70 max-w-sm leading-relaxed">
        Preserves fonts, margins, signature tables, and clean paragraph flow locally on your device.
      </p>

      <button
        type="button"
        class="mt-5 px-4 py-2 text-xs font-semibold bg-[#202734] text-[#FAF9F6] border border-[#202734] rounded-[4px] hover:bg-[#202734]/90 cursor-pointer transition-colors"
        @click="browsePdf"
      >
        Select PDF File
      </button>
    </div>

    <!-- Selected PDF Card (Ready / Converting / Done / Error) -->
    <div
      v-else
      class="w-full bg-[#F1F3F5] border border-[#202734]/20 rounded-[4px] p-4 space-y-3"
    >
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3 min-w-0">
          <div class="w-9 h-9 rounded-[4px] bg-[#202734] text-[#B7D894] flex items-center justify-center shrink-0 text-[11px] font-bold tracking-wide">
            PDF
          </div>
          <div class="min-w-0">
            <p class="text-sm font-semibold text-[#202734] truncate" :title="selectedFile.name">
              {{ selectedFile.name }}
            </p>
            <p class="text-xs text-[#202734]/65 truncate mt-0.5" :title="selectedFile.path">
              {{ formatBytes(selectedFile.size) }}
              <span v-if="selectedFile.dir"> · {{ selectedFile.dir }}</span>
            </p>
          </div>
        </div>

        <button
          v-if="status !== 'converting'"
          type="button"
          class="px-2.5 py-1 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/20 rounded-[4px] hover:bg-[#FAF9F6] cursor-pointer shrink-0"
          @click="reset"
        >
          Clear
        </button>
      </div>

      <!-- Output Destination Row -->
      <div class="flex items-center justify-between gap-2 bg-[#FFFFFF] border border-[#202734]/15 rounded-[4px] px-3 py-2">
        <div class="min-w-0 flex-1">
          <span class="block text-[10px] font-semibold uppercase tracking-wider text-[#202734]/55">
            Output DOCX
          </span>
          <p class="text-xs text-[#202734] truncate mt-0.5" :title="outputPath">
            {{ outputPath }}
          </p>
        </div>

        <button
          v-if="status === 'ready' || status === 'error'"
          type="button"
          class="px-2.5 py-1 text-xs font-medium text-[#202734] bg-[#F1F3F5] border border-[#202734]/20 rounded-[4px] hover:bg-[#B7D894]/30 cursor-pointer shrink-0"
          @click="chooseOutputPath"
        >
          Change
        </button>
      </div>

      <!-- Primary Conversion Action -->
      <div v-if="status === 'ready'" class="pt-1 flex items-center justify-end gap-2">
        <button
          type="button"
          class="px-3.5 py-2 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/25 rounded-[4px] hover:bg-[#FAF9F6] cursor-pointer"
          @click="browsePdf"
        >
          Replace PDF
        </button>
        <button
          type="button"
          class="px-4 py-2 text-xs font-bold text-[#202734] bg-[#B7D894] border border-[#202734] rounded-[4px] hover:bg-[#a9ce83] cursor-pointer"
          @click="convert"
        >
          Convert to DOCX
        </button>
      </div>
    </div>
  </section>
</template>
