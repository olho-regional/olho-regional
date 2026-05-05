<template>
  <div class="portugal-map" ref="containerRef">
    <Transition name="tooltip">
      <div v-if="hoveredDistrict" class="portugal-map__tooltip">
        <strong>{{ hoveredDistrict }}</strong>
        <span v-if="districtCounts && districtCounts[hoveredDistrict]"> — {{ districtCounts[hoveredDistrict] }} {{ countLabel }}</span>
      </div>
    </Transition>
    <svg
      v-if="districts.length"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      class="portugal-map__svg"
    >
      <!-- Mainland districts -->
      <g>
        <path
          v-for="district in districts"
          :key="district.name"
          :d="district.path"
          class="portugal-map__district"
          :class="{ 'portugal-map__district--active': hoveredDistrict === district.name }"
          :style="districtStyle(district.name)"
          @mouseenter="hoveredDistrict = district.name"
          @mouseleave="hoveredDistrict = null"
          @click="navigateToDistrict(district.codigoine)"
        />
      </g>
      <!-- Island inset boxes -->
      <g v-for="group in islandGroups" :key="group.label">
        <rect
          :x="group.box.x"
          :y="group.box.y"
          :width="group.box.w"
          :height="group.box.h"
          class="portugal-map__inset-box"
        />
        <text
          :x="group.box.x + group.box.w / 2"
          :y="group.box.y - 0.03"
          class="portugal-map__inset-label"
        >{{ group.label }}</text>
        <g :transform="group.transform">
          <path
            v-for="island in group.islands"
            :key="island.name"
            :d="island.path"
            class="portugal-map__district portugal-map__district--island"
            :class="{ 'portugal-map__district--active': hoveredDistrict === island.name }"
            :style="districtStyle(island.name)"
            @mouseenter="hoveredDistrict = island.name"
            @mouseleave="hoveredDistrict = null"
            @click="navigateToDistrict(island.codigoine)"
          />
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
interface Feature {
  type: string
  properties: Record<string, string>
  geometry: { type: string; coordinates: [number, number][][] | [number, number][][][] }
}

interface FeatureCollection {
  type: string
  features: Feature[]
}

const props = withDefaults(defineProps<{
  districtCounts?: Record<string, number>
  geojsonUrl?: string
  labelField?: string
  countLabel?: string
  maxOverride?: number
  hue?: number
  clickable?: boolean
}>(), {
  geojsonUrl: '/portugal-distritos.json',
  labelField: 'distrito',
  countLabel: 'jornais',
  hue: 210,
  clickable: true,
})

const containerRef = ref<HTMLElement | null>(null)
const hoveredDistrict = ref<string | null>(null)
const geojson = ref<FeatureCollection | null>(null)
const router = useRouter()

function navigateToDistrict(codigoine: string) {
  if (!props.clickable) return
  router.push({ path: '/jornais', query: { distrito: codigoine } })
}

const maxCount = computed(() => {
  if (props.maxOverride) return props.maxOverride
  if (!props.districtCounts) return 1
  return Math.max(...Object.values(props.districtCounts), 1)
})

function districtStyle(name: string) {
  if (!props.districtCounts) return {}
  const count = props.districtCounts[name] || 0
  if (count === 0) return {}
  const intensity = Math.sqrt(count / maxCount.value) // sqrt scale for better contrast
  const lightness = 90 - intensity * 55 // from 90% (light) to 35% (dark)
  return { fill: `hsl(${props.hue}, 70%, ${lightness}%)` }
}

onMounted(async () => {
  const resp = await fetch(props.geojsonUrl)
  geojson.value = await resp.json()
})

// Mercator projection helpers
function projectLon(lon: number): number {
  return lon
}

function projectLat(lat: number): number {
  const latRad = (lat * Math.PI) / 180
  return -Math.log(Math.tan(Math.PI / 4 + latRad / 2)) * (180 / Math.PI)
}

function featureToPath(feature: Feature, skipRemoteIslands = false): string {
  const coords = feature.geometry.type === 'Polygon'
    ? [feature.geometry.coordinates as [number, number][][]]
    : feature.geometry.coordinates as [number, number][][][]

  let path = ''
  for (const polygon of coords) {
    for (const ring of polygon) {
      // Skip remote sub-polygons (Selvagens/Desertas) when rendering Madeira concelhos
      if (skipRemoteIslands) {
        const avgLat = ring.reduce((s, c) => s + c[1], 0) / ring.length
        if (avgLat < 32.5) continue
      }
      const points = ring.map((coord) => {
        return `${projectLon(coord[0])},${projectLat(coord[1])}`
      })
      path += `M${points.join('L')}Z `
    }
  }
  return path.trim()
}

