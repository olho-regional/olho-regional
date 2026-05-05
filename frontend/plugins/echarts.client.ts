import { use } from 'echarts/core'
import { SVGRenderer, CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, HeatmapChart, GraphChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  ToolboxComponent,
  CalendarComponent,
  VisualMapComponent,
} from 'echarts/components'

use([
  SVGRenderer,
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  HeatmapChart,
  GraphChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  ToolboxComponent,
  CalendarComponent,
  VisualMapComponent,
])

export default defineNuxtPlugin(() => {})
