<template>
  <v-container>
    <h1 class="text-h4 mb-6">Dados e Curiosidades</h1>
    <p class="mb-4">
      Nesta página encontram-se mais detalhes sobre o projeto, e links para acesso aos nossos dados completos.<br />
    </p>

    <!-- Datasets -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Conjuntos de Dados</h2>
    <p class="mb-4">
      Alguns ficheiros são demasiado grandes para estarem disponíveis para download público direto, mas podem ser
      pedidos através do formulário indicado.
    </p>
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
              <v-btn v-if="ds.downloadUrl" size="small" variant="tonal" color="primary" :href="ds.downloadUrl"
                prepend-icon="mdi-download">
                Download
              </v-btn>
              <v-btn v-else-if="ds.requestUrl" size="small" variant="tonal" color="information" :href="ds.requestUrl"
                target="_blank" prepend-icon="mdi-link">
                Pedir acesso
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
            Os autores identificaram primeiramente um problema que assola a nossa sociedade atual. O panorama noticioso
            nacional (e mundial) está a sofrer alterações a uma velocidade sem precedentes nos últimos anos. Nos dias
            correntes a principal fonte de notícias da população em geral reside na utilização de redes sociais, o que
            levanta preocupações a nível da credibilidade, imparcialidade e manipulação das mesmas.
          </p>
          <p class="mb-4">
            Com este panorama surge então a necessidade de encontrar maneiras “fáceis” de chegar aos meios noticiosos
            tradicionais, que tendencialmente perdem para as redes sociais pelo facto de estas conseguirem centralizar a
            atenção dos utilizadores numa única plataforma.
          </p>
          <p class="mb-4">
            Os autores identificaram também que os meios noticiosos mais afetados pela atual conjectura, são
            necessariamente os que têm menor financiamento e alcance - os meios noticiosos regionais.
          </p>
          <p>
            Conhecendo o projecto do <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a>, encontrou-se no
            concurso de 2026 a oportunidade de criar uma plataforma que agrega e facilita o acesso a estes meios
            regionais e que consegue dar ferramentas, pelo uso do <a href="https://arquivo.pt/"
              target="_blank">Arquivo.pt</a>, para quem quiser fazer descoberta de meios noticiosos regionais, de
            notícias e análises sobre os dados relativos às notícias regionais nas últimas 3 décadas.
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
            Implementar e disponibilizar publicamente um processo automatizado de recolha e extração de notícias em
            larga escala, a partir do Arquivo.pt.
          </p>
          <p class="mb-4">
            Compilar, enriquecer e partilhar uma base de dados de jornais e notícias regionais em Portugal dos últimos
            30 anos.
          </p>
          <p class="mb-4">
            Facilitar um interface de pesquisa e análise sobre a base de dados construída.
          </p>
          <p class="mb-4">
            Apresentar casos de estudo que incidam sobre os dados recolhidos e que sirvam de inspiração à reutilização e
            maior adoção do projeto por cidadãos e académicos.
          </p>
          <p class="mb-4">
            Permitir a preservação de notícias regionais no Arquivo.pt, que ainda não se encontrem lá.
          </p>
        </v-card-text>
      </v-card>
    </section>

    <!-- Methodology -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Metodologia</h2>
      <v-card variant="outlined">
        <v-card-text class="text-body-1">
          <h4>1. Identificação de fontes de dados para o trabalho</h4>
          <p class="mb-4">O trabalho baseia-se em dois datasets principais, os jornais e as notícias.<br>Identificou-se
            a Entidade Reguladora para a Comunicação Social (ERC) como a fonte primária para o dataset dos
            jornais.<br>Identificou-se a exposição <a href="https://memoriaimprensa.wordpress.com/"
              target="_blank">Memória da Imprensa Portuguesa</a> como uma fonte complementar para o dataset dos
            jornais.<br>Identificou-se o <a href="https://arquivo.pt/" target="_blank">Arquivo.pt</a> como a principal
            fonte de dados para a recolha de notícias e validação das características dos jornais.<br>Identificaram-se a
            <a href="https://web.archive.org/" target="_blank">wayback machine</a> e os sites dos próprios jornais que
            estão ativos, como fontes complementares de dados para a recolha de notícias.
          </p>
          <h4>2. Recolha dos dados da ERC sobre os jornais e critérios de exclusão de meios noticiosos</h4>
          <p class="mb-4">
            Contactou-se a ERC, que prontamente disponibilizou um dataset contendo a lista completa de publicações
            periódicas registadas em Portugal, ativas e inativas entre 2000 e 2026.<br>A lista contém os seguintes
            campos por publicação e a metodologia de exclusão de publicações seguiu os seguintes critérios:<br>Todas as
            publicações de âmbito não regional foram excluídas.<br>Todas as publicações sem suporte online foram
            excluídas.<br>Todas as publicações de informação especializada foram excluídas.<br>Define-se neste ponto
            os jornais que sobreviveram aos critérios de exclusão como “jornais regionais”.<br>A aplicação destes
            critérios de exclusão resultou numa lista de 663 jornais regionais.<br><br>Em seguida procedeu-se a uma
            verificação individual de cada um dos registos no <a href="https://arquivo.pt/"
              target="_blank">Arquivo.pt</a> ou site ativo para validar que a publicação tem ou teve em qualquer espaço
            temporal, uma presença online verificável.<br>Verificou-se também o conteúdo das notícias e foram excluídos
            todos os registos que apresentaram um carácter diferente de notícias regionais (como desporto, doutrinário,
            especializado ou notícias nacionais ou internacionais).<br>A aplicação destes critérios de exclusão resultou
            numa lista de 462 jornais regionais.<br><br>Incrementou-se também a lista com registos provenientes do
            projecto Memória da Imprensa Portuguesa, o que permitiu resgatar registos que estavam declarados na lista da
            ERC como não tendo site online mas que acabaram por ter.<br>Procedeu-se à mesma verificação manual que no
            passo anterior o que permitiu fechar a lista com 573 jornais regionais.<br><br>Reconhecemos que a esta lista
            faltarão Órgãos de Comunicação Social com presença online não comunicada à ERC, que só uma revisão manual
            mais extensa poderá colmatar.
          </p>
          <h4>3. Enriquecimento dos dados sobre os jornais regionais</h4>
          <p class="mb-4">
            Identificou-se manualmente as regiões, distritos e municípios que cada jornal cobre, fazendo uso dos
            respectivos Estatutos Editoriais e análise das próprias notícias. Esta cobertura é distinta da localização
            da sede: um jornal sediado em Lisboa pode cobrir a região do Alentejo, por exemplo.
          </p>
          <h4>4. Recolha das notícias dos jornais regionais</h4>
          <p class="mb-4">
            Procedeu-se a realizar uma extração/scrapping de todas as notícias em todos os jornais regionais. Os
            scrappers começaram por recolher todas as notícias do Arquivo.pt, e para os casos em que não foi possível,
            recolheram as notícias dos sites ativos e Wayback Machine. O nosso scraper consegue-se adaptar a variações
            na organização dos websites mas ainda há vários jornais com notícias online para os quais só um código
            específico conseguirá extrair as notícias corretamente, a dimensão desse esforço não coube nesta primeira
            fase de desenvolvimento e enquadra-se nos principais objetivos futuros para a plataforma.

          </p>
          <h4>5. Processamento dos dados e categorização</h4>
          <p class="mb-4">
            Com base no texto disponível no título e corpo das notícias, encontraram-se os temas mais comuns que
            formaram as categorias usadas no processo de categorização das mesmas. A lista inicial de categorias foi
            feita manualmente e foi usada uma abordagem de descoberta automática de novas categorias que seleciona
            grupos significativos de notícias e identifica novas possíveis categorias, as quais foram manualmente
            verificadas.
          </p>
          <h4>6. Apresentação e disponibilização dos dados</h4>
          <p class="mb-4">
            Criou-se um site que funciona como plataforma de acesso aos datasets e que permite fazer exploração e
            análise sobre os mesmos. Disponibilizou-se também na plataforma links para acesso a todos os conjuntos de
            dados relevantes.
          </p>
        </v-card-text>
      </v-card>
    </section>

    <!-- Code & License -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Código</h2>
      <v-card variant="outlined">
        <v-card-text>
          <v-btn href="https://github.com/olho-regional/olho-regional" target="_blank" color="primary" variant="tonal"
            prepend-icon="mdi-github" class="mb-4">
            Ver no GitHub
          </v-btn>
          <p class="text-body-1 mb-4">
            Todo o código deste projeto é de fonte aberta e está disponível no GitHub.<br /> O projeto inclui
            ferramentas de scraping, processamento de dados e esta aplicação web.
          </p>
          <v-divider class="my-4" />
          <h3 class="text-h6 mb-2">Licença</h3>
          <p class="text-body-2">
            Este projeto está licenciado sob a <a href="https://creativecommons.org/licenses/by/4.0/deed.pt" target="_blank"><strong>Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)</strong></a>. <br />Qualquer um pode usar, copiar,
            modificar e distribuir livremente, desde que dê o crédito apropriado. <br />
            Os dados recolhidos estão sujeitos aos termos de uso das fontes originais.
          </p>
        </v-card-text>
      </v-card>
    </section>

    <!-- Authors -->
    <section class="mb-10">
      <h2 class="text-h5 mb-4">Autores</h2>
      <p class="text-body-1">João Carvalho e Miguel Ramalho<br /> que numa tainada soalheira esboçaram este projeto</p>
    </section>
  </v-container>
