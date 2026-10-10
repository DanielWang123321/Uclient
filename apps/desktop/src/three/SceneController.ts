import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'
import URDFLoader, { type URDFRobot } from 'urdf-loader'

export /** Camera distance factor for the robot framing (smaller = closer). */
const VIEW_FIT = 1.6
const ASSET_BASE = 'robot-assets/'

function eulerXYZ(rpyDeg: number[]): THREE.Euler {
  // Fixed-axis X-Y-Z RPY (R = Rz·Ry·Rx) equals three.js intrinsic 'ZYX' order.
  const [r, p, y] = rpyDeg.map((d) => THREE.MathUtils.degToRad(d))
  return new THREE.Euler(r, p, y, 'ZYX')
}

/**
 * Imperative three.js scene. Kept out of Vue reactivity (design doc §4/§8).
 * Z-up world (camera.up = +Z), metres/radians internally.
 */
export class SceneController {
  readonly renderer: THREE.WebGLRenderer
  readonly scene = new THREE.Scene()
  readonly camera: THREE.PerspectiveCamera
  readonly controls: OrbitControls
  private robot: URDFRobot | null = null
  private eeLink = 'link6'
  private tcpAxes = new THREE.AxesHelper(0.08)
  private baseAxes = new THREE.AxesHelper(0.15)
  private com = new THREE.Mesh(
    new THREE.SphereGeometry(1, 20, 14),
    new THREE.MeshStandardMaterial({ color: 0xff9f1c, emissive: 0x442200 }),
  )
  private gravityArrow = new THREE.ArrowHelper(new THREE.Vector3(0, 0, -1), new THREE.Vector3(), 0.1, 0xff9f1c)
  private renderRequested = false
  private resizeObs: ResizeObserver | null = null
  private draco: DRACOLoader
  private loadSeq = 0
  onLoaded: (ok: boolean, err?: unknown) => void = () => {}

