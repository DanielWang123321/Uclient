// Copy the Draco decoder shipped with three.js into public/ so it works offline.
import { cpSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const threeRoot = join(here, '..', 'node_modules', 'three')
const out = join(here, '..', 'public', 'draco')
mkdirSync(out, { recursive: true })
for (const f of ['draco_decoder.js', 'draco_decoder.wasm', 'draco_wasm_wrapper.js']) {
  cpSync(join(threeRoot, 'examples/jsm/libs/draco', f), join(out, f))
}
console.log('draco decoder ->', out)
