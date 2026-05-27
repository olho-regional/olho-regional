<template>
  <div class="story">
    <!-- Hero -->
    <section class="story__hero" @mousemove="onMouseMove">
      <canvas ref="canvasRef" class="story__hero-canvas" />
      <div class="story__hero-content">
        <h1 class="story__title">Olh'ó Regional</h1>
        <p class="story__subtitle">Um projeto de análise do jornalismo local em Portugal</p>
      </div>
      <div class="story__scroll-hint" :class="{ 'story__scroll-hint--hidden': scrollHintHidden }">
        <span>scroll para descobrir</span>
        <div class="story__chevron" />
      </div>
    </section>

    <!-- Intro paragraph -->
    <section class="story__intro" ref="introRef">
      <p class="story__intro-text">
        Este projeto parte de uma curiosidade em compreender a realidade do jornalismo local em Portugal.
        Para isso, procurámos os jornais com presença online quer ainda ativos, quer já extintos e auxiliámo-nos do
        <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a> para aceder ao seu conteúdo histórico. Criámos uma
        forma de extrair as suas notícias, aplicámos técnicas de análise de texto e visualização de dados, e construímos
        esta plataforma para partilhar os resultados e permitir a outros satisfazer essa mesma curiosidade.
      </p>
      <div class="story__continue-hint" :class="{ 'story__continue-hint--hidden': !showContinueHint }">
        <span>continuar para baixo</span>
        <div class="story__chevron" />
      </div>
    </section>

    <!-- ═══ SCROLL STORY 1: Identificação ═══ -->
    <section class="scroll-story" ref="scrollStory1Ref">
      <div class="scroll-story__viz" ref="viz1Ref">
        <div class="scroll-story__viz-inner">
          <!-- Phase 0-2: table -->
          <div class="viz-table" :class="{ 'viz-table--hidden': phase1 > 2 }">
            <div class="viz-table__scroll" ref="tableScrollRef">
              <table>
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Localidade</th>
                    <th>Âmbito</th>
                    <th>Suporte</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in tableRows" :key="i" :class="{
                    'viz-table__row--removed': row.hideAtPhase !== null && phase1 >= row.hideAtPhase,
                    'viz-table__row--active': row.hideAtPhase === null || phase1 < row.hideAtPhase,
                  }">
                    <td>{{ row.nome }}</td>
                    <td>{{ row.localidade }}</td>
                    <td><span class="viz-table__tag" :class="{ 'viz-table__tag--yes': row.ambito === 'Regional' }">{{
                        row.ambito }}</span></td>
                    <td><span class="viz-table__tag"
                        :class="{ 'viz-table__tag--yes': row.suporte.includes('Online') }">{{ row.suporte }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <!-- Phase 3: district map -->
          <div class="viz-map" :class="{ 'viz-map--visible': phase1 === 3 }">
            <PortugalMap :district-counts="districtCounts" :clickable="false" />
          </div>
          <!-- Phase 4: concelhos map -->
          <div class="viz-map" :class="{ 'viz-map--visible': phase1 === 4 }">
            <PortugalMap geojson-url="/portugal-concelhos.json" label-field="concelho"
              :district-counts="concelhoCounts" :clickable="false" />
          </div>
          <!-- Phase 5: active-only concelhos (desertos de notícias) -->
          <div class="viz-map" :class="{ 'viz-map--visible': phase1 === 5 }">
            <PortugalMap geojson-url="/portugal-concelhos.json" label-field="concelho"
              :district-counts="activeConcelhos" count-label="jornais ativos" :clickable="false" />
          </div>
        </div>
      </div>

      <div class="scroll-story__narrative">
        <div class="scroll-story__step" data-step="0">
          <h2 class="scroll-story__title">Identificação de Jornais Regionais</h2>
          <p class="scroll-story__text">
            Começámos por pedir à <strong>Entidade Reguladora para a Comunicação Social</strong> (<a
              href="https://portaltransparencia.erc.pt/ocs/" target="_blank">ERC</a>) a lista completa de publicações
            periódicas registadas em Portugal — ativas e inativas — entre 2000 e 2026.
          </p>
          <p class="scroll-story__text">
            O portal de transparência da ERC apenas disponibiliza os Órgãos de Comunicação Social (OCS) atualmente ativos. Para obter o histórico
            completo, foi necessário um pedido formal de dados. Aqui manifestamos a nossa gratidão à expediente
            colaboração da ERC.
          </p>
          <div class="scroll-story__stat">
            <span class="scroll-story__stat-num">4679</span>
            <span class="scroll-story__stat-label">registos recebidos da ERC</span>
          </div>
        </div>

        <div class="scroll-story__step" data-step="1">
          <h2 class="scroll-story__title">Filtragem por metadados</h2>
          <p class="scroll-story__text">
            Os dados da ERC incluem campos como âmbito geográfico, tipo de publicação e suporte. Usámos esses metadados
            para uma primeira filtragem automática:
          </p>
          <ul class="scroll-story__list">
            <li>Excluindo publicações de âmbito <strong>não regional</strong></li>
            <li>Incluindo apenas publicações com <strong>presença online</strong> verificável</li>
          </ul>
          <div class="scroll-story__stat">
            <span class="scroll-story__stat-num">4679</span>
            <span class="scroll-story__stat-arrow">→</span>
            <span class="scroll-story__stat-num">1357</span>
            <span class="scroll-story__stat-label">regionais</span>
            <span class="scroll-story__stat-arrow">→</span>
            <span class="scroll-story__stat-num">663</span>
            <span class="scroll-story__stat-label">online</span>
          </div>
        </div>

        <div class="scroll-story__step" data-step="2">
          <h2 class="scroll-story__title">Filtragem manual</h2>
          <p class="scroll-story__text">
            Cada uma das 663 publicações restantes foi verificada individualmente, sob os mesmos critérios.
            Complementámos esta lista com o trabalho prévio do projeto <a href="https://memoriaimprensa.wordpress.com/"
              target="_blank">Memória da Imprensa Portuguesa</a> que contém entradas de jornais declarados como
            <strong>Imprensa</strong> escrita com uma presença online não comunicada à ERC.
          </p>
          <div class="scroll-story__stat">
            <span class="scroll-story__stat-num">663</span>
            <span class="scroll-story__stat-arrow">→</span>
            <span class="scroll-story__stat-num">462</span>
            <span class="scroll-story__stat-label">ERC</span>
            <span class="scroll-story__stat-arrow">→</span>
            <span class="scroll-story__stat-num">573</span>
            <span class="scroll-story__stat-label">final</span>
          </div>
          <p class="scroll-story__text">
            <br />
            Ainda assim, reconhecemos que a esta lista faltarão OCSs com presença online não comunicada à ERC, que só
            uma revisão manual futura irá colmatar.
          </p>
        </div>

        <div class="scroll-story__step" data-step="3">
          <h2 class="scroll-story__title">Cobertura geográfica</h2>
          <p class="scroll-story__text">
            Para cada jornal que passou os filtros, identificámos manualmente a ou as regiões que cobre.
            Esta cobertura é <strong>distinta da localização da sede</strong>: um jornal sediado em Lisboa pode cobrir a
            região do Alentejo, por exemplo.
          </p>
          <p class="scroll-story__text">
            O mapa mostra a densidade de publicações regionais por distrito — quanto mais escuro, mais jornais cobrem
            essa região.
          </p>
        </div>

        <div class="scroll-story__step" data-step="4">
          <h2 class="scroll-story__title">Granularidade municipal</h2>
          <p class="scroll-story__text">
            Para além do distrito, mapeámos a cobertura ao nível do <strong>município</strong>, incluindo jornais ativos
            e inativos. Com 308 municípios em Portugal, esta granularidade permite análises muito mais finas.
          </p>
        </div>

        <div class="scroll-story__step" data-step="5" style="margin-bottom:6rem;;">
          <h2 class="scroll-story__title">Desertos de notícias</h2>
          <p class="scroll-story__text">
            Se considerarmos apenas os jornais online <strong>atualmente ativos</strong>, surgem <strong>{{ desertCount
              }}</strong> municípios sem qualquer cobertura, conhecidos por desertos de notícias. Aqui faltam os jornais identificados como Imprensa que possam ter presença online não declarada à ERC.
          </p>
        </div>
      </div>
    </section>

    <!-- ═══ SCROLL STORY 2: Pipeline (Recolha + Análise) ═══ -->
    <section class="scroll-story scroll-story--alt" ref="scrollStory2Ref">
      <div class="scroll-story__viz" ref="viz2Ref">
        <div class="scroll-story__viz-inner">
          <svg class="viz-pipeline" viewBox="0 0 520 440" preserveAspectRatio="xMidYMid meet">
            <!-- Layout: Left sources centered at x=70, DB at x=220, Right tasks at x=420 -->
            <!-- Vertical center = 220; items at y=110, 185, 260, 335 -->

            <!-- ── Source node: Arquivo.pt ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Source >= 1 }">
              <g transform="translate(70, 110)">
                <rect x="-50" y="-26" width="100" height="52" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--arquivo" />
                <text y="-5" class="viz-pipeline__node-label">Arquivo.pt</text>
                <text y="11" class="viz-pipeline__node-sub">1996–2026</text>
              </g>
              <line x1="120" y1="110" x2="184" y2="172" class="viz-pipeline__edge viz-pipeline__edge--arquivo"
                marker-end="url(#arrowBlue)" />
            </g>

            <!-- ── Source node: Sites ativos ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Source >= 2 }">
              <g transform="translate(70, 185)">
                <rect x="-50" y="-26" width="100" height="52" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--live" />
                <text y="-5" class="viz-pipeline__node-label">Sites ativos</text>
                <text y="11" class="viz-pipeline__node-sub">web scraping</text>
              </g>
              <line x1="120" y1="185" x2="184" y2="185" class="viz-pipeline__edge viz-pipeline__edge--live"
                marker-end="url(#arrowGreen)" />
            </g>

            <!-- ── Source node: Wayback ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Source >= 3 }">
              <g transform="translate(70, 260)">
                <rect x="-50" y="-26" width="100" height="52" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--wayback" />
                <text y="-5" class="viz-pipeline__node-label">Wayback</text>
                <text y="11" class="viz-pipeline__node-sub">arquivo web</text>
              </g>
              <line x1="120" y1="260" x2="184" y2="198" class="viz-pipeline__edge viz-pipeline__edge--wayback"
                marker-end="url(#arrowOrange)" />
            </g>

            <!-- ── Database node (visible once all sources shown) ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2 >= 0 }">
              <g transform="translate(220, 185)">
                <ellipse cx="0" cy="-14" rx="36" ry="11" class="viz-pipeline__db-shape" />
                <path d="M-36,-14 v28 a36,11 0 0,0 72,0 v-28" class="viz-pipeline__db-shape" />
                <ellipse cx="0" cy="14" rx="36" ry="11" class="viz-pipeline__db-shape viz-pipeline__db-bottom" />
                <text y="36" class="viz-pipeline__db-label">Base de dados</text>
                <text y="49" class="viz-pipeline__db-count">~1M notícias</text>
              </g>
            </g>

            <!-- ── Task 1: Metadados (phase2Task >= 1) ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Task >= 1 }">
              <line x1="256" y1="168" x2="370" y2="90" class="viz-pipeline__edge viz-pipeline__edge--task"
                marker-end="url(#arrowTaskEnd)" :marker-start="phase2 >= 2 ? 'url(#arrowTaskStart)' : ''" />
              <g transform="translate(420, 90)">
                <rect x="-50" y="-22" width="100" height="44" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--task" />
                <text y="-3" class="viz-pipeline__node-label">Metadados</text>
                <text y="11" class="viz-pipeline__node-sub">título, data, autor</text>
              </g>
            </g>

            <!-- ── Task 2: Tópicos (phase2Task >= 2) ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Task >= 2 }">
              <line x1="256" y1="178" x2="370" y2="155" class="viz-pipeline__edge viz-pipeline__edge--task"
                marker-end="url(#arrowTaskEnd)" :marker-start="phase2 >= 2 ? 'url(#arrowTaskStart)' : ''" />
              <g transform="translate(420, 155)">
                <rect x="-50" y="-22" width="100" height="44" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--task" />
                <text y="-3" class="viz-pipeline__node-label">Tópicos</text>
                <text y="11" class="viz-pipeline__node-sub">28 categorias</text>
              </g>
            </g>

            <!-- ── Task 3: Entidades (phase2Task >= 3) ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Task >= 3 }">
              <line x1="256" y1="192" x2="370" y2="220" class="viz-pipeline__edge viz-pipeline__edge--task"
                marker-end="url(#arrowTaskEnd)" :marker-start="phase2 >= 2 ? 'url(#arrowTaskStart)' : ''" />
              <g transform="translate(420, 220)">
                <rect x="-50" y="-22" width="100" height="44" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--task" />
                <text y="-3" class="viz-pipeline__node-label">Entidades</text>
                <text y="11" class="viz-pipeline__node-sub">NER</text>
              </g>
            </g>

            <!-- ── Task 4: Género (phase2Task >= 4) ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Task >= 4 }">
              <line x1="256" y1="202" x2="370" y2="285" class="viz-pipeline__edge viz-pipeline__edge--task"
                marker-end="url(#arrowTaskEnd)" :marker-start="phase2 >= 2 ? 'url(#arrowTaskStart)' : ''" />
              <g transform="translate(420, 285)">
                <rect x="-50" y="-22" width="100" height="44" rx="10"
                  class="viz-pipeline__node viz-pipeline__node--task" />
                <text y="-3" class="viz-pipeline__node-label">Género</text>
                <text y="11" class="viz-pipeline__node-sub">citações</text>
              </g>
            </g>

            <!-- ── Step 2: Olh'ó Regional (delayed trigger) ── -->
            <g class="viz-pipeline__group" :class="{ 'viz-pipeline__group--visible': phase2Platform }">
              <!-- Arrow from DB down to Olh'ó Regional -->
              <line x1="220" y1="234" x2="220" y2="360" class="viz-pipeline__edge viz-pipeline__edge--platform"
                marker-end="url(#arrowPlatform)" />
              <g transform="translate(220, 385)">
                <rect x="-58" y="-18" width="116" height="36" rx="8"
                  class="viz-pipeline__node viz-pipeline__node--platform" />
                <text y="5" class="viz-pipeline__platform-label">Olh'ó Regional</text>
              </g>
            </g>

            <!-- Arrow markers (small) -->
            <defs>
              <marker id="arrowBlue" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto">
                <polygon points="0,0 5,2.5 0,5" fill="#1565C0" />
              </marker>
              <marker id="arrowGreen" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto">
                <polygon points="0,0 5,2.5 0,5" fill="#2e7d32" />
              </marker>
              <marker id="arrowOrange" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto">
                <polygon points="0,0 5,2.5 0,5" fill="#ff8f00" />
              </marker>
              <marker id="arrowTaskEnd" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto">
                <polygon points="0,0 5,2.5 0,5" fill="#5e35b1" />
              </marker>
              <marker id="arrowTaskStart" markerWidth="5" markerHeight="5" refX="0.5" refY="2.5" orient="auto">
                <polygon points="5,0 0,2.5 5,5" fill="#5e35b1" />
              </marker>
              <marker id="arrowPlatform" markerWidth="5" markerHeight="5" refX="4.5" refY="2.5" orient="auto">
                <polygon points="0,0 5,2.5 0,5" fill="#1565C0" />
              </marker>
            </defs>
          </svg>
        </div>
      </div>

      <div class="scroll-story__narrative">
        <div class="scroll-story__step" data-step="0" data-story="2">
          <h2 class="scroll-story__title">Recolha de notícias</h2>
          <p class="scroll-story__text">
            O <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a> preserva versões históricas de sites na Web
            Portuguesa desde a década de 1990. Com a sua API, descarregámos notícias arquivadas de cada jornal identificado, muitas
            inacessíveis de outra forma. Complementámos estes resultados com uma extração de notícias de sites ainda
            ativos e com a <a href="https://web.archive.org/" target="_blank">Wayback Machine</a> (um projeto irmão do
            Arquivo.pt gerido pelo Internet Archive).
          </p>
          <p class="scroll-story__text">
            Apesar de termos extraído mais de <strong>3 milhões de notícias</strong> destas fontes, limitámos as
            notícias nesta primeira versão a 5000 por jornal, para garantir uma representação equilibrada entre jornais
            ativos e inativos, perfazendo aproximadamente <strong>1 milhão de notícias</strong>.
          </p>
        </div>

        <div class="scroll-story__step" data-step="1" data-story="2">
          <h2 class="scroll-story__title">Processamento</h2>
          <p class="scroll-story__text">
            Cada notícia recolhida passa por várias etapas de processamento automático:
          </p>
          <ul class="scroll-story__text scroll-story__list">
            <li><strong>Extração de metadados</strong> — título, corpo da notícia, data de publicação e autor</li>
            <li><strong>Deteção de tópicos</strong> — 28 categorias temáticas identificadas com modelos automáticos e curadoria manual</li>
            <li><strong>Deteção de entidades</strong> — pessoas e organizações mencionadas nas notícias</li>
            <li><strong>Análise de género</strong> — representação de género nas fontes citadas, usando bases de nomes do Instituto dos Registos e Notariado (IRN)</li>
          </ul>
        </div>

        <div class="scroll-story__step" data-step="2" data-story="2">
          <h2 class="scroll-story__title">Resultado</h2>
          <p class="scroll-story__text">
            Toda esta investigação — identificação, recolha, processamento e análise — é disponibilizada através deste
            site: <strong class="story__brand">Olh'ó Regional</strong>. 
          </p>
          <p class="scroll-story__text">
            Todo o código subjacente a este projeto está <a href="#TODO" target="_blank">disponível no GitHub</a>, sob uma licença de código aberto. Estamos disponíveis para partilhar os dados com qualquer cidadão interessado.
          </p>
          <div class="scroll-story__cta">
            <v-btn to="/analisar" color="primary" size="large">Explorar Dados</v-btn>
            <v-btn to="/jornais" variant="outlined" size="large">Ver Jornais</v-btn>
            <v-btn to="/analises" color="secondary" variant="flat" size="large">Ver os nossos Casos de Estudo</v-btn>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

