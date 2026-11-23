import { invoke } from '@tauri-apps/api/core'
import { getCurrentWebview } from '@tauri-apps/api/webview'
import { open, save } from '@tauri-apps/plugin-dialog'
import { openPath, revealItemInDir } from '@tauri-apps/plugin-opener'
import { Command } from '@tauri-apps/plugin-shell'

export type ConversionStatusState =
  | 'idle'
  | 'ready'
  | 'converting'
  | 'success'
  | 'error'

export interface SelectedPdfFile {
  path: string
  name: string
  size: number
  dir: string
}

export interface ConversionWarning {
  code: string
  message: string
}

export interface ConversionStats {
  fonts_normalized: number
  empty_paragraphs_removed: number
  artifacts_stripped: number
  tables_processed: number
  ocr_pages?: number
  ocr_images_replaced?: number
}

export interface ConversionResultMeta {
  outputPath: string
  pages: number
  warnings: ConversionWarning[]
  stats: ConversionStats
}

export interface ConversionOptions {
  normalizeFonts: boolean
  stripEmptyLines: boolean
  cleanEncoding: boolean
  preserveLayoutTables: boolean
  ocrScanned: boolean
  forceOcr: boolean
}

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
}

function deriveOutputPath(pdfPath: string): string {
  if (/\.pdf$/i.test(pdfPath)) {
    return pdfPath.replace(/\.pdf$/i, '.docx')
  }
  return `${pdfPath}.docx`
}

function extractFilename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

function extractDir(filePath: string): string {
  const idx = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'))
  return idx > 0 ? filePath.slice(0, idx) : ''
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let val = bytes
  let idx = 0
  while (val >= 1024 && idx < units.length - 1) {
    val /= 1024
    idx += 1
  }
  return `${val < 10 && idx > 0 ? val.toFixed(1) : Math.round(val)} ${units[idx]}`
}

