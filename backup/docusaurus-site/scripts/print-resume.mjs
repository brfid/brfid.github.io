#!/usr/bin/env node
// Generate a PDF of /resume from the built site using Playwright
// Usage: node scripts/print-resume.mjs [port]

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BUILD_DIR = path.resolve(__dirname, '..', 'build');
const PORT = Number(process.argv[2]) || 4173;

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case '.html': return 'text/html; charset=utf-8';
    case '.css': return 'text/css; charset=utf-8';
    case '.js': return 'text/javascript; charset=utf-8';
    case '.json': return 'application/json; charset=utf-8';
    case '.svg': return 'image/svg+xml';
    case '.png': return 'image/png';
    case '.jpg':
    case '.jpeg': return 'image/jpeg';
    case '.gif': return 'image/gif';
    case '.ico': return 'image/x-icon';
    case '.woff': return 'font/woff';
    case '.woff2': return 'font/woff2';
    default: return 'application/octet-stream';
  }
}

function startStaticServer(rootDir, port) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://localhost:${port}`);
    let filePath = path.join(rootDir, decodeURIComponent(url.pathname));

    // Map directory paths to index.html
    try {
      const stat = fs.existsSync(filePath) && fs.statSync(filePath);
      if (stat && stat.isDirectory()) {
        filePath = path.join(filePath, 'index.html');
      }
    } catch {}

    if (!fs.existsSync(filePath)) {
      // Try with trailing slash and index.html
      const alt = path.join(rootDir, decodeURIComponent(url.pathname), 'index.html');
      if (fs.existsSync(alt)) {
        filePath = alt;
      }
    }

    if (!fs.existsSync(filePath)) {
      res.writeHead(404, {'Content-Type': 'text/plain; charset=utf-8'});
      res.end('Not Found');
      return;
    }

    res.writeHead(200, {'Content-Type': contentType(filePath)});
    fs.createReadStream(filePath).pipe(res);
  });

  return new Promise((resolve) => {
    server.listen(port, () => resolve(server));
  });
}

async function main() {
  if (!fs.existsSync(BUILD_DIR)) {
    console.error('Build directory not found. Run "npm run build" first.');
    process.exit(1);
  }

  let server;
  try {
    server = await startStaticServer(BUILD_DIR, PORT);
    const url = `http://localhost:${PORT}/resume`;

    let chromium;
    try {
      // Lazy import to provide a clearer error if Playwright isn't installed
      ({chromium} = await import('playwright'));
    } catch (e) {
      console.error('\nPlaywright is not installed. Install with:');
      console.error('  npm i -D playwright');
      console.error('Then run:');
      console.error('  npx playwright install');
      process.exit(1);
    }

    const browser = await chromium.launch({headless: true});
    const page = await browser.newPage();
    await page.emulateMedia({media: 'print'});
    await page.goto(url, {waitUntil: 'networkidle'});

    const outPath = path.join(BUILD_DIR, 'resume.pdf');
    await page.pdf({
      path: outPath,
      format: 'Letter',
      printBackground: true,
      margin: {top: '0.5in', right: '0.5in', bottom: '0.5in', left: '0.5in'},
    });

    // Also copy to static/ so dev server can serve /resume.pdf
    const staticDir = path.resolve(__dirname, '..', 'static');
    try { fs.mkdirSync(staticDir, {recursive: true}); } catch {}
    const staticOut = path.join(staticDir, 'resume.pdf');
    fs.copyFileSync(outPath, staticOut);

    await browser.close();
    console.log(`Saved PDF: ${path.relative(process.cwd(), outPath)}`);
    console.log(`Copied PDF to: ${path.relative(process.cwd(), staticOut)}`);
  } finally {
    if (server) server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