// ── Refs ──
const canvasRef = ref<HTMLCanvasElement | null>(null)
const introRef = ref<HTMLElement | null>(null)
const scrollStory1Ref = ref<HTMLElement | null>(null)
const scrollStory2Ref = ref<HTMLElement | null>(null)
const viz1Ref = ref<HTMLElement | null>(null)
const viz2Ref = ref<HTMLElement | null>(null)
const tableScrollRef = ref<HTMLElement | null>(null)

const mouse = reactive({ x: 0.5, y: 0.5 })
const phase1 = ref(0)
const phase2 = ref(-1)
const phase2Source = ref(0) // 0=none, 1=arquivo, 2=+sites, 3=+wayback (scrub animated)
const phase2Task = ref(0) // 0=none, 1=metadados, 2=tópicos, 3=entidades, 4=género (scrub animated)
const phase2Platform = ref(false) // Olh'ó Regional box visibility (delayed)
const scrollHintHidden = ref(false)
const showContinueHint = ref(false)

// ── District counts for choropleth (from DB) ──
const { data: geoCounts } = await useFetch<{ districtCounts: Record<string, number>; concelhoCounts: Record<string, number> }>('/api/jornais/geo-counts')
const districtCounts = computed(() => geoCounts.value?.districtCounts ?? {})
const concelhoCounts = computed(() => geoCounts.value?.concelhoCounts ?? {})