  constructor(private host: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    host.appendChild(this.renderer.domElement)

    this.scene.background = new THREE.Color(0xf7f8f9) // light scene as in the v8 mockup
    this.scene.fog = new THREE.Fog(0xf7f8f9, 3, 10)
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.01, 50)
    this.camera.up.set(0, 0, 1)
    this.resetView()
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.target.set(0.3, 0, 0.35)
    this.controls.addEventListener('change', () => this.requestRender())
    this.controls.update()

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a96a8, 2.4))
    const sun = new THREE.DirectionalLight(0xffffff, 2.0)
    sun.position.set(2, -2, 4)
    this.scene.add(sun)
    const grid = new THREE.GridHelper(8, 80, 0xd5d8dd, 0xe3e5e9)
    grid.rotation.x = Math.PI / 2
    this.scene.add(grid)
    this.scene.add(this.baseAxes)
    this.com.visible = false
    this.gravityArrow.visible = false

    this.draco = new DRACOLoader()
    this.draco.setDecoderPath('draco/')

    this.resizeObs = new ResizeObserver(() => this.resize())
    this.resizeObs.observe(host)
    this.resize()
  }

  /** Default view; once a robot is loaded it is framed to fill the free scene area. */
  resetView() {
    let target = new THREE.Vector3(0.3, 0, 0.35)
    let pos = new THREE.Vector3(1.9, -1.6, 1.3)
    if (this.robot && this.reach > 0) {
      // Frame the whole reachable envelope (pose independent), not the current pose.
      const sphere = new THREE.Sphere(new THREE.Vector3(0.1 * this.reach, 0, 0.45 * this.reach), 0.62 * this.reach)
      target = sphere.center.clone()
      const dir = new THREE.Vector3(0.45, 1.0, 0.42).normalize()
      const fov = THREE.MathUtils.degToRad(this.camera.fov)
      pos = target.clone().addScaledVector(dir, (sphere.radius / Math.sin(fov / 2)) * VIEW_FIT)
    }
    this.camera.position.copy(pos)
    this.camera.lookAt(target)
    this.controls?.target.copy(target)
    this.controls?.update()
    this.requestRender()
  }

  loadUrdf(relpath: string, eeLink: string) {
    this.eeLink = eeLink
    const seq = ++this.loadSeq
    if (this.robot) {
      // keep the shared overlay helpers alive; only the robot meshes are disposed
      for (const o of [this.tcpAxes, this.com, this.gravityArrow]) o.removeFromParent()
      this.scene.remove(this.robot)
      this.disposeObject(this.robot)
      this.robot = null
    }
    let failed: string | null = null
    const manager = new THREE.LoadingManager()
    const loader = new URDFLoader(manager)
    const gltf = new GLTFLoader(manager)
    gltf.setDRACOLoader(this.draco)
    loader.loadMeshCb = (path, _m, _material, done) => {
      gltf.load(
        path,
        (g) => done(g.scene),
        undefined,
        (err) => {
          failed = path
          done(null as unknown as THREE.Object3D, err as Error)
        },
      )
    }
    let robot: URDFRobot | null = null
    manager.onLoad = () => {
      if (!robot || seq !== this.loadSeq) return
      this.robot = robot
      this.scene.add(robot)
      this.reach = Object.values(robot.joints).reduce((a, j) => a + j.position.length(), 0)
      this.resetView()
      const ee = robot.links[this.eeLink]
      if (ee) {
        ee.add(this.tcpAxes)
        ee.add(this.com)
        ee.add(this.gravityArrow)
      }
      this.requestRender()
      if (failed) this.onLoaded(false, new Error(`failed to load ${failed}`))
      else this.onLoaded(true)
    }
    manager.onError = (url) => {
      failed = url
    }
    loader.load(ASSET_BASE + relpath, (r) => {
      robot = r
    })
  }

  setJoints(names: string[], qDeg: number[]) {
    if (!this.robot) return
    names.forEach((n, i) => this.robot!.setJointValue(n, THREE.MathUtils.degToRad(qDeg[i] ?? 0)))
    this.updateGravityArrow()
    this.requestRender()
  }

  setTcp(offset: number[]) {
    this.tcpAxes.position.set(offset[0] / 1000, offset[1] / 1000, offset[2] / 1000)
    this.tcpAxes.rotation.copy(eulerXYZ(offset.slice(3, 6)))
    this.requestRender()
  }

  setPayload(massKg: number, comMm: number[]) {
    const show = massKg > 0
    this.com.visible = show
    this.gravityArrow.visible = show
    const r = 0.012 * Math.cbrt(Math.max(massKg, 0.01))
    this.com.scale.setScalar(r)
    this.com.position.set(comMm[0] / 1000, comMm[1] / 1000, comMm[2] / 1000)
    this.gravityArrow.position.copy(this.com.position)
    this.gravityArrow.setLength(Math.max(0.03, 0.02 * massKg), 0.02, 0.012)
    this.updateGravityArrow()
    this.requestRender()
  }

  setVisible(what: 'base' | 'tcp' | 'com', on: boolean) {
    const obj = what === 'base' ? this.baseAxes : what === 'tcp' ? this.tcpAxes : this.com
    obj.visible = on
    if (what === 'com') this.gravityArrow.visible = on
    this.requestRender()
  }

  private updateGravityArrow() {
    const parent = this.gravityArrow.parent
    if (!parent) return
    parent.updateWorldMatrix(true, false)
    const inv = new THREE.Quaternion()
    parent.getWorldQuaternion(inv).invert()
    this.gravityArrow.setDirection(new THREE.Vector3(0, 0, -1).applyQuaternion(inv))
  }

  requestRender() {
    if (this.renderRequested) return
    this.renderRequested = true
    requestAnimationFrame(() => {
      this.renderRequested = false
      this.controls.update()
      this.renderer.render(this.scene, this.camera)
    })
  }

  /** Screen-space insets (px) covered by floating panels; the view is centred in the free area. */
  /** Sum of joint offsets = an upper bound of the arm's reach (m). */
  private reach = 0
  private insets = { left: 0, right: 0, top: 0, bottom: 0 }
  setInsets(i: { left: number; right: number; top: number; bottom: number }) {
    this.insets = { ...i }
    this.resize()
  }

  private resize() {
    const w = this.host.clientWidth || 1
    const h = this.host.clientHeight || 1
    this.renderer.setSize(w, h, false)
    this.renderer.domElement.style.width = '100%'
    this.renderer.domElement.style.height = '100%'
    this.camera.aspect = w / h
    const { left, right, top, bottom } = this.insets
    const dx = (right - left) / 2
    const dy = (bottom - top) / 2
    if (dx || dy) this.camera.setViewOffset(w, h, dx, dy, w, h)
    else this.camera.clearViewOffset()
    this.camera.updateProjectionMatrix()
    this.requestRender()
  }

  private disposeObject(root: THREE.Object3D) {
    root.traverse((o) => {
      const m = o as THREE.Mesh
      m.geometry?.dispose()
      const mats = Array.isArray(m.material) ? m.material : m.material ? [m.material] : []
      mats.forEach((mat) => {
        Object.values(mat).forEach((v) => (v instanceof THREE.Texture ? v.dispose() : undefined))
        mat.dispose()
      })
    })
  }

  dispose() {
    this.resizeObs?.disconnect()
    this.controls.dispose()
    if (this.robot) this.disposeObject(this.robot)
    this.draco.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
