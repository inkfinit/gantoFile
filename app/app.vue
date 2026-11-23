<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useConverter } from '~/composables/useConverter'

const settingsOpen = ref(false)
const { setupDragDrop, teardownDragDrop } = useConverter()

onMounted(() => {
  void setupDragDrop()
})

onUnmounted(() => {
  teardownDragDrop()
})
</script>

<template>
  <UApp>
    <div class="h-screen w-screen overflow-hidden flex flex-col bg-[#FAF9F6] text-[#202734]">
      <AppHeader @open-settings="settingsOpen = true" />

      <main class="flex-1 overflow-y-auto px-5 py-5 flex flex-col justify-center gap-4">
        <FileDropzone />
        <ConversionStatus />
      </main>

      <footer class="px-5 py-2.5 border-t border-[#202734]/15 bg-[#F1F3F5] flex items-center justify-between text-[11px] text-[#202734]/70 shrink-0">
        <span>100% offline · Files never leave your device</span>
        <span class="font-medium text-[#202734]">Rianda Syahputra, S.P. · v0.1.0</span>
      </footer>

      <SettingsDrawer :open="settingsOpen" @close="settingsOpen = false" />
    </div>
  </UApp>
</template>
