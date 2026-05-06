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
            1. Identificação de fontes de dados para o trabalho:<br><br>O trabalho baseia-se em dois datasets principais, os jornais e as notícias.<br>Identificou-se a Entidade Reguladora para a Comunicação Social (ERC) como a fonte primária para o dataset dos jornais.<br>Identificou-se a exposição <a href="https://memoriaimprensa.wordpress.com/" target="_blank">Memória da Imprensa Portuguesa</a> como uma fonte complementar para o dataset dos jornais.<br>Identificou-se o <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a> como a principal fonte de dados para a recolha de notícias e validação das características dos jornais.<br>Identificaram-se a <a href="https://web.archive.org/" target="_blank">wayback machine</a> e os sites dos próprios jornais que estão ativos, como fontes complementares de dados para a recolha de notícias.
          </p>
          <p class="mb-4">
            2. Recolha dos dados da ERC sobre os jornais e critérios de exclusão de meios noticiosos:<br><br>Contactou-se a ERC, que prontamente disponibilizou um dataset contendo a lista completa de publicações periódicas registadas em Portugal, ativas e inativas entre 2000 e 2026.<br>A lista contém os seguintes campos por publicação e a metodologia de exclusão de publicações seguiu os seguintes critérios:<br>Todas as publicações de âmbito não regional foram excluídas.<br>Todas as publicações sem suporte online foram excluídas.<br>Define-se neste ponto os jornais que sobreviveram aos critérios de exclusão como “jornais regionais”.<br>A aplicação destes critérios de exclusão resultou numa lista de 663 jornais regionais.<br><br>Em seguida procedeu-se a uma verificação individual de cada um dos registos no <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a> ou site ativo para validar que a publicação tem ou teve em qualquer espaço temporal, uma presença online verificável.<br>Verificou-se também o conteúdo das notícias e foram excluídos todos os registos que apresentaram um carácter diferente de notícias regionais (como desporto, doutrinário, especializado ou notícias nacionais ou internacionais).<br>A aplicação destes critérios de exclusão resultou numa lista de 462 jornais regionais.<br><br>Incrementou-se também a lista com registos provenientes do projecto Memória da Imprensa Portuguesa, o que permitiu resgatar registos que estavam declarados na lista da ERC como não tendo site online mas que acabaram por ter.<br>Procedeu-se à mesma verificação manual que no passo anterior o que permitiu fechar a lista com 573 jornais regionais.<br><br>Reconhecemos que a esta lista faltarão Órgãos de Comunicação Social com presença online não comunicada à ERC, que só uma revisão manual mais extensa poderá colmatar.
          </p>
          <p class="mb-4">
            3. Enriquecimento dos dados sobre os jornais regionais:<br><br>Identificou-se manualmente as regiões, distritos e municípios que cada jornal cobre, fazendo uso dos respectivos Estatutos Editoriais e análise das próprias notícias. Esta cobertura é distinta da localização da sede: um jornal sediado em Lisboa pode cobrir a região do Alentejo, por exemplo.
          </p>
          <p class="mb-4">
            4. Recolha das notícias dos jornais regionais<br><br>Procedeu-se a realizar um scrapping de todas as notícias em todos os jornais regionais. Os scrappers começaram por recolher todas as notícias do <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a>, e para os casos em que não foi possível, recolheram as notícias dos sites ativos e wayback machine.
          </p>
          <p class="mb-4">
            5. Processamento dos dados e categorização.<br><br>Com base no texto disponível no título e corpo das notícias, encontraram-se os temas mais comuns que formaram as categorias usadas no processo de categorização das mesmas.
          </p>
          <p class="mb-4">
            6. Apresentação e disponibilização dos dados.<br><br>Criou-se um site que funciona como plataforma de acesso aos datasets e que permite fazer exploração e análise sobre os mesmos. Disponibilizou-se também na plataforma links para acesso a todos os datasets relevantes.
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
