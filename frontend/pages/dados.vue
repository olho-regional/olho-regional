<template>
  <v-container>
    <h1 class="text-h4 mb-6">Dados e Metodologia</h1>

    <!-- Datasets -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Conjuntos de Dados</h2>
      <v-table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>Descrição</th>
            <th>Tamanho</th>
            <th>Formato</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ds in datasets" :key="ds.name">
            <td class="font-weight-medium">{{ ds.name }}</td>
            <td>{{ ds.description }}</td>
            <td>{{ ds.size }}</td>
            <td><v-chip size="small" variant="outlined">{{ ds.format }}</v-chip></td>
            <td>
              <v-btn size="small" variant="tonal" color="primary" :href="ds.downloadUrl" prepend-icon="mdi-download">
                Download
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </section>

    <!-- Context -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Contexto / Problema a resolver</h2>
      <v-card variant="outlined">
        <v-card-text class="text-body-1">
          <p class="mb-4">
            Os autores identificaram primeiramente um problema que assola a nossa sociedade atual. O panorama noticioso nacional (e mundial) está a sofrer alterações a uma velocidade sem precedentes nos últimos anos. Nos dias correntes a principal fonte de notícias da população em geral reside na utilização de redes sociais, o que levanta preocupações a nível da credibilidade, imparcialidade e manipulação das mesmas.
          </p>
          <p class="mb-4">
            Com este panorama surge então a necessidade de encontrar maneiras “fáceis” de chegar aos meios noticiosos tradicionais, que tendencialmente perdem para as redes sociais pelo facto de estas conseguirem centralizar a atenção dos utilizadores numa única plataforma.
          </p>
          <p class="mb-4">
            Os autores identificaram também que os meios noticiosos mais afetados pela atual conjectura, são necessariamente os que têm menor financiamento e alcance - os meios noticiosos regionais.
          </p>
          <p>
            Conhecendo o projecto do <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a>, encontrou-se no concurso de 2026 a oportunidade de criar uma plataforma que agrega e facilita o acesso a estes meios regionais e que consegue dar ferramentas, pelo uso do <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a>, para quem quiser fazer descoberta de meios noticiosos regionais, de notícias e análises sobre os dados relativos às notícias regionais nas últimas 3 décadas.
          </p>
        </v-card-text>
      </v-card>
    </section>

    <!-- Objectives -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Objetivos</h2>
      <v-card variant="outlined">
        <v-card-text class="text-body-1">
          <p class="mb-4">
            Criar um catálogo de fácil acesso a meios regionais de notícias, que tenham estado activos em qualquer momento dos últimos 30 anos, que permita a descoberta e exploração de notícias.
          </p>
          <p class="mb-4">
            Fornecer funcionalidades de análise de dados com filtros por regiões, categorias, séries temporais, jornais e autores, com uso de mapas gráficos e outro tipo de visualizações que permitam ilustrar a realidade noticiosa regional em Portugal.
          </p>
          <p class="mb-4">
            Fornecer uma ferramenta de exploração de dados em contexto científico e disponibilização de datasets sobre jornais regionais e suas notícias.
          </p>
          <p>
            Fornecer funcionalidades que facilitem a arquivação de notícias ou sites no <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a>, que ainda não se encontrem lá.
          </p>
        </v-card-text>
      </v-card>
    </section>
    
    <!-- Methodology -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Metodologia</h2>
      <v-card variant="outlined">
        <v-card-text class="text-body-1">
          <p class="mb-4">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
          </p>
          <p class="mb-4">
            Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.
          </p>
          <p class="mb-4">
            Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem.
          </p>
          <p>
            Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur, vel illum qui dolorem eum fugiat quo voluptas nulla pariatur?
          </p>
        </v-card-text>
      </v-card>
    </section>

    <!-- Code & License -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Código</h2>
      <v-card variant="outlined">
        <v-card-text>
          <p class="text-body-1 mb-4">
            Todo o código deste projeto é open-source e está disponível no GitHub. O projeto inclui ferramentas de scraping, processamento de dados, análise de tópicos (topic modelling) e esta aplicação web.
          </p>
          <v-btn
            href="https://github.com/msramalho/olho-regional"
            target="_blank"
            color="primary"
            variant="tonal"
            prepend-icon="mdi-github"
            class="mb-4"
          >
            Ver no GitHub
          </v-btn>
          <v-divider class="my-4" />
          <h3 class="text-h6 mb-2">Licença</h3>
          <p class="text-body-2">
            Este projeto está licenciado sob a <strong>MIT License</strong>. Podes usar, copiar, modificar e distribuir o código livremente, desde que mantenhas a atribuição original. Os dados recolhidos estão sujeitos aos termos de uso das fontes originais.
          </p>
        </v-card-text>
      </v-card>
    </section>

    <!-- Authors -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Autores</h2>
      <p class="text-body-1">João Carvalho e Miguel Ramalho<br/> que numa tainada soalheira esboçaram este projeto</p>
    </section>
  </v-container>
</template>

<script setup lang="ts">
const datasets = [
  {
    name: 'Artigos Completos',
    description: 'Todos os artigos recolhidos com texto completo, metadados e classificação de tópicos.',
    size: '2.3 GB',
    format: 'JSON',
    downloadUrl: '#',
  },
  {
    name: 'Metadados de Artigos',
    description: 'Apenas metadados (título, data, autor, secção, URL) sem texto completo.',
    size: '340 MB',
    format: 'CSV',
    downloadUrl: '#',
  },
  {
    name: 'Catálogo de Jornais',
    description: 'Lista de todos os jornais regionais identificados com informações de contacto e região.',
    size: '245 KB',
    format: 'CSV',
    downloadUrl: '#',
  },
  {
    name: 'Classificação de Tópicos',
    description: 'Resultados do topic modelling com probabilidades por artigo e por tópico.',
    size: '890 MB',
    format: 'Parquet',
    downloadUrl: '#',
  },
  {
    name: 'Séries Temporais',
    description: 'Agregações temporais de publicação por jornal, distrito e categoria.',
    size: '12 MB',
    format: 'CSV',
    downloadUrl: '#',
  },
]


</script>