// ── Active-only concelhos for desertos de notícias ──
const { data: geoCountsActive } = await useFetch<{ concelhoCounts: Record<string, number> }>('/api/jornais/geo-counts-active')
const activeConcelhos = computed(() => geoCountsActive.value?.concelhoCounts ?? {})
const totalConcelhos = 308
const desertCount = computed(() => totalConcelhos - Object.keys(activeConcelhos.value).length)


// ── Sample OCS data (from erc-for-viz.csv) ──
const sampleOCS: Array<{ nome: string; regiao: string; localidade: string; ambito: string; suporte: string; hideAtPhase: number | null }> = [
  { nome: 'Forum Esine Revista', regiao: 'Lisboa', localidade: 'Amadora', ambito: 'Nacional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Região D\'Ouro - Jornal', regiao: 'Vila Real', localidade: 'Vila Real', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Noticias de Santo Estevão', regiao: 'Santarém', localidade: 'Benavente', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Oeste Online', regiao: 'Leiria', localidade: 'Caldas da Rainha', ambito: 'Nacional', suporte: 'Online', hideAtPhase: 1 },
  { nome: 'Beira Alta TV', regiao: 'Guarda', localidade: 'Celorico da Beira', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Florentinos Gentes das Flores', regiao: 'Ilha das Flores', localidade: 'Santa Cruz das Flores', ambito: 'Regional', suporte: 'Online', hideAtPhase: null },
  { nome: 'On Sempre Ligados', regiao: 'Porto', localidade: 'Matosinhos', ambito: 'Nacional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Primitiva', regiao: 'Viana do Castelo', localidade: 'Monção', ambito: 'Nacional', suporte: 'Papel/Online', hideAtPhase: 1 },
  { nome: 'Viver - Vidas e Veredas da Raia', regiao: 'Castelo Branco', localidade: 'Vila Velha de Ródão', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Edit Mag', regiao: 'Lisboa', localidade: 'Lisboa', ambito: 'Nacional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Noticias de Tábua', regiao: 'Coimbra', localidade: 'Oliveira do Hospital', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: 2 },
  { nome: 'NGL - Notícias Grande Lisboa', regiao: 'Lisboa', localidade: 'Sintra', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Região Centro', regiao: 'Leiria', localidade: 'Pombal', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Revista Network', regiao: 'Lisboa', localidade: 'Oeiras', ambito: 'Regional', suporte: 'Online', hideAtPhase: null },
  { nome: 'Jornal de Ermesinde', regiao: 'Porto', localidade: 'Gondomar', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Discurso Directo', regiao: 'Aveiro', localidade: 'Arouca', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Time Out Lisboa', regiao: 'Lisboa', localidade: 'Lisboa', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Casas & Negócios', regiao: 'Braga', localidade: 'Braga', ambito: 'Nacional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Braga TV', regiao: 'Braga', localidade: 'Braga', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Chafariz de Arruda', regiao: 'Lisboa', localidade: 'Azambuja', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'TomarTV', regiao: 'Santarém', localidade: 'Tomar', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Metrojornal', regiao: 'Coimbra', localidade: 'Miranda do Corvo', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Info-Fajãs', regiao: 'Ilha de São Jorge', localidade: 'Velas', ambito: 'Regional', suporte: 'Online', hideAtPhase: null },
  { nome: 'LOURESmagazineODIVELAS', regiao: 'Lisboa', localidade: 'Odivelas', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Semanário V', regiao: 'Braga', localidade: 'Braga', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Correio de Amarante', regiao: 'Porto', localidade: 'Amarante', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'NovoPerfil', regiao: 'Lisboa', localidade: 'Lisboa', ambito: 'Nacional', suporte: 'Papel/Online', hideAtPhase: 1 },
  { nome: 'Mafra Regional', regiao: 'Lisboa', localidade: 'Mafra', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Gazeta Rural', regiao: 'Viseu', localidade: 'Viseu', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Notícias de Albergaria', regiao: 'Aveiro', localidade: 'Águeda', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Your Vip Partner', regiao: 'Lisboa', localidade: 'Cascais', ambito: 'Nacional', suporte: 'Online', hideAtPhase: 1 },
  { nome: 'Trendy Report', regiao: 'Lisboa', localidade: 'Lisboa', ambito: 'Nacional', suporte: 'Online', hideAtPhase: 1 },
  { nome: 'Viseu Global', regiao: 'Viseu', localidade: 'Viseu', ambito: 'Regional', suporte: 'Online', hideAtPhase: null },
  { nome: 'Mundo Açoriano', regiao: 'R.A. Açores', localidade: 'Ribeira Grande', ambito: 'Regional', suporte: 'Online', hideAtPhase: 2 },
  { nome: 'Agreste Magazine', regiao: 'Lisboa', localidade: 'Sobral de Monte Agraço', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Mais Alerta Jornal', regiao: 'Aveiro', localidade: 'Oliveira de Azeméis', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Jornal de Tauromaquia', regiao: 'Santarém', localidade: 'Cartaxo', ambito: 'Nacional', suporte: 'Papel/Online', hideAtPhase: 1 },
  { nome: 'Jornal O Vilaverdense', regiao: 'Braga', localidade: 'Vila Verde', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Zen Energy', regiao: 'Lisboa', localidade: 'Lisboa', ambito: 'Nacional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Notícias Maia', regiao: 'Porto', localidade: 'Maia', ambito: 'Regional', suporte: 'Online', hideAtPhase: null },
  { nome: 'Montejunto Online', regiao: 'Lisboa', localidade: 'Cadaval', ambito: 'Nacional', suporte: 'Papel/Online', hideAtPhase: 1 },
  { nome: 'Mapfre Magazine', regiao: 'Lisboa', localidade: 'Amadora', ambito: 'Nacional', suporte: 'Papel/Online', hideAtPhase: 1 },
  { nome: 'VTV - Viseu TV', regiao: 'Viseu', localidade: 'Viseu', ambito: 'Nacional', suporte: 'Online', hideAtPhase: 1 },
  { nome: 'Eduser: Rev. de Educação', regiao: 'Bragança', localidade: 'Bragança', ambito: 'Nacional', suporte: 'Online', hideAtPhase: 1 },
  { nome: 'Notícias de Valença', regiao: 'Porto', localidade: 'Matosinhos', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Jornal Lezirias', regiao: 'Santarém', localidade: 'Coruche', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'Sineense', regiao: 'Setúbal', localidade: 'Sines', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
  { nome: 'Barcelos na Hora', regiao: 'Braga', localidade: 'Barcelos', ambito: 'Regional', suporte: 'Online', hideAtPhase: null },
  { nome: 'Voz de Argoncilhe', regiao: 'Aveiro', localidade: 'Santa Maria da Feira', ambito: 'Regional', suporte: 'Papel', hideAtPhase: 1 },
  { nome: 'YES Notícias', regiao: 'Porto', localidade: 'Lousada', ambito: 'Regional', suporte: 'Papel/Online', hideAtPhase: null },
]

const tableRows = computed(() => sampleOCS)

// ──────────────────────────────────────────────
// CANVAS (hero background – floating jornal names)
// ──────────────────────────────────────────────
function onMouseMove(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  mouse.x = (e.clientX - rect.left) / rect.width
  mouse.y = (e.clientY - rect.top) / rect.height
}

// Fetch real names from DB (cached server-side)
const { data: jornalNames } = await useFetch<string[]>('/api/jornais/names')

interface FloatingName {
  text: string; x: number; y: number; vx: number; vy: number; speed: number
  fontSize: number; baseOpacity: number; parallax: number; layer: number
  homeX: number; homeY: number; textW: number
}

const floatingNames: FloatingName[] = []
const GLOW_RADIUS = 0.15 // normalized distance for full glow effect
const GRAVITY_RADIUS = 0.12 // pull range
const GRAVITY_STRENGTH = 0 // disabled
const DAMPING = 0.92 // velocity decay
const ROW_PAD = 0.03 // normalized vertical gap between rows

function initFloatingNames() {
  floatingNames.length = 0
  const names = jornalNames.value ?? []
  if (!names.length) return
  const shuffled = [...names].sort(() => Math.random() - 0.5)
  const count = 75

  // Distribute into 3 layers, stagger vertically per layer
  const perLayer = Math.ceil(count / 3)
  for (let i = 0; i < count; i++) {
    const layer = i % 3
    const indexInLayer = Math.floor(i / 3)
    const baseSize = layer === 0 ? 11 : layer === 1 ? 15 : 20
    const fontSize = baseSize + Math.random() * 5
    // Estimate text width in normalized coords (~0.6 of fontSize * charCount / canvasWidth)
    const charW = fontSize * 0.55
    const textW = (shuffled[i % shuffled.length]!.length * charW) / 1200 // rough norm for ~1200px wide canvas

    // Spread rows evenly across 0..1+extra so they wrap continuously
    const rowH = ROW_PAD + fontSize / 800
    const y = (indexInLayer * rowH) % 1.3 + Math.random() * 0.01
    const x = 0.02 + Math.random() * (0.96 - textW)

    floatingNames.push({
      text: shuffled[i % shuffled.length]!,
      x, y, homeX: x, homeY: y,
      vx: 0, vy: 0,
      speed: 0.006 + layer * 0.005 + Math.random() * 0.003,
      fontSize,
      textW,
      baseOpacity: layer === 0 ? 0.03 : layer === 1 ? 0.05 : 0.07,
      parallax: 0.01 + layer * 0.02,
      layer,
    })
  }
}

function separateNames() {
  // Only separate within same layer
  for (let layer = 0; layer < 3; layer++) {
    const layerNames = floatingNames.filter(n => n.layer === layer)
    for (let i = 0; i < layerNames.length; i++) {
      const a = layerNames[i]!
      for (let j = i + 1; j < layerNames.length; j++) {
        const b = layerNames[j]!
        const dy = a.homeY - b.homeY
        const minH = (a.fontSize + b.fontSize) / 2 / 800 + 0.005
        if (Math.abs(dy) >= minH) continue
        // Check horizontal overlap
        const aRight = a.homeX + a.textW
        const bRight = b.homeX + b.textW
        if (a.homeX > bRight || b.homeX > aRight) continue
        // Push apart vertically
        const push = (minH - Math.abs(dy)) * 0.5
        if (dy >= 0) { a.homeY += push; b.homeY -= push }
        else { a.homeY -= push; b.homeY += push }
        a.y = a.homeY; b.y = b.homeY
      }
    }
  }
}

function drawFloatingNames(ctx: CanvasRenderingContext2D, w: number, h: number) {
  separateNames()

  for (const n of floatingNames) {
    // Gravitational pull toward cursor
    const dx = mouse.x - n.x
    const dy = mouse.y - n.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist < GRAVITY_RADIUS && dist > 0.001) {
      const force = GRAVITY_STRENGTH * (1 - dist / GRAVITY_RADIUS)
      n.vx += (dx / dist) * force
      n.vy += (dy / dist) * force
    }

    // Spring back toward home position (gentle)
    n.vx += (n.homeX - n.x) * 0.0003
    n.vy += (n.homeY - n.y) * 0.0003

    // Apply velocity with damping
    n.vx *= DAMPING
    n.vy *= DAMPING
    n.x += n.vx
    n.y += n.vy

    // Parallax offset for rendering
    const ox = (mouse.x - 0.5) * n.parallax * w
    const oy = (mouse.y - 0.5) * n.parallax * h
    const cx = n.x * w + ox
    const cy = n.y * h + oy

    // Glow based on proximity
    const proximity = Math.max(0, 1 - dist / GLOW_RADIUS)
    const glow = proximity * proximity

    // Opacity: base + glow boost
    const opacity = n.baseOpacity + glow * (0.35 - n.baseOpacity)

    // Color shifts from dark grey to primary blue when near cursor
    const r = Math.round(26 * (1 - glow) + 21 * glow)
    const g = Math.round(26 * (1 - glow) + 101 * glow)
    const b = Math.round(26 * (1 - glow) + 192 * glow)

    ctx.save()
    ctx.globalAlpha = opacity
    ctx.fillStyle = `rgb(${r},${g},${b})`
    ctx.font = `600 ${n.fontSize}px "Playfair Display", Georgia, "Times New Roman", serif`
    ctx.textBaseline = 'middle'
    ctx.fillText(n.text, cx, cy)
    ctx.restore()

    // Scroll upward, wrap around (applied to home position so gravity doesn't fight it)
    n.homeY -= n.speed * 0.01
    if (n.homeY < -0.05) {
      n.homeY = 1.05
      n.homeX = Math.random()
      n.x = n.homeX
      n.y = n.homeY
      n.vx = 0
      n.vy = 0
    }
  }
}

let animId: number
function animate() {
  const c = canvasRef.value; if (!c) return
  const ctx = c.getContext('2d'); if (!ctx) return
  ctx.clearRect(0, 0, c.width, c.height)
  const dpr = window.devicePixelRatio
  drawFloatingNames(ctx, c.width / dpr, c.height / dpr)
  animId = requestAnimationFrame(animate)
}

function resizeCanvas() {
  const c = canvasRef.value; if (!c) return
  c.width = c.offsetWidth * window.devicePixelRatio
  c.height = c.offsetHeight * window.devicePixelRatio
  const ctx = c.getContext('2d')
  if (ctx) ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
}

// ──────────────────────────────────────────────
// AUTO-SCROLL TABLE
// ──────────────────────────────────────────────
let tableScrollTween: gsap.core.Tween | null = null

function startTableScroll() {
  const el = tableScrollRef.value
  if (!el) return
  const scrollHeight = el.scrollHeight - el.clientHeight
  if (scrollHeight <= 0) return
  el.scrollTop = 0
  tableScrollTween = gsap.to(el, {
    scrollTop: scrollHeight,
    duration: scrollHeight / 30,
    ease: 'none',
    repeat: -1,
    yoyo: true,
  })
}

function stopTableScroll() {
  if (tableScrollTween) { tableScrollTween.kill(); tableScrollTween = null }
}

// ──────────────────────────────────────────────
// SCROLL TRIGGERS
// ──────────────────────────────────────────────
function setupStoryTriggers(container: HTMLElement, phaseRef: ReturnType<typeof ref<number>>) {
  const steps = Array.from(container.querySelectorAll('.scroll-story__step'))

  // Determine correct initial phase from current scroll position FIRST
  let initialPhase = 0
  for (const step of steps) {
    const rect = step.getBoundingClientRect()
    const stepNum = parseInt((step as HTMLElement).dataset.step || '0')
    if (rect.top < window.innerHeight * 0.6) {
      initialPhase = stepNum
    }
  }
  phaseRef.value = initialPhase

  // Guard: ignore ScrollTrigger callbacks during first refresh to avoid race conditions
  let initialized = false
  requestAnimationFrame(() => { initialized = true })

  // Now create triggers — they won't override the initial phase due to the guard
  steps.forEach((step) => {
    const stepNum = parseInt((step as HTMLElement).dataset.step || '0')
    ScrollTrigger.create({
      trigger: step,
      start: 'top 60%',
      end: 'bottom 40%',
      onEnter: () => { if (initialized) phaseRef.value = stepNum },
      onEnterBack: () => { if (initialized) phaseRef.value = stepNum },
    })
  })
  steps.forEach((step) => {
    gsap.fromTo(step,
      { opacity: 0, y: 40 },
      {
        opacity: 1, y: 0, duration: 0.6, ease: 'power2.out',
        scrollTrigger: { trigger: step, start: 'top 85%', end: 'top 55%', toggleActions: 'play none none reverse' }
      },
    )
  })
}

function setupScrollAnimations() {
  if (scrollStory1Ref.value) setupStoryTriggers(scrollStory1Ref.value, phase1)
  if (scrollStory2Ref.value) {
    setupStoryTriggers(scrollStory2Ref.value, phase2)

    // Scrub: animate source nodes appearing during step 0
    const step0 = scrollStory2Ref.value.querySelector('[data-step="0"][data-story="2"]')
    if (step0) {
      ScrollTrigger.create({
        trigger: step0,
        start: 'top 80%',
        end: 'bottom 50%',
        scrub: true,
        onUpdate: (self) => {
          const p = self.progress
          if (p < 0.33) phase2Source.value = 1
          else if (p < 0.66) phase2Source.value = 2
          else phase2Source.value = 3
        },
      })
    }

    // Once step 1 enters, ensure all sources are fully visible
    watch(phase2, (p) => {
      if (p >= 1) phase2Source.value = 3
      if (p < 1) phase2Task.value = 0
    })

    // Scrub: animate task nodes appearing during step 1
    const step1 = scrollStory2Ref.value.querySelector('[data-step="1"][data-story="2"]')
    if (step1) {
      ScrollTrigger.create({
        trigger: step1,
        start: 'top 80%',
        end: 'bottom 50%',
        scrub: true,
        onUpdate: (self) => {
          const p = self.progress
          if (p <= 0.01) phase2Task.value = 0
          else if (p < 0.2) phase2Task.value = 1
          else if (p < 0.4) phase2Task.value = 2
          else if (p < 0.6) phase2Task.value = 3
          else phase2Task.value = 4
        },
        onLeaveBack: () => { phase2Task.value = 0 },
      })
    }

    // Once step 2 enters, ensure all tasks are fully visible
    watch(phase2, (p) => { if (p >= 2) phase2Task.value = 4 })

    // Delayed trigger for Olh'ó Regional platform box (center of viewport)
    const step2 = scrollStory2Ref.value.querySelector('[data-step="2"][data-story="2"]')
    if (step2) {
      ScrollTrigger.create({
        trigger: step2,
        start: 'top 40%',
        onEnter: () => { phase2Platform.value = true },
        onLeaveBack: () => { phase2Platform.value = false },
      })
    }
  }

  // Auto-scroll table during phases 0-2 (table is visible)
  watch(phase1, (p) => { p <= 2 ? startTableScroll() : stopTableScroll() })
}

// ──────────────────────────────────────────────
// LIFECYCLE
// ──────────────────────────────────────────────
// ──────────────────────────────────────────────
// ARROW KEY SECTION NAVIGATION
// ──────────────────────────────────────────────
function getSections(): HTMLElement[] {
  const story = canvasRef.value?.closest('.story')
  if (!story) return []
  const targets: HTMLElement[] = []
  for (const section of Array.from(story.querySelectorAll(':scope > section')) as HTMLElement[]) {
    const steps = section.querySelectorAll('.scroll-story__step')
    if (steps.length) {
      targets.push(...(Array.from(steps) as HTMLElement[]))
    } else {
      targets.push(section)
    }
  }
  return targets
}

function getCurrentSectionIndex(sections: HTMLElement[]): number {
  const scrollY = window.scrollY + window.innerHeight * 0.3
  let current = 0
  for (let i = 0; i < sections.length; i++) {
    if (sections[i]!.offsetTop <= scrollY) current = i
  }
  return current
}

function onKeydownNav(e: KeyboardEvent) {
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
  // Don't hijack when user is in an input/textarea
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

  const sections = getSections()
  if (!sections.length) return

  const current = getCurrentSectionIndex(sections)
  let target: number

  if (e.key === 'ArrowRight') {
    target = Math.min(current + 1, sections.length - 1)
  } else {
    target = Math.max(current - 1, 0)
  }

  if (target !== current) {
    e.preventDefault()
    const el = sections[target]!
    const isLast = target === sections.length - 1
    el.scrollIntoView({ behavior: 'smooth', block: isLast ? 'center' : 'start' })
  }
}

let introObserver: IntersectionObserver | null = null
let continueHintObserver: IntersectionObserver | null = null
let continueHintTimer: ReturnType<typeof setTimeout> | null = null
let continueHintScrollHandler: (() => void) | null = null

onMounted(() => {
  initFloatingNames(); resizeCanvas(); animate()
  window.addEventListener('resize', resizeCanvas)
  window.addEventListener('keydown', onKeydownNav)
  nextTick(() => {
    setupScrollAnimations()
    startTableScroll()
  })

  // Hide scroll hint when intro paragraph is 50% visible
  if (introRef.value) {
    introObserver = new IntersectionObserver(
      ([entry]) => { scrollHintHidden.value = (entry?.isIntersecting ?? false) },
      { threshold: 0.5 },
    )
    introObserver.observe(introRef.value)
  }

  // Show "continuar para baixo" hint when user is in the intro and table is not 20% visible
  if (scrollStory1Ref.value) {
    let tableVisible = false
    continueHintObserver = new IntersectionObserver(
      ([entry]) => {
        tableVisible = entry?.isIntersecting ?? false
        if (tableVisible) {
          showContinueHint.value = false
          if (continueHintTimer) { clearTimeout(continueHintTimer); continueHintTimer = null }
        }
      },
      { threshold: 0.2 },
    )
    continueHintObserver.observe(scrollStory1Ref.value)

    // Show hint after user is idle for 2s in the intro area
    let lastScroll = Date.now()
    const checkIdle = () => {
      if (tableVisible) return
      const introEl = introRef.value
      if (!introEl) return
      const rect = introEl.getBoundingClientRect()
      const inIntro = rect.top < window.innerHeight && rect.bottom > 0
      if (inIntro && Date.now() - lastScroll > 2000) {
        showContinueHint.value = true
      }
    }
    const onScrollContinue = () => {
      lastScroll = Date.now()
      showContinueHint.value = false
    }
    window.addEventListener('scroll', onScrollContinue, { passive: true })
    continueHintTimer = setInterval(checkIdle, 500) as unknown as ReturnType<typeof setTimeout>
    continueHintScrollHandler = onScrollContinue
  }
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  stopTableScroll()
  window.removeEventListener('resize', resizeCanvas)
  window.removeEventListener('keydown', onKeydownNav)
  ScrollTrigger.getAll().forEach(t => t.kill())
  introObserver?.disconnect()
  continueHintObserver?.disconnect()
  if (continueHintTimer) clearInterval(continueHintTimer as unknown as number)
  if (continueHintScrollHandler) {
    window.removeEventListener('scroll', continueHintScrollHandler)
    continueHintScrollHandler = null
  }
})
</script>

<style scoped lang="scss">
/* Hero */
.story__hero {
  position: relative;
  height: calc(100vh - 64px);
  height: calc(100dvh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.story__hero-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.story__hero-content {
  position: relative;
  text-align: center;
  z-index: 1;
}

.story__title {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
  font-size: clamp(2.5rem, 8vw, 5rem);
  font-weight: 900;
  letter-spacing: -0.02em;
  margin: 0;
  color: #1a1a1a;
  font-style: italic;
  text-decoration: underline;
  text-decoration-color: #1565C0;
  text-decoration-thickness: 0.06em;
  text-underline-offset: 0.15em;
}

.story__subtitle {
  font-size: clamp(1rem, 2.5vw, 1.4rem);
  color: #555;
  margin-top: 0.75rem;
  font-weight: 400;
}

.story__scroll-hint {
  position: absolute;
  bottom: 3rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  z-index: 1;
  animation: fadeInUp 1s ease 1.5s both;
  transition: opacity 0.4s ease;

  span {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #888;
    font-weight: 500;
  }
}

.story__scroll-hint--hidden {
  opacity: 0 !important;
  pointer-events: none;
}

.story__chevron {
  width: 20px;
  height: 20px;
  border-right: 2px solid #888;
  border-bottom: 2px solid #888;
  transform: rotate(45deg);
  animation: bounceDown 1.5s ease infinite;
}

/* Intro */
.story__intro {
  max-width: 840px;
  margin: 0 auto;
  padding: 16rem 2rem 22rem;

  position: relative;
}

.story__continue-hint {
  position: absolute;
  bottom: 8rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  transition: opacity 0.4s ease;
  opacity: 1;

  span {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #888;
    font-weight: 500;
  }
}

.story__continue-hint--hidden {
  opacity: 0;
  pointer-events: none;
}

.story__intro-text {
  font-size: 1.2rem;
  line-height: 1.85;
  color: #333;
  text-align: center;
}

/* ═══════════════════════════════════════════════
   SCROLL STORY (shared)
   ═══════════════════════════════════════════════ */
.scroll-story {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  padding: 0 2rem;
  max-width: 1400px;
  margin: 0 auto 4rem;
}

.scroll-story--alt {
  margin-top: 4rem;
}

.scroll-story__narrative {
  padding: 0 1rem;
  display: flex;
  flex-direction: column;
  order: -1;
}

.scroll-story__step {
  min-height: 80vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 4rem 0;
}

.scroll-story__title {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
  font-size: clamp(1.4rem, 3vw, 2rem);
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 1.2rem;
}

.scroll-story__text {
  font-size: 1.05rem;
  line-height: 1.75;
  color: #444;
  margin: 0 0 1rem;
}

.scroll-story__text--muted {
  color: #888;
  font-style: italic;
  font-size: 0.95rem;
}

.scroll-story__list {
  padding-left: 1.2rem;
  li { margin-bottom: 0.5rem; }
}

.scroll-story__list {
  margin: 0.5rem 0 1rem;
  padding-left: 1.5rem;

  li {
    font-size: 1rem;
    line-height: 1.75;
    color: #444;
    margin-bottom: 0.5rem;
  }
}

.scroll-story__stat {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-top: 1.5rem;
  flex-wrap: wrap;
}

.scroll-story__stat-num {
  font-size: 2.2rem;
  font-weight: 800;
  color: #1565C0;
}

.scroll-story__stat-arrow {
  font-size: 1.4rem;
  color: #999;
  margin: 0 0.25rem;
}

.scroll-story__stat-label {
  font-size: 0.9rem;
  color: #666;
}

.scroll-story__cta {
  margin-top: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

/* Sticky viz */
.scroll-story__viz {
  position: sticky;
  top: 80px;
  height: calc(100vh - 96px);
  align-self: start;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.scroll-story__viz-inner {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}

/* Table */
.viz-table {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  transition: opacity 0.5s ease;
  overflow: hidden;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid #e0e0e0;
}

.viz-table--hidden {
  opacity: 0;
  pointer-events: none;
}

.viz-table__scroll {
  overflow: hidden;
  flex: 1;
}

.viz-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.viz-table thead {
  position: sticky;
  top: 0;
  background: #1565C0;
  color: white;
  z-index: 1;
}

.viz-table th {
  padding: 0.6rem 0.75rem;
  text-align: left;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.viz-table td {
  padding: 0.45rem 0.75rem;
  border-bottom: 1px solid #eee;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.viz-table tbody tr {
  transition: all 0.4s ease;
}

.viz-table__row--removed {
  opacity: 0.15;
  text-decoration: line-through;
  background: #fff5f5;

  td {
    color: #999;
  }
}

.viz-table__row--active {
  background: #e8f5e9;
}

.viz-table__tag {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 500;
  background: #f5f5f5;
  color: #666;
}

.viz-table__tag--yes {
  background: #c8e6c9;
  color: #2e7d32;
  font-weight: 600;
}

/* Map */
.viz-map {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: scale(0.95);
  transition: opacity 0.6s ease, transform 0.6s ease;
  pointer-events: none;
}

.viz-map--visible {
  opacity: 1;
  transform: scale(1);
  pointer-events: auto;
}

/* Pipeline graph */
.viz-pipeline {
  width: 100%;
  height: 100%;
  max-height: 100%;
}

.viz-pipeline__group {
  opacity: 0;
  transition: opacity 0.6s ease;
}

.viz-pipeline__group--visible {
  opacity: 1;
}

.viz-pipeline__node {
  fill: #f5f5f5;
  stroke-width: 2;
}

.viz-pipeline__node--arquivo {
  stroke: #1565C0;
}

.viz-pipeline__node--live {
  stroke: #2e7d32;
}

.viz-pipeline__node--wayback {
  stroke: #ff8f00;
}

.viz-pipeline__node--task {
  stroke: #5e35b1;
  fill: #ede7f6;
}

.viz-pipeline__node--platform {
  stroke: #1565C0;
  fill: #e3f2fd;
  stroke-width: 2.5;
}

.viz-pipeline__node-label {
  text-anchor: middle;
  font-size: 11px;
  font-weight: 700;
  fill: #333;
}

.viz-pipeline__node-sub {
  text-anchor: middle;
  font-size: 8px;
  fill: #888;
}

.viz-pipeline__platform-label {
  text-anchor: middle;
  font-size: 11px;
  font-weight: 800;
  fill: #1565C0;
  font-style: italic;
  text-decoration: underline;
}

.story__brand {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
  font-style: italic;
  text-decoration: underline;
  text-decoration-color: #1565C0;
  text-decoration-thickness: 0.06em;
  text-underline-offset: 0.15em;
  letter-spacing: -0.02em;
}

.viz-pipeline__edge {
  stroke-width: 2;
  stroke-dasharray: 5 3;
  fill: none;
}

.viz-pipeline__edge--arquivo {
  stroke: #1565C0;
}

.viz-pipeline__edge--live {
  stroke: #2e7d32;
}

.viz-pipeline__edge--wayback {
  stroke: #ff8f00;
}

.viz-pipeline__edge--task {
  stroke: #5e35b1;
}

.viz-pipeline__edge--platform {
  stroke: #1565C0;
  stroke-width: 2.5;
  stroke-dasharray: none;
}

.viz-pipeline__db-shape {
  fill: #e3f2fd;
  stroke: #1565C0;
  stroke-width: 2;
}

.viz-pipeline__db-bottom {
  fill: none;
}

.viz-pipeline__db-label {
  text-anchor: middle;
  font-size: 9px;
  font-weight: 600;
  fill: #1565C0;
}

.viz-pipeline__db-count {
  text-anchor: middle;
  font-size: 8px;
  fill: #666;
}

/* Responsive */
@media (max-width: 900px) {
  .scroll-story {
    display: flex;
    flex-direction: column;
    padding: 0;
    gap: 0;
    margin-bottom: 2rem;
  }

  .scroll-story__viz {
    position: sticky;
    top: 56px;
    height: 45vh;
    z-index: 2;
    padding: 0.75rem;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    align-self: stretch;
  }

  .scroll-story__viz-inner {
    height: 100%;
  }

  .scroll-story__narrative {
    padding: 0 1.25rem;
    order: unset;
  }

  .scroll-story__step {
    min-height: auto;
    padding: 3rem 0;
  }

  .scroll-story__step:last-child {
    padding-bottom: 2rem;
  }

  .scroll-story__title {
    font-size: 1.3rem;
  }

  .scroll-story__text {
    font-size: 0.95rem;
  }

  .scroll-story__stat-num {
    font-size: 1.8rem;
  }

  .viz-table th {
    padding: 0.4rem 0.5rem;
    font-size: 0.65rem;
  }

  .viz-table td {
    padding: 0.3rem 0.5rem;
    font-size: 0.72rem;
    max-width: 100px;
  }

  .viz-map {
    padding: 0.5rem;

    :deep(.portugal-map__svg) {
      max-height: 100%;
    }
  }

  .viz-pipeline {
    padding: 0;
  }

  .story__intro {
    padding: 3rem 1.5rem 7rem;
  }

  .story__intro-text {
    font-size: 1.05rem;
  }
}

@media (max-width: 480px) {
  .scroll-story__viz {
    height: 40vh;
    top: 48px;
    padding: 0.25rem;
  }

  .story__hero {
    height: calc(100vh - 56px);
    height: calc(100dvh - 56px);
  }

  .story__title {
    font-size: 2.2rem;
  }
}

@keyframes bounceDown {

  0%,
  100% {
    margin-top: 0;
    opacity: 1;
  }

  50% {
    margin-top: 8px;
    opacity: 0.5;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes pulseGlow {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.7;
  }
}
</style>