</template>

<script setup lang="ts">
const datasets = [
  {
    name: 'Lista de Publicações periódicas - ERC',
    description: 'Lista completa de publicações periódicas registadas em Portugal, ativas e inativas entre 2000 e 2026.',
    size: '1 MB',
    format: 'CSV',
    downloadUrl: 'https://github.com/olho-regional/olho-regional/blob/main/dados/erc-jornais-2026-04.csv',
  },
  {
    name: 'Jornais regionais neste projeto',
    description: 'Lista estruturada dos jornais regionais identificados para este projeto, com de distrito e municípios.',
    size: '260 KB',
    format: 'JSON',
    downloadUrl: 'https://github.com/olho-regional/olho-regional/blob/main/processamento/database/jornais.json',
  },
  {
    name: 'Base de dados - Lite',
    description: 'Uma versão com todo a estrutura da nossa base de dados mas apenas um máximo de 10 notícias por jornal, útil para testes e compreender a estrutura.',
    size: '20 MB',
    format: 'SQLITE',
    downloadUrl: 'https://github.com/olho-regional/olho-regional/blob/main/dados/olho-regional-lite.db',
  },
  {
    name: 'Base de dados - Completa',
    description: 'A base de dados usada para suportar este site, podemos gerar várias versões mediante pedido: máximo 1000/5000/10000/sem limite de notícias por jornal.',
    size: '5/40 GB',
    format: 'SQLITE',
    requestUrl: 'https://forms.gle/D1YGZFxwKibGhcQz9',
  },
  {
    name: 'Notícias extraídas',
    description: 'Um conjunto de ficheiros JSON, um por jornal, contendo as notícias extraídas para cada jornal. Cada notícia tem o título, corpo, data de publicação e URL de origem. Dados são partilhados num ficheiro .zip.',
    size: '2 GB',
    format: 'JSON',
    requestUrl: 'https://forms.gle/D1YGZFxwKibGhcQz9',
  },
]


</script>
