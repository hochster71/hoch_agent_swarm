# HOCH NEURO — Photoreal Brain Image Specification

This document details the visual specification, generation prompt, and quality acceptance criteria for the `hoch-brain.png` asset.

## 1. Visual Generation Prompt
Use the following prompt in a high-quality image generation tool (e.g. Midjourney, Stable Diffusion, Imagen):

> **Prompt:** A photorealistic, hyper-detailed anatomical 3D render of a human brain on a pure dark black background. Show a glowing cyan core at the thalamus and brainstem center. Radiating outward from the center is a complex, delicate, glowing red and orange arterial network (like the Circle of Willis and cerebral arteries) tracing the contours of the cerebral cortex. Cinematic volumetric lighting, ultra-sharp focus on the vascular pathways, deep shadows, dark futuristic tech aesthetic, 8k resolution, octane render style.

## 2. Asset Details
- **Filename:** `hoch-brain.png`
- **Primary Path:** `frontend/public/assets/hoch-brain.png`
- **Secondary Path:** `assets/hoch-brain.png`
- **Resolution:** Minimum 1024 x 640 pixels (recommended 1920 x 1200 pixels)
- **Format:** Transparent PNG (or PNG with deep black `#000000` background)

## 3. Quality Acceptance Criteria
- **Background:** Must be pure black or fully transparent with no framing devices.
- **Arteries:** Red and orange arterial structures must be clearly visible and contrast highly against the dark background.
- **Core:** The thalamus center must have a distinct cyan/light-blue glow.
- **Aesthetic:** Must look premium, clinical, and clean — avoiding cartoonish or overly bright colors.

## 4. Execution Policy
*Generation of this asset using paid burst GPU or external services is a founder-gated action.*
Once generated, place the resulting `hoch-brain.png` in the target paths above.
