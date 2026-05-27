# Olh'ó Regional

Um projeto de análise do jornalismo local em Portugal.

**Plataforma:** [olho-regional.pages.dev](https://olho-regional.pages.dev)

## Contexto

O panorama noticioso está a sofrer alterações a uma velocidade sem precedentes. Os meios noticiosos mais afetados são os que têm menor financiamento e alcance — os meios noticiosos regionais.

Este projeto agrega e facilita o acesso a meios regionais e fornece ferramentas para descoberta de jornais, notícias e análises sobre os dados relativos às notícias regionais nas últimas 3 décadas, fazendo uso do [Arquivo.pt](https://arquivo.pt/).

## Objetivos

- Implementar e disponibilizar publicamente um processo automatizado de recolha e extração de notícias em larga escala, a partir do Arquivo.pt.
- Compilar, enriquecer e partilhar uma base de dados de jornais e notícias regionais em Portugal dos últimos 30 anos.
- Facilitar um interface de pesquisa e análise sobre a base de dados construída.
- Apresentar casos de estudo que sirvam de inspiração à reutilização e maior adoção do projeto por cidadãos e académicos.
- Permitir a preservação de notícias regionais no Arquivo.pt, que ainda não se encontrem lá.

## Estrutura do Projeto

| Pasta | Descrição |
|-------|-----------|
| `frontend/` | Aplicação web (Nuxt 3 + Vuetify) |
| `backend/` | Servidor e deploy (Caddy + Docker) |
| `processamento/` | Pipelines de recolha, processamento e análise de dados |
| `dados/` | Ficheiros de dados auxiliares |

<details>
<summary><strong>1. Criar jornais.csv e jornais.json</strong></summary>

O processo começa pela construção da lista de jornais regionais:

```bash
cd processamento/data-scraping

# Gera jornais.csv a partir dos dados da ERC + Memória da Imprensa
python create_jornais_csv.py
```

Em seguida, valida-se e enriquece-se com dados geográficos para produzir `jornais.json`:

```bash
cd processamento/database

# Cruza jornais.csv com dados de municípios (geoapi.pt) e gera jornais.json
python parse_municipios.py
```

Ficheiros relevantes:
- [`processamento/data-scraping/create_jornais_csv.py`](processamento/data-scraping/create_jornais_csv.py)
- [`processamento/database/parse_municipios.py`](processamento/database/parse_municipios.py)
- [`processamento/scrape-erc/`](processamento/scrape-erc/) — scraping dos dados da ERC

</details>

<details>
<summary><strong>2. Recolha de notícias</strong></summary>

```bash
cd processamento/data-scraping
pip install -r requirements.txt
python collect.py
```

Recolhe artigos do Arquivo.pt, Wayback Machine e sites ativos para todos os jornais em `jornais.csv`. Ver [`processamento/data-scraping/README.md`](processamento/data-scraping/README.md) para mais detalhes.

</details>

<details>
<summary><strong>3. Análises e enriquecimentos</strong></summary>

Após a recolha de notícias, correm-se várias análises:

| Análise | Pasta | Descrição |
|---------|-------|-----------|
| Deteção de tópicos | [`processamento/topic-detection/`](processamento/topic-detection/) | Categorização automática de notícias por tema |
| Deteção de entidades (NER) | [`processamento/entity-detection/`](processamento/entity-detection/) | Extração de nomes de pessoas, locais e organizações |
| Análise de género | [`processamento/gender-analysis/`](processamento/gender-analysis/) | Análise da representação de género nas notícias |
| Qualidade das notícias | [`processamento/news-quality/`](processamento/news-quality/) | Métricas de qualidade dos artigos recolhidos |

Cada pasta contém um notebook Jupyter (`.ipynb`) com o pipeline completo.

</details>

<details>
<summary><strong>4. Construir a base de dados SQLite</strong></summary>

O script `insert_data.py` agrega todos os dados recolhidos e análises numa única base de dados SQLite (`olho-regional.db`):

```bash
cd processamento/database/scripts
pip install sqlite-utils
python insert_data.py
```

O script executa 7 etapas sequenciais:
1. Cria tabelas geográficas (distritos + municípios) a partir de `geo_data.json`
2. Cria tabela de jornais a partir de `jornais.json`
3. Insere artigos dos ficheiros `articles.jsonl` em `data-scraping/data/`
4. Insere labels (tópicos) de `topic-detection/articles_topics.jsonl`
5. Insere citações com género de `gender-analysis/output/quotes_with_gender.jsonl`
6. Insere entidades (NER) de `entity-detection/output/entities.jsonl`
7. Cria tabelas de resumo pré-agregadas para queries rápidas


A base de dados resultante é escrita em `processamento/database/olho-regional.db`.

</details>


## Autores

João Carvalho e Miguel Ramalho

## Licença

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt)
