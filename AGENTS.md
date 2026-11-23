# PRD & Technical Architecture Specification: Ganto

**Project Name:** Ganto  
**Application Type:** Cross-Platform Native Desktop Utility (macOS & Windows)  
**Core Function:** Offline, high-precision PDF-to-DOCX document conversion preserving exact typography, layout structure, tables, headers, and spacing without extraneous characters or formatting artifacts.  
**Tech Stack:** Tauri v2 + Nuxt v4 + Nuxt UI + Tailwind CSS + Python Sidecar (`pdf2docx`, `python-docx`, `PyMuPDF`)

---

## 1. Product Overview & Core Principles

**Ganto** is a lightweight, offline-first desktop application designed to convert structured PDF documents (such as official letters, administrative templates, and reports) into clean, ready-to-edit `.docx` files.

### Core Functional Goals
1. **Structural & Typographic Fidelity:** Maintain exact page margins, line spacing, font families, invisible layout tables (e.g., signature blocks, letterheads), and paragraph alignment.
2. **Artifact-Free Output:** Strip redundant line breaks, broken character encodings, floating unnecessary text boxes, and embedded font gibberish so the resulting `.docx` flows naturally when edited in Microsoft Word or LibreOffice.
3. **100% Local & Private:** Zero cloud uploads. All processing runs locally via an embedded Python sidecar binary.
4. **Cross-Platform Parity:** Built on macOS and compiled cleanly for both **macOS** (`.app` / `.dmg` for Apple Silicon & Intel) and **Windows** (`.exe` / `.msi`).

---

## 2. Strict UI/UX Design System & Brand Guidelines

The AI coding agent MUST strictly enforce the following visual rules across all components, states, and CSS overrides.

### 2.1 Color Palette
* **Primary Ink / Dark Surface (`#202734`):** Deep slate charcoal. Used for primary typography, primary action buttons, active borders, and dark-mode surfaces.
* **Primary Accent / Highlight (`#B7D894`):** Soft sage lime. Used for primary CTA fills (paired with `#202734` text), active dropzone highlights, progress indicators, and success states.
* **Background Canvas (`#FAF9F6` or `#FFFFFF`):** Crisp, clean off-white paper canvas for maximum legibility.
* **Subtle Surface / Secondary Fill (`#F1F3F5`):** Flat muted surface for secondary containers, file metadata cards, and disabled states.
* **Border / Divider (`#D0D5DD` or `#202734` at 15% opacity):** Crisp `1px` solid or dashed structural borders.
* **Error State (`#DC2626`):** Flat crimson for invalid file warnings or scanned-PDF alerts.

### 2.2 Typography
* **Primary Font Family:** **Lora** (Google Fonts / local bundled `.woff2` for offline reliability).
  * **App Title / Headings:** `Lora`, SemiBold (`600`) or Bold (`700`), tight tracking (`-0.01em`).
  * **Body / UI Labels / File Paths:** `Lora`, Regular (`400`) and Medium (`500`).
  * **Monospace (Technical logs/codes only, if needed):** System monospace.
* *Note:* Bundle `Lora` font files locally inside `app/assets/fonts/` so typography renders identically offline without requiring an internet connection.

### 2.3 Strict Visual Constraints (Zero Slop Rules)
* **Style:** Strict **Flat UI**.
* **NO Drop Shadows:** `box-shadow: none !important;` on all cards, buttons, modals, and inputs.
* **NO Gradients:** Solid flat hex colors only (`#202734`, `#B7D894`, `#FAF9F6`). Never use `linear-gradient` or `radial-gradient`.
* **NO Blur / Glassmorphism:** No `backdrop-filter: blur()`.
* **Rounded Corners (`Small`):** Maximum border radius of `4px` (`rounded` / `rounded-[4px]`) for buttons, cards, badges, and dropzones. Avoid pill shapes (`rounded-full`) or large rounded cards (`rounded-xl`/`rounded-2xl`).
* **Hierarchy via Borders & Contrast:** Use crisp `1px` solid borders (`border-[#202734]/20`) and high-contrast color blocks (`#202734` vs `#B7D894`) instead of elevation shadows.

---

## 3. System Architecture & Directory Structure

```text
ganto/
├── app/                          # Nuxt v4 Frontend Directory
│   ├── assets/
│   │   ├── css/
│   │   │   └── main.css          # Tailwind + Lora font-face + flat overrides
│   │   └── fonts/                # Local Lora .woff2 files (Regular, Medium, SemiBold, Bold)
│   ├── components/
│   │   ├── AppHeader.vue         # Minimalist title bar & conversion options
│   │   ├── FileDropzone.vue      # Native Tauri drag-and-drop PDF target
│   │   ├── ConversionStatus.vue  # Active progress, warnings, & post-convert actions
│   │   └── SettingsDrawer.vue    # Optional post-processing toggles
│   ├── composables/
│   │   └── useConverter.ts       # Tauri Sidecar IPC invocation & file dialog logic
│   └── app.vue                   # Single-window desktop app shell
├── src-tauri/                    # Tauri v2 Rust Backend
│   ├── binaries/                 # Compiled PyInstaller sidecar binaries
│   │   ├── ganto-engine-aarch64-apple-darwin
│   │   ├── ganto-engine-x86_64-apple-darwin
│   │   └── ganto-engine-x86_64-pc-windows-msvc.exe
│   ├── capabilities/
│   │   └── default.json          # Tauri v2 permissions (shell, dialog, fs)
│   ├── src/
│   │   └── main.rs               # Rust entry point
│   ├── Cargo.toml
│   └── tauri.conf.json           # Window config (non-resizable/compact, externalBin)
├── sidecar-python/               # Python Conversion Engine
│   ├── engine.py                 # CLI entrypoint using pdf2docx + python-docx cleanup
│   ├── cleaner.py                # Post-processing rules (font normalization, whitespace)
│   ├── requirements.txt          # pdf2docx, python-docx, PyMuPDF
│   └── build_sidecar.py          # Automated PyInstaller build script per OS target
├── nuxt.config.ts                # SSR: false (SPA mode required for Tauri)
└── package.json