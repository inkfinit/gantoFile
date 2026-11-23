<script setup lang="ts">
import { useConverter } from '~/composables/useConverter'

defineProps<{
  open: boolean
}>()

defineEmits<{
  (e: 'close'): void
}>()

const { options } = useConverter()

interface ToggleItem {
  key: keyof typeof options.value
  label: string
  description: string
}

const toggleItems: ToggleItem[] = [
  {
    key: 'ocrScanned',
    label: 'Offline OCR for scanned / image PDFs',
    description: 'Extract editable text and layout from image-based PDFs locally via ONNX OCR.',
  },
  {
    key: 'normalizeFonts',
    label: 'Normalize embedded PDF fonts',
    description: 'Strip subset prefixes (e.g. ABCDEE+) and map PostScript names to system fonts.',
  },
  {
    key: 'stripEmptyLines',
    label: 'Strip redundant empty lines',
    description: 'Collapse stacked blank paragraphs and trailing whitespace for natural editing.',
  },
  {
    key: 'cleanEncoding',
    label: 'Clean broken encodings & artifacts',
    description: 'Remove replacement glyphs, zero-width spaces, and map stray PUA bullets.',
  },
  {
    key: 'preserveLayoutTables',
    label: 'Preserve invisible layout tables',
    description: 'Keep signature blocks and letterhead tables strictly borderless in Word.',
  },
]
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex justify-end">
    <!-- Solid flat scrim (no blur) -->
    <div
      class="flex-1 bg-[#202734]/35"
      aria-hidden="true"
      @click="$emit('close')"
    />

    <aside
      class="w-80 h-full bg-[#FAF9F6] border-l border-[#202734]/20 flex flex-col justify-between p-5"
      role="dialog"
      aria-label="Conversion Options"
    >
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-[#202734]/15">
          <div>
            <h2 class="text-sm font-bold tracking-[-0.01em] text-[#202734]">
              Post-Processing Rules
            </h2>
            <p class="text-[11px] text-[#202734]/65 mt-0.5">
              Applied locally after PDF layout extraction
            </p>
          </div>
          <button
            type="button"
            class="px-2 py-1 text-xs font-medium text-[#202734] bg-[#FFFFFF] border border-[#202734]/20 rounded-[4px] hover:bg-[#F1F3F5] cursor-pointer"
            @click="$emit('close')"
          >
            Close
          </button>
        </div>

        <div class="space-y-3">
          <label
            v-for="item in toggleItems"
            :key="item.key"
            class="flex items-start justify-between gap-3 p-3 bg-[#FFFFFF] border border-[#202734]/15 rounded-[4px] cursor-pointer hover:border-[#202734]/35"
          >
            <div class="space-y-0.5">
              <span class="block text-xs font-semibold text-[#202734]">
                {{ item.label }}
              </span>
              <span class="block text-[11px] text-[#202734]/65 leading-snug">
                {{ item.description }}
              </span>
            </div>

            <button
              type="button"
              role="switch"
              :aria-checked="options[item.key]"
              class="w-9 h-5 rounded-[4px] border border-[#202734] p-0.5 shrink-0 transition-colors cursor-pointer flex items-center"
              :class="options[item.key] ? 'bg-[#B7D894] justify-end' : 'bg-[#F1F3F5] justify-start'"
              @click.prevent="options[item.key] = !options[item.key]"
            >
              <span class="w-3.5 h-3.5 rounded-[2px] bg-[#202734] block" />
            </button>
          </label>
        </div>
      </div>

      <div class="pt-3 border-t border-[#202734]/15 space-y-1.5">
        <div class="flex items-center justify-between text-[11px] text-[#202734]/60">
          <span>Engine: PyMuPDF + RapidOCR + pdf2docx</span>
          <button
            type="button"
            class="font-semibold text-[#202734] underline cursor-pointer"
            @click="
              options.ocrScanned = true;
              options.normalizeFonts = true;
              options.stripEmptyLines = true;
              options.cleanEncoding = true;
              options.preserveLayoutTables = true;
            "
          >
            Reset defaults
          </button>
        </div>
        <p class="text-[11px] text-[#202734]/75">
          Developed by <span class="font-semibold text-[#202734]">Rianda Syahputra, S.P.</span>
        </p>
      </div>
    </aside>
  </div>
</template>
