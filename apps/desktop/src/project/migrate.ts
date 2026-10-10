// Project file (*.uclient.json) schema and migrations (design doc §6.1).
export const SCHEMA_VERSION = 1

export interface TcpPreset {
  id: string
  name: string
  offset: number[]
}
export interface PayloadPreset {
  id: string
  name: string
  mass_kg: number
  com_mm: number[]
  inertia_kgm2: number[] | null
}
export interface ProjectFile {
  schema_version: number
  app: { name: string; version: string }
  core: { ufactory_genesis_commit: string; pinocchio: string }
  robot: { key: string; end_effector: string; calibration: null; mounting: { gravity_dir: number[] } }
  tcp_presets: TcpPreset[]
  payload_presets: PayloadPreset[]
  active: { tcp: string; payload: string }
  poses: { id: string; name: string; tcp_pose: number[]; q_deg?: number[] }[]
  trajectories: unknown[]
  results: unknown[]
}

export function newProject(): ProjectFile {
  return {
    schema_version: SCHEMA_VERSION,
    app: { name: 'Uclient', version: '0.1.0' },
    core: { ufactory_genesis_commit: '60fe926', pinocchio: '4.0.0' },
    robot: { key: 'uf850', end_effector: 'none', calibration: null, mounting: { gravity_dir: [0, 0, -1] } },
    // Tool TCPs come from the sidecar (URDF tcp joint of the mounted end effector), not from here.
    tcp_presets: [{ id: 'flange', name: 'Flange', offset: [0, 0, 0, 0, 0, 0] }],
    payload_presets: [{ id: 'p3kg', name: '3kg box', mass_kg: 3.0, com_mm: [0, 0, 35], inertia_kgm2: null }],
    active: { tcp: 'flange', payload: 'p3kg' },
    poses: [{ id: 'case-850-a', name: '850 far reach', tcp_pose: [830, 0, 200, -180, 0, 0] }],
    trajectories: [],
    results: [],
  }
}

type Migration = (p: Record<string, unknown>) => Record<string, unknown>
// index i migrates schema i -> i+1. Version 0 = pre-release files without schema_version.
const MIGRATIONS: Migration[] = [(p) => ({ ...newProject(), ...p, schema_version: 1 })]

export function migrate(raw: unknown): ProjectFile {
  if (typeof raw !== 'object' || raw === null) throw new Error('project file must be a JSON object')
  let p = raw as Record<string, unknown>
  let v = typeof p.schema_version === 'number' ? p.schema_version : 0
  if (v > SCHEMA_VERSION) throw new Error(`project schema ${v} is newer than this app (${SCHEMA_VERSION})`)
  while (v < SCHEMA_VERSION) {
    p = MIGRATIONS[v](p)
    v += 1
  }
  return dropStaleG2Preset(p as unknown as ProjectFile)
}

/** v0.1.0 shipped a 'g2' preset of z = 101.1 mm, which is a grasp-planning offset, not the G2 TCP. */
function dropStaleG2Preset(p: ProjectFile): ProjectFile {
  const stale = (t: TcpPreset) => t.id === 'g2' && t.offset.join(',') === '0,0,101.1,0,0,0'
  if (!p.tcp_presets?.some(stale)) return p
  const tcp_presets = p.tcp_presets.filter((t) => !stale(t))
  const active = p.active?.tcp === 'g2' ? { ...p.active, tcp: 'flange' } : p.active
  return { ...p, tcp_presets, active }
}