export function useConverter() {
  const selectedFile = useState<SelectedPdfFile | null>('ganto:selectedFile', () => null)
  const outputPath = useState<string>('ganto:outputPath', () => '')
  const status = useState<ConversionStatusState>('ganto:status', () => 'idle')
  const progress = useState<number>('ganto:progress', () => 0)
  const stage = useState<string>('ganto:stage', () => '')
  const statusMessage = useState<string>('ganto:statusMessage', () => '')
  const warnings = useState<ConversionWarning[]>('ganto:warnings', () => [])
  const errorMessage = useState<string>('ganto:errorMessage', () => '')
  const resultMeta = useState<ConversionResultMeta | null>('ganto:resultMeta', () => null)
  const isDragging = useState<boolean>('ganto:isDragging', () => false)

  const options = useState<ConversionOptions>('ganto:options', () => ({
    normalizeFonts: true,
    stripEmptyLines: true,
    cleanEncoding: true,
    preserveLayoutTables: true,
    ocrScanned: true,
    forceOcr: false,
  }))

  let unlistenDragDrop: (() => void) | null = null

  async function selectFile(path: string): Promise<void> {
    if (!path.toLowerCase().endsWith('.pdf')) {
      status.value = 'error'
      errorMessage.value = 'Invalid file type. Please choose a valid .pdf document.'
      return
    }

    errorMessage.value = ''
    warnings.value = []
    resultMeta.value = null
    progress.value = 0
    stage.value = ''
    statusMessage.value = ''

    if (isTauriRuntime()) {
      try {
        const meta = await invoke<SelectedPdfFile>('get_file_metadata', { path })
        selectedFile.value = meta
      } catch {
        selectedFile.value = {
          path,
          name: extractFilename(path),
          size: 0,
          dir: extractDir(path),
        }
      }
    } else {
      selectedFile.value = {
        path,
        name: extractFilename(path),
        size: 0,
        dir: extractDir(path),
      }
    }

    outputPath.value = deriveOutputPath(path)
    status.value = 'ready'
  }

  async function browsePdf(): Promise<void> {
    if (!isTauriRuntime()) {
      status.value = 'error'
      errorMessage.value = 'Desktop file picker is available when running inside the GantoFile Tauri app.'
      return
    }

    const picked = await open({
      multiple: false,
      directory: false,
      title: 'Select PDF Document',
      filters: [{ name: 'PDF Document', extensions: ['pdf'] }],
    })

    if (typeof picked === 'string' && picked.length > 0) {
      await selectFile(picked)
    }
  }

  async function chooseOutputPath(): Promise<void> {
    if (!isTauriRuntime() || !selectedFile.value) return

    const chosen = await save({
      title: 'Save Converted DOCX As',
      defaultPath: outputPath.value || deriveOutputPath(selectedFile.value.path),
      filters: [{ name: 'Word Document', extensions: ['docx'] }],
    })

    if (typeof chosen === 'string' && chosen.length > 0) {
      outputPath.value = chosen.toLowerCase().endsWith('.docx') ? chosen : `${chosen}.docx`
    }
  }

  function handleEngineEvent(line: string): void {
    const trimmed = line.trim()
    if (!trimmed) return

    let payload: Record<string, unknown>
    try {
      payload = JSON.parse(trimmed) as Record<string, unknown>
    } catch {
      return
    }

    const eventType = String(payload.event ?? '')

    if (eventType === 'progress') {
      progress.value = typeof payload.percent === 'number' ? payload.percent : progress.value
      stage.value = typeof payload.stage === 'string' ? payload.stage : ''
      statusMessage.value = typeof payload.message === 'string' ? payload.message : ''
    } else if (eventType === 'warning') {
      const code = typeof payload.code === 'string' ? payload.code : 'WARNING'
      const message = typeof payload.message === 'string' ? payload.message : ''
      if (message && !warnings.value.some((w) => w.code === code && w.message === message)) {
        warnings.value = [...warnings.value, { code, message }]
      }
    } else if (eventType === 'done') {
      progress.value = 100
      stage.value = 'done'
      statusMessage.value = 'Conversion completed.'
      const finalOut =
        typeof payload.output_path === 'string' ? payload.output_path : outputPath.value
      outputPath.value = finalOut
      resultMeta.value = {
        outputPath: finalOut,
        pages: typeof payload.pages === 'number' ? payload.pages : 0,
        warnings: Array.isArray(payload.warnings)
          ? (payload.warnings as ConversionWarning[])
          : warnings.value,
        stats: (payload.stats as ConversionStats) ?? {
          fonts_normalized: 0,
          empty_paragraphs_removed: 0,
          artifacts_stripped: 0,
          tables_processed: 0,
        },
      }
      status.value = 'success'
    } else if (eventType === 'error') {
      errorMessage.value =
        typeof payload.message === 'string' ? payload.message : 'PDF conversion failed.'
      status.value = 'error'
    }
  }

  async function convert(): Promise<void> {
    if (!selectedFile.value || status.value === 'converting') return

    if (!isTauriRuntime()) {
      status.value = 'error'
      errorMessage.value = 'Sidecar conversion requires the GantoFile Tauri desktop runtime.'
      return
    }

    const targetOut = outputPath.value || deriveOutputPath(selectedFile.value.path)
    outputPath.value = targetOut

    status.value = 'converting'
    progress.value = 5
    stage.value = 'starting'
    statusMessage.value = 'Launching local conversion engine...'
    warnings.value = []
    errorMessage.value = ''
    resultMeta.value = null

    const args: string[] = [
      '--input',
      selectedFile.value.path,
      '--output',
      targetOut,
      options.value.normalizeFonts ? '--normalize-fonts' : '--no-normalize-fonts',
      options.value.stripEmptyLines ? '--strip-empty-lines' : '--no-strip-empty-lines',
      options.value.cleanEncoding ? '--clean-encoding' : '--no-clean-encoding',
      options.value.preserveLayoutTables
        ? '--preserve-layout-tables'
        : '--no-preserve-layout-tables',
      options.value.ocrScanned ? '--ocr-scanned' : '--no-ocr-scanned',
      options.value.forceOcr ? '--force-ocr' : '--no-force-ocr',
    ]

    let stdoutBuffer = ''
    const stderrLines: string[] = []

    try {
      const command = Command.sidecar('binaries/ganto-engine', args)

      command.stdout.on('data', (chunk: string) => {
        stdoutBuffer += chunk
        const lines = stdoutBuffer.split(/\r?\n/)
        stdoutBuffer = lines.pop() ?? ''
        for (const line of lines) {
          handleEngineEvent(line)
        }
      })

      command.stderr.on('data', (chunk: string) => {
        const trimmed = chunk.trim()
        if (trimmed) stderrLines.push(trimmed)
      })

      const closePromise = new Promise<void>((resolve) => {
        command.on('close', ({ code }) => {
          if (stdoutBuffer.trim()) {
            handleEngineEvent(stdoutBuffer)
            stdoutBuffer = ''
          }
          if (status.value === 'converting') {
            if (code === 0) {
              status.value = 'success'
              progress.value = 100
            } else {
              status.value = 'error'
              errorMessage.value =
                stderrLines[stderrLines.length - 1] ||
                `Conversion engine exited with code ${code ?? 'unknown'}.`
            }
          }
          resolve()
        })

        command.on('error', (err) => {
          status.value = 'error'
          errorMessage.value = typeof err === 'string' ? err : String(err)
          resolve()
        })
      })

      await command.spawn()
      await closePromise
    } catch (err) {
      status.value = 'error'
      errorMessage.value =
        err instanceof Error ? err.message : 'Unable to start local conversion sidecar.'
    }
  }

  async function openOutputFile(): Promise<void> {
    const target = resultMeta.value?.outputPath || outputPath.value
    if (!target || !isTauriRuntime()) return
    try {
      await openPath(target)
    } catch (err) {
      errorMessage.value =
        err instanceof Error ? err.message : 'Could not open output DOCX file.'
    }
  }

  async function revealOutputFolder(): Promise<void> {
    const target = resultMeta.value?.outputPath || outputPath.value
    if (!target || !isTauriRuntime()) return
    try {
      await revealItemInDir(target)
    } catch (err) {
      errorMessage.value =
        err instanceof Error ? err.message : 'Could not reveal output folder.'
    }
  }

  function reset(): void {
    selectedFile.value = null
    outputPath.value = ''
    status.value = 'idle'
    progress.value = 0
    stage.value = ''
    statusMessage.value = ''
    warnings.value = []
    errorMessage.value = ''
    resultMeta.value = null
    isDragging.value = false
  }

  async function setupDragDrop(): Promise<void> {
    if (!isTauriRuntime() || unlistenDragDrop) return

    unlistenDragDrop = await getCurrentWebview().onDragDropEvent(async (event) => {
      if (status.value === 'converting') return

      if (event.payload.type === 'enter' || event.payload.type === 'over') {
        isDragging.value = true
      } else if (event.payload.type === 'leave') {
        isDragging.value = false
      } else if (event.payload.type === 'drop') {
        isDragging.value = false
        const paths = event.payload.paths
        if (paths && paths.length > 0 && paths[0]) {
          await selectFile(paths[0])
        }
      }
    })
  }

  function teardownDragDrop(): void {
    if (unlistenDragDrop) {
      unlistenDragDrop()
      unlistenDragDrop = null
    }
  }

  return {
    selectedFile,
    outputPath,
    status,
    progress,
    stage,
    statusMessage,
    warnings,
    errorMessage,
    resultMeta,
    options,
    isDragging,
    selectFile,
    browsePdf,
    chooseOutputPath,
    convert,
    openOutputFile,
    revealOutputFolder,
    reset,
    setupDragDrop,
    teardownDragDrop,
  }
}
