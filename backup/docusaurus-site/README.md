# Technical Resume Site

Resume website built with Docusaurus and TypeScript.

## Architecture

**Single Source of Truth**: Resume data lives in [`src/data/resume.json`](src/data/resume.json) following JSON Resume schema. TypeScript React component dynamically renders sections based on available data, eliminating duplication.

**Output Formats**:

- Responsive web version with sidebar navigation and modern UI
- Print-optimized PDF via Playwright automation (`npm run pdf`)

**Print/Screen Optimization**: CSS media queries provide distinct layouts. Print version uses compact spacing, hides interactive elements, and optimizes for Letter format.

## Key Features

- **Type Safety**: Full TypeScript implementation with JSON Resume schema types
- **Responsive Design**: Mobile-first CSS Grid layout with sticky sidebar on desktop
- **Automated PDF**: Playwright generates PDFs from web version, ensuring consistency
- **GitHub Pages**: Zero-config deployment with automated builds
- **Extensible**: Docusaurus foundation supports blog, docs, and custom pages

## Usage

```bash
npm install
npm start          # Development server
npm run build      # Production build
npm run pdf        # Generate PDF from built site
npm run build:pdf  # Build + PDF in one command
```