function featureBounds(feature: Feature, skipRemoteIslands = false) {
  const coords = feature.geometry.type === 'Polygon'
    ? [feature.geometry.coordinates as [number, number][][]]
    : feature.geometry.coordinates as [number, number][][][]

  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const polygon of coords) {
    for (const ring of polygon) {
      if (skipRemoteIslands) {
        const avgLat = ring.reduce((s, c) => s + c[1], 0) / ring.length
        if (avgLat < 32.5) continue
      }
      for (const coord of ring) {
        const x = projectLon(coord[0])
        const y = projectLat(coord[1])
        minX = Math.min(minX, x)
        maxX = Math.max(maxX, x)
        minY = Math.min(minY, y)
        maxY = Math.max(maxY, y)
      }
    }
  }
  return { minX, maxX, minY, maxY }
}

// Compute bounds and paths
const mapData = computed(() => {
  if (!geojson.value?.features) return { mainland: [], islands: [], viewBox: '0 0 100 100' }

  const lf = props.labelField
  const isIsland = (f: Feature) => {
    const distrito = (f.properties['distrito'] || f.properties[lf] || '').toLowerCase()
    return distrito.startsWith('ilha') || distrito.includes('açores') || distrito.includes('madeira')
  }
  const isAzores = (f: Feature) => {
    const distrito = (f.properties['distrito'] || f.properties[lf] || '').toLowerCase()
    return (distrito.startsWith('ilha') && !distrito.includes('madeira') && !distrito.includes('porto santo')) || distrito.includes('açores')
  }

  const mainlandFeatures = geojson.value.features.filter(f => !isIsland(f))
  const islandFeatures = geojson.value.features.filter(f => isIsland(f))

  // Mainland bounds
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const feature of mainlandFeatures) {
    const b = featureBounds(feature)
    minX = Math.min(minX, b.minX)
    maxX = Math.max(maxX, b.maxX)
    minY = Math.min(minY, b.minY)
    maxY = Math.max(maxY, b.maxY)
  }

  const mainland = mainlandFeatures.map(f => ({ name: f.properties[lf] || '', codigoine: f.properties['codigoine'] || '', path: featureToPath(f) }))

  // Islands: group into Azores and Madeira, compute their own bounds for inset positioning
  const azoresFeatures = islandFeatures.filter(f => isAzores(f))
  const madeiraFeatures = islandFeatures.filter(f => !isAzores(f))

  // ViewBox with extra left space for inset boxes
  const padding = 0.1
  const w = maxX - minX
  const h = maxY - minY
  const leftExtra = 1.0 // extra space on left for island boxes
  const vbMinX = minX - w * (padding + leftExtra)
  const vbMinY = minY - h * padding
  const vbW = w * (1 + padding * 2 + leftExtra)
  const vbH = h * (1 + padding * 2)

  // Each inset box is placed to the left of the mainland, stacked vertically
  const boxX = minX - w * (leftExtra + padding * 0.3)
  const boxGap = h * 0.03
  // Azores: wide box
  const azBoxW = w * 0.95
  const azBoxH = h * 0.45
  // Madeira: smaller box
  const mdBoxW = w * 0.35
  const mdBoxH = h * 0.2

  function makeIslandInset(features: Feature[], bx: number, by: number, bw: number, bh: number, label: string, compressGaps = false, skipRemote = false) {
    if (!features.length) return null

    // For Azores: compress the large ocean gaps between island groups
    // by shifting each island so groups are closer together
    let adjustedPaths: { name: string; path: string }[]
    let ib = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity }

    if (compressGaps) {
      // Sort islands by projected X position
      const groups = features.map(f => {
        const b = featureBounds(f) // already in projected space
        const cx = (b.minX + b.maxX) / 2
        return { feature: f, bounds: b, cx }
      })
      groups.sort((a, b) => a.cx - b.cx)

      // Cluster islands into sub-groups (gap > 1 projected unit = new group)
      const islandGroups: (typeof groups)[] = []
      let currentGroup: typeof groups = []
      for (const g of groups) {
        if (currentGroup.length === 0 || g.bounds.minX - currentGroup[currentGroup.length - 1]!.bounds.maxX <= 1) {
          currentGroup.push(g)
        } else {
          islandGroups.push(currentGroup)
          currentGroup = [g]
        }
      }
      if (currentGroup.length) islandGroups.push(currentGroup)

      // Compute offset per group to compress gaps (all in projected space)
      const targetGap = 0.3
      const groupOffsets: number[] = []
      let prevGroupMaxX = -Infinity
      for (const grp of islandGroups) {
        const grpMinX = Math.min(...grp.map(g => g.bounds.minX))
        const grpMaxX = Math.max(...grp.map(g => g.bounds.maxX))
        let offset = 0
        if (prevGroupMaxX !== -Infinity) {
          offset = prevGroupMaxX + targetGap - grpMinX
        }
        groupOffsets.push(offset)
        prevGroupMaxX = grpMaxX + offset
      }

      // Map each island to its group's offset
      const offsetMap = new Map<Feature, number>()
      for (let gi = 0; gi < islandGroups.length; gi++) {
        for (const g of islandGroups[gi]!) {
          offsetMap.set(g.feature, groupOffsets[gi] ?? 0)
        }
      }

      adjustedPaths = groups.map((g) => {
        const offset = offsetMap.get(g.feature) ?? 0
        // Rebuild path: project first, then shift by offset in projected space
        const coords = g.feature.geometry.type === 'Polygon'
          ? [g.feature.geometry.coordinates as [number, number][][]]
          : g.feature.geometry.coordinates as [number, number][][][]

        let path = ''
        for (const polygon of coords) {
          for (const ring of polygon) {
            const points = ring.map(coord => {
              const x = projectLon(coord[0]) + offset
              const y = projectLat(coord[1])
              return `${x},${y}`
            })
            path += `M${points.join('L')}Z `
          }
        }

        // Update bounds with offset (bounds already projected, just add offset to X)
        ib.minX = Math.min(ib.minX, g.bounds.minX + offset)
        ib.maxX = Math.max(ib.maxX, g.bounds.maxX + offset)
        ib.minY = Math.min(ib.minY, g.bounds.minY)
        ib.maxY = Math.max(ib.maxY, g.bounds.maxY)

        return { name: g.feature.properties[lf] || '', codigoine: g.feature.properties['codigoine'] || '', path: path.trim() }
      })
    } else {
      adjustedPaths = features.map(f => ({
        name: f.properties[lf] || '',
        codigoine: f.properties['codigoine'] || '',
        path: featureToPath(f, skipRemote),
      }))
      for (const f of features) {
        const b = featureBounds(f, skipRemote)
        ib.minX = Math.min(ib.minX, b.minX)
        ib.maxX = Math.max(ib.maxX, b.maxX)
        ib.minY = Math.min(ib.minY, b.minY)
        ib.maxY = Math.max(ib.maxY, b.maxY)
      }
    }

    const iw = ib.maxX - ib.minX
    const ih = ib.maxY - ib.minY
    const innerPad = 0.05
    const scale = Math.min((bw * (1 - innerPad * 2)) / iw, (bh * (1 - innerPad * 2)) / ih)
    const cx = (ib.minX + ib.maxX) / 2
    const cy = (ib.minY + ib.maxY) / 2
    const tx = bx + bw / 2
    const ty = by + bh / 2

    return {
      label,
      box: { x: bx, y: by, w: bw, h: bh },
      transform: `translate(${tx - cx * scale}, ${ty - cy * scale}) scale(${scale})`,
      islands: adjustedPaths,
    }
  }

  const azoresBox = makeIslandInset(azoresFeatures, boxX, vbMinY + h * padding, azBoxW, azBoxH, 'Açores', true)
  const madeiraBox = makeIslandInset(madeiraFeatures, boxX, vbMinY + h * padding + azBoxH + boxGap, mdBoxW, mdBoxH, 'Madeira', false, true)

  const islandGroups = [azoresBox, madeiraBox].filter(Boolean) as NonNullable<typeof azoresBox>[]

  const viewBoxStr = `${vbMinX} ${vbMinY} ${vbW} ${vbH}`
  return { mainland, islandGroups, viewBox: viewBoxStr }
})

const districts = computed(() => mapData.value.mainland)
const islandGroups = computed(() => mapData.value.islandGroups)
const viewBox = computed(() => mapData.value.viewBox)
</script>

<style scoped lang="scss">
.portugal-map {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.portugal-map__svg {
  width: 100%;
  height: 100%;
  max-height: 70vh;
}

.portugal-map__district {
  fill: #ffffff;
  stroke: #1565C0;
  stroke-width: 0.02;
  transition: fill 0.2s ease;
  cursor: pointer;

  &:hover,
  &--active {
    fill: #90caf9;
    stroke: #0d47a1;
    stroke-width: 0.03;
  }
}

.portugal-map__inset-box {
  fill: none;
  stroke: #999;
  stroke-width: 0.01;
}

.portugal-map__inset-label {
  font-size: 0.12px;
  fill: #666;
  text-anchor: middle;
  font-weight: 500;
}

.portugal-map__tooltip {
  position: absolute;
  bottom: 20%;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 0.4rem 0.9rem;
  border-radius: 0.5rem;
  font-size: 0.85rem;
  pointer-events: none;
  white-space: nowrap;
  z-index: 10;
  strong { font-weight: 700; }
  span { font-weight: 400; opacity: 0.9; }
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.2s ease;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
}
</style>
