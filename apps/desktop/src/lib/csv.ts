import type { TorqueResult } from '../rpc/types'

export function torqueCsv(jointNames: string[], q: number[], t: TorqueResult): string {
  const rows = [['joint', 'q_deg', 'tau_nm', 'tau_arm_nm', 'tau_payload_nm', 'max_torque_nm', 'utilization_pct']]
  jointNames.forEach((n, i) =>
    rows.push([
      n,
      q[i].toFixed(4),
      t.tau_nm[i].toFixed(4),
      t.tau_arm_nm?.[i]?.toFixed(4) ?? '',
      t.tau_payload_nm?.[i]?.toFixed(4) ?? '',
      t.effort_limits_nm[i].toFixed(2),
      (t.utilization[i] * 100).toFixed(2),
    ]),
  )
  return rows.map((r) => r.join(',')).join('\n') + '\n'
}
